import datetime
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
from sqlalchemy import func, exists, select, create_engine
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.api.services.subscribe_service import build_article_push_fields
from app.core.database import session_scope, database_url
from app.enums import DownloadClientEnum, SubscribeStatus
from app.models import DownloadLog, Rule, Filter, Movie, Subscribe
from app.models.article import Article
from app.utils.db_lock import acquire_subscribe_write_lock
from app.modules.downloadclient.manager import downloadManager
from app.modules.mediaserver import mediaServerManager
from app.modules.notification.manager import pushManager
from app.schemas.article import ArticleQuery
from app.api.services import rule_service
from app.api.services.article_match_service import has_chinese, has_uc, matches_article_filter, has_uhd
from app.schemas.response import success, error
import pandas as pd
import re

from app.utils.movie_number import extract_movie_numbers, extract_primary_movie_number
from app.utils import logger

ARRAY_FIELDS = {"magnet", "edk", "preview_images"}
ARTICLE_SUBSCRIBE_COMPLETED_MESSAGE = '已命中资源并创建下载任务'


def _extract_article_movie_numbers(title: str | None) -> list[str]:
    return extract_movie_numbers((title or '').strip())


def _extract_article_match_number(title: str | None) -> str | None:
    return extract_primary_movie_number(title)


def _hydrate_article_match_number(article: Article) -> None:
    article.match_number = _extract_article_match_number(article.title)


def _hydrate_article_match_number_row(row: dict) -> dict:
    row['match_number'] = _extract_article_match_number(row.get('title'))
    return row


def _update_subscribe_state_after_article_download(article: Article) -> None:
    article_numbers = _extract_article_movie_numbers(article.title)
    if not article_numbers:
        return

    with session_scope() as db:
        acquire_subscribe_write_lock(db)
        rows = (
            db.query(Subscribe, Movie, Filter)
            .join(Movie, Movie.id == Subscribe.movie_id)
            .outerjoin(Filter, Filter.id == Subscribe.filter_id)
            .filter(
                Subscribe.status == SubscribeStatus.ACTIVE.value,
                Movie.number.in_(article_numbers),
            )
            .order_by(Subscribe.id.asc())
            .all()
        )

        completed_push_payloads: list[tuple[int, int]] = []
        for subscribe, movie, filter_obj in rows:
            if matches_article_filter(article, filter_obj):
                subscribe.status = SubscribeStatus.COMPLETED.value
                subscribe.pre_download_enabled = False
                completed_push_payloads.append((subscribe.id, movie.id))
                continue

            if subscribe.pre_download_enabled:
                subscribe.pre_download_enabled = False

    if not rows or not completed_push_payloads:
        return

    from app.api.services.subscribe_service import _push_subscribe_completed

    with session_scope() as db:
        article_in_db = db.get(Article, article.id)
        for subscribe_id, movie_id in completed_push_payloads:
            subscribe = db.get(Subscribe, subscribe_id)
            movie = db.get(Movie, movie_id)
            if not subscribe or not movie:
                continue
            _push_subscribe_completed(
                subscribe,
                movie,
                article=article_in_db,
                completion_source='download',
                db=db,
            )


def _build_article_library_lookup(rows) -> tuple[dict[int, list[str]], dict[str, bool]]:
    article_numbers_map: dict[int, list[str]] = {}
    movie_numbers: set[str] = set()

    for article, _ in rows:
        if not article:
            continue
        numbers = _extract_article_movie_numbers(article.title)
        article_numbers_map[article.id] = numbers
        movie_numbers.update(numbers)

    in_library_map: dict[str, bool] = {}
    if not movie_numbers:
        return article_numbers_map, in_library_map

    max_workers = min(8, len(movie_numbers))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_number = {
            executor.submit(mediaServerManager.any_movie_exists_by_number, number): number
            for number in movie_numbers
        }
        for future in as_completed(future_to_number):
            number = future_to_number[future]
            try:
                in_library_map[number] = future.result()
            except Exception:
                in_library_map[number] = False

    return article_numbers_map, in_library_map


def _parse_pg_text_array(value: str) -> list[str | None]:
    text = value.strip()
    if text == '{}':
        return []
    if not (text.startswith('{') and text.endswith('}')):
        raise ValueError('invalid postgres array text')

    items: list[str | None] = []
    token: list[str] = []
    in_quotes = False
    escaped = False

    for ch in text[1:-1]:
        if escaped:
            token.append(ch)
            escaped = False
            continue

        if in_quotes:
            if ch == '\\':
                escaped = True
            elif ch == '"':
                in_quotes = False
            else:
                token.append(ch)
            continue

        if ch == ',':
            raw = ''.join(token).strip()
            items.append(None if raw == 'NULL' else raw)
            token = []
            continue

        if ch == '"':
            in_quotes = True
            continue

        token.append(ch)

    if escaped or in_quotes:
        raise ValueError('unterminated postgres array text')

    raw = ''.join(token).strip()
    items.append(None if raw == 'NULL' else raw)
    return items


def _normalize_array_field(value):
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith('[') and text.endswith(']'):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return parsed
        if text.startswith('{') and text.endswith('}'):
            return _parse_pg_text_array(text)
        return [text]
    return value


def _normalize_import_row(row: dict) -> dict:
    normalized = dict(row)
    for field in ARRAY_FIELDS:
        if field in normalized:
            normalized[field] = _normalize_array_field(normalized[field])
    return _hydrate_article_match_number_row(normalized)


def get_article_list(db: Session, query: ArticleQuery) -> Dict:
    in_stock_expr = exists().where(
        DownloadLog.article_id == Article.id
    )
    q = db.query(Article, in_stock_expr.label("in_stock"))
    if query.website:
        q = q.filter(Article.website == query.website)
    if query.keyword:
        q = q.filter(Article.title.ilike(f"%{query.keyword}%"))
    if query.section:
        q = q.filter(Article.section == query.section)
    if query.category:
        q = q.filter(Article.category == query.category)
    if query.date_range and query.date_range.get('from') and query.date_range.get('to'):
        q = q.filter(Article.publish_date.between(query.date_range.get('from'), query.date_range.get('to')))
    total = q.count()
    page = query.page
    offset = (page - 1) * query.page_size
    rows = (
        q.order_by(Article.publish_date.desc(), Article.create_time.desc(), Article.id.desc())
        .offset(offset)
        .limit(query.page_size)
        .all()
    )
    article_numbers_map, in_library_map = _build_article_library_lookup(rows)
    items = []
    for article, in_stock in rows:
        setattr(article, "in_stock", in_stock)
        article_numbers = article_numbers_map.get(article.id, [])
        setattr(article, "in_library", any(in_library_map.get(number, False) for number in article_numbers))
        if article.website == 'x1080x' and article.preview_images:
            imgs = [f'/api/v1/img-proxy/?url={url}' if 'hxmmdd' in url else url for url in article.preview_images]
            setattr(article, "img_list", imgs)
        else:
            setattr(article, "img_list", article.preview_images)
        items.append(article)
    has_more = len(items) == query.page_size
    return success({
        "page": page,
        "pageSize": query.page_size,
        "total": total,
        "items": items,
        "hasMore": has_more
    })


def get_torrents(keyword, db: Session) -> Dict:
    articles = db.query(Article).filter(Article.title.ilike(f"%{keyword}%")).all()
    torrents = []
    for article in articles:
        magnet_list = article.magnet or []
        edk_list = article.edk or []
        download_url = magnet_list[0] if magnet_list else (edk_list[0] if edk_list else '')

        torrent = {
            'id': article.tid,
            'site': article.website,
            'size_mb': article.size or 0,
            'seeders': 66,
            'title': article.title,
            'download_url': download_url,
            'free': True,
            'chinese': has_chinese(f"{article.title}{article.section}"),
            'uc': has_uc(f"{article.title}{article.section}"),
            'uhd': has_uhd(f"{article.title}{article.section}")
        }
        torrents.append(torrent)
    return success(torrents)


def get_category(db: Session):
    item_count = func.count(Article.id).label("item_count")
    result = (
        db.query(Article.website, Article.section, Article.category, item_count)
        .filter(Article.website.isnot(None), Article.website != '', Article.section.isnot(None), Article.section != '')
        .group_by(Article.website, Article.section, Article.category)
        .order_by(item_count.desc())
        .all()
    )

    websites = {}
    for website, section, category, count in result:
        website_key = website or ''
        if website_key not in websites:
            websites[website_key] = {
                "name": website_key,
                "count": 0,
                "sections": {},
            }

        website_item = websites[website_key]
        section_map = website_item["sections"]
        if section not in section_map:
            section_map[section] = {
                "name": section,
                "count": 0,
                "categories": [],
            }

        section_item = section_map[section]
        if category:
            section_item["categories"].append({
                "name": category,
                "count": count,
            })

        section_item["count"] += count
        website_item["count"] += count

    items = []
    for website_name, website_item in sorted(websites.items(), key=lambda item: (-item[1]["count"], item[0])):
        sections = []
        for section_name, section_item in sorted(
                website_item["sections"].items(), key=lambda item: (-item[1]["count"], item[0])
        ):
            section_item["categories"] = sorted(
                section_item["categories"], key=lambda item: (-item["count"], item["name"])
            )
            sections.append(section_item)
        items.append({
            "name": website_name,
            "count": website_item["count"],
            "sections": sections,
        })

    return success(items)


def calc_score(rule, website, section, category, title):
    score = 0

    if rule_service.rule_matches_option(rule.website, website):
        website_values = rule_service.normalize_rule_values(rule.website)
        score += 10 if rule_service.ALL_VALUE not in website_values else 1
    else:
        return 0

    if rule_service.rule_matches_option(rule.section, section):
        section_values = rule_service.normalize_rule_values(rule.section)
        score += 10 if rule_service.ALL_VALUE not in section_values else 1
    else:
        return 0

    if rule_service.rule_matches_option(rule.category, category):
        category_values = rule_service.normalize_rule_values(rule.category)
        score += 5 if rule_service.ALL_VALUE not in category_values else 1
    else:
        return 0

    rule_regex = rule.regex

    if rule_regex:
        try:
            if re.search(rule_regex, title):
                score += 20
            else:
                return 0
        except re.error as e:
            # 脏数据兜底：跳过该 rule，避免一条坏 regex 把整批订阅搞挂
            from app.utils import logger
            logger.warning(
                f"Rule 正则无效，已跳过该规则 | rule_id={getattr(rule, 'id', '?')}, regex={rule_regex!r}, err={e}"
            )
            return 0
    else:
        score += 1
    return score


def match_best_rules(rules, website, section, category, title):
    best_score = 0
    best_rules = []

    for rule in rules:
        score = calc_score(rule, website, section, category, title)
        if score == 0:
            continue

        if score > best_score:
            best_score = score
            best_rules = [rule]
        elif score == best_score:
            best_rules.append(rule)

    return best_rules


def convert_save_path(article: Article, original_save_path):
    current_date = datetime.date.today()
    save_path = original_save_path.format(section=article.section,
                                          category=article.category or '未分类',
                                          publish_date=article.publish_date,
                                          current_date=current_date
                                          )
    return save_path


def download_magnet(article: Article, downloader, save_path):
    save_path = convert_save_path(article, save_path)
    success_count = 0
    errors = []
    if article.magnet:
        for magnet in article.magnet:
            is_success, err = downloadManager.download(f'Downloader.{downloader}', magnet, save_path)
            if is_success:
                success_count += 1
            elif err:
                errors.append(err)
    if article.edk and f'Downloader.{downloader}' in [DownloadClientEnum.THUNDER.value,
                                                      DownloadClientEnum.CLOUDDRIVE.value, DownloadClientEnum.TOOLS115.value]:
        for edk in article.edk:
            is_success, err = downloadManager.download(f'Downloader.{downloader}', edk, save_path)
            if is_success:
                success_count += 1
            elif err:
                errors.append(err)

    if success_count > 0:
        with session_scope() as db:
            download_log = DownloadLog()
            download_log.article_id = article.id
            download_log.save_path = save_path
            download_log.downloader = downloader
            db.add(download_log)
        return True, None
    error_msg = errors[0] if errors else '下载失败'
    return False, error_msg


def convert_message_data(article: Article, downloader: str, save_path: str):
    payload = {
        'download_client': downloader,
        'download_save_path': save_path,
        'image': article.preview_images[0] if article.preview_images else None

    }
    payload.update(build_article_push_fields(article))
    return payload


def _normalize_article_id(article_id) -> int:
    try:
        return int(article_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'Invalid article id: {article_id}') from exc


def download_article(article_id: int, update_subscribe_state: bool = True):
    article_id = _normalize_article_id(article_id)
    with session_scope() as db:
        article = db.get(Article, article_id)
        rules = db.query(Rule).all()

    if not article:
        return error('文章不存在')

    if not rules:
        return error('未配置下载规则')

    success_count = 0
    website = article.website
    section = article.section
    category = article.category
    best_rules = match_best_rules(rules, website, section, category, article.title)
    if not best_rules:
        return error("未匹配到合适的下载路径")

    last_error = None
    for rule in best_rules:
        is_success, err = download_magnet(article, rule.downloader, rule.save_path)
        if is_success:
            pushManager.send_event('download', convert_message_data(article, rule.downloader, rule.save_path))
            success_count += 1
        else:
            last_error = err

    if success_count > 0:
        if update_subscribe_state:
            _update_subscribe_state_after_article_download(article)
        return success(message="成功创建下载任务")
    return error(last_error or "创建下载任务失败")


def manul_download(article_id, downloader, save_path, update_subscribe_state: bool = True):
    article_id = _normalize_article_id(article_id)
    with session_scope() as db:
        article = db.get(Article, article_id)

    if not article:
        return error('文章不存在')

    is_success, err = download_magnet(article, downloader, save_path)
    if is_success:
        pushManager.send_event('download', convert_message_data(article, downloader, save_path))
        if update_subscribe_state:
            _update_subscribe_state_after_article_download(article)
        return success(message="成功创建下载任务")
    return error(err or "创建下载任务失败")


def _batch_download_worker(article_id_list):
    results = []
    success_count = 0
    fail_count = 0

    for raw_article_id in article_id_list:
        try:
            article_id = _normalize_article_id(raw_article_id)
            resp = download_article(article_id)
            item_success = isinstance(resp, dict) and resp.get('code') == 0
            if item_success:
                success_count += 1
            else:
                fail_count += 1
            results.append({
                'article_id': article_id,
                'success': item_success,
                'message': resp.get('message') if isinstance(resp, dict) else None,
            })
        except Exception as exc:
            fail_count += 1
            logger.exception(f'批量下载失败 | article_id={raw_article_id}')
            results.append({
                'article_id': raw_article_id,
                'success': False,
                'message': str(exc),
            })

    logger.info(
        f'批量下载处理完成 | total={len(results)}, success_count={success_count}, fail_count={fail_count}'
    )
    return {
        'total': len(results),
        'success_count': success_count,
        'fail_count': fail_count,
        'items': results,
    }


def batch_download(article_id_list):
    article_ids = [str(article_id).strip() for article_id in (article_id_list or []) if str(article_id).strip()]
    if not article_ids:
        return error('article_id_list is empty')

    if len(article_ids) == 1:
        article_id = _normalize_article_id(article_ids[0])
        return download_article(article_id)

    threading.Thread(
        target=_batch_download_worker,
        kwargs={'article_id_list': article_ids},
        name='article-batch-download',
        daemon=True,
    ).start()
    return success({
        'total': len(article_ids),
    }, message='批量下载任务已提交，正在后台处理')


def _batch_manul_download_worker(article_id_list, downloader, save_path):
    results = []
    success_count = 0
    fail_count = 0

    for raw_article_id in article_id_list:
        try:
            article_id = _normalize_article_id(raw_article_id)
            resp = manul_download(article_id, downloader, save_path)
            item_success = isinstance(resp, dict) and resp.get('code') == 0
            if item_success:
                success_count += 1
            else:
                fail_count += 1
            results.append({
                'article_id': article_id,
                'success': item_success,
                'message': resp.get('message') if isinstance(resp, dict) else None,
            })
        except Exception as exc:
            fail_count += 1
            logger.exception(f'批量手动下载失败 | article_id={raw_article_id}')
            results.append({
                'article_id': raw_article_id,
                'success': False,
                'message': str(exc),
            })

    logger.info(
        f'批量手动下载处理完成 | total={len(results)}, success_count={success_count}, fail_count={fail_count}, downloader={downloader}'
    )
    return {
        'total': len(results),
        'success_count': success_count,
        'fail_count': fail_count,
        'items': results,
    }


def batch_manul_download(article_id_list, downloader, save_path):
    article_ids = [str(article_id).strip() for article_id in (article_id_list or []) if str(article_id).strip()]
    if not article_ids:
        return error('article_id_list is empty')

    if len(article_ids) == 1:
        article_id = _normalize_article_id(article_ids[0])
        return manul_download(article_id, downloader, save_path)

    threading.Thread(
        target=_batch_manul_download_worker,
        kwargs={
            'article_id_list': article_ids,
            'downloader': downloader,
            'save_path': save_path,
        },
        name='article-batch-manual-download',
        daemon=True,
    ).start()
    return success({
        'total': len(article_ids),
        'downloader': downloader,
        'save_path': save_path,
    }, message='批量手动下载任务已提交，正在后台处理')


CHUNK_SIZE = 5000


async def import_excel(file, db: Session):
    contents = await file.read()
    filename = file.filename.lower()
    try:
        if filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
        elif filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(contents), engine="xlrd")
        elif filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            logger.info("不支持的文件格式")
            return error("不支持的文件格式")
    except Exception as e:
        logger.exception("")
        return error(f"解析文件失败: {e}")

    df = df.astype(object).where(pd.notnull(df), None)

    cols = ["publish_date", "size", "category"]
    for col in cols:
        if col in df.columns:
            df[col] = df[col].where(pd.notna(df[col]), None)

    rows = df.to_dict(orient="records")
    del df

    total_inserted = 0
    total_skipped = 0

    for i in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[i: i + CHUNK_SIZE]

        valid_chunk = [
            row for row in chunk
            if row.get("tid") is not None and row.get("website") is not None
        ]
        total_skipped += len(chunk) - len(valid_chunk)

        if not valid_chunk:
            continue

        pairs = list({(int(row["tid"]), str(row["website"])) for row in valid_chunk})

        try:
            tid_list = list({p[0] for p in pairs})
            result = db.execute(
                select(Article.tid, Article.website).where(
                    Article.tid.in_(tid_list)
                )
            )
            existing = {(row[0], row[1]) for row in result}
        except Exception as e:
            db.rollback()
            logger.exception("")
            return error(f"查询失败: {e}")

        new_rows = [
            row for row in valid_chunk
            if (int(row["tid"]), str(row["website"])) not in existing
        ]
        total_skipped += len(valid_chunk) - len(new_rows)
        logger.info(f"已完成同步 {i + len(chunk)}/{len(rows)}")
        if not new_rows:
            continue

        objects = [
            Article(**{key: value for key, value in _normalize_import_row(row).items() if key != "id"})
            for row in new_rows
        ]
        db.bulk_save_objects(objects)
        total_inserted += len(objects)

    logger.info(f"插入: {total_inserted} 条，跳过: {total_skipped} 条")
    return success({
        "inserted": total_inserted,
        "skipped": total_skipped,
    })


def row_to_safe_list(row):
    safe_row = []
    for value in row:
        if isinstance(value, (list, dict)):
            # ARRAY 或 JSON 序列化成 JSON 字符串
            safe_row.append(json.dumps(value, ensure_ascii=False))
        else:
            safe_row.append(value)
    return safe_row


def generate_csv():
    read_engine = create_engine(
        database_url,
        execution_options={"stream_results": True}
    )
    with read_engine.connect() as conn:
        raw = conn.connection
        cursor = raw.cursor()

        buffer = io.StringIO()

        try:
            cursor.copy_expert(
                "COPY article TO STDOUT WITH CSV HEADER",
                buffer
            )

            buffer.seek(0)

            while True:
                chunk = buffer.read(8192)
                if not chunk:
                    break
                yield chunk.encode("utf-8")

        finally:
            cursor.close()


def export_article():
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=article.csv"
        }
    )
