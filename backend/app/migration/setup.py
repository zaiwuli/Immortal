import json
from pathlib import Path

from sqlalchemy import or_, text

from app.core.database import session_scope
from app.models import Article, Config
from app.models.task import Task
from app.utils.movie_number import extract_primary_movie_number

BASE_DIR = Path(__file__).resolve().parent
RULE_MIGRATION_MARKER = 'MigrationRuleWebsiteArr'
PERF_INDEX_MIGRATION_MARKER = 'MigrationPerfIndexes20260326'
ARTICLE_MATCH_NUMBER_MIGRATION_MARKER = 'MigArticleMatchNum20260326'
NORMALIZE_SUBTITLES_MIGRATION_MARKER = 'MigNormalizeSubtitles20260326'
ARTICLE_MATCH_NUMBER_BACKFILL_BATCH_SIZE = 1000


def run_sql_file(session, filename: str):
    sql = (BASE_DIR / filename).read_text(encoding='utf-8').lstrip('\ufeff')
    session.execute(text(sql))


def run_sql_file_once(session, filename: str, marker_key: str):
    marker = session.query(Config).filter(Config.key == marker_key).first()
    if marker is not None:
        return False

    run_sql_file(session, filename)
    session.add(Config(key=marker_key, content=json.dumps({'filename': filename, 'done': True})))
    session.flush()
    return True


def backfill_article_match_numbers(session) -> int:
    updated_count = 0
    last_id = 0

    while True:
        articles = (
            session.query(Article)
            .filter(Article.id > last_id)
            .filter(
                or_(
                    Article.match_number.is_(None),
                    Article.match_number == '',
                )
            )
            .order_by(Article.id.asc())
            .limit(ARTICLE_MATCH_NUMBER_BACKFILL_BATCH_SIZE)
            .all()
        )
        if not articles:
            break

        for article in articles:
            article.match_number = extract_primary_movie_number(article.title)
            last_id = article.id

        updated_count += len(articles)
        session.flush()

    return updated_count


def upgrade():
    with session_scope() as session:
        run_sql_file_once(session, '20260324_rule_multiselect_website.sql', RULE_MIGRATION_MARKER)
        run_sql_file_once(session, '20260326_add_perf_indexes.sql', PERF_INDEX_MIGRATION_MARKER)
        article_match_migration_ran = run_sql_file_once(
            session,
            '20260326_article_match_number.sql',
            ARTICLE_MATCH_NUMBER_MIGRATION_MARKER,
        )
        run_sql_file_once(
            session,
            '20260326_normalize_subtitles.sql',
            NORMALIZE_SUBTITLES_MIGRATION_MARKER,
        )

        if article_match_migration_ran:
            backfill_article_match_numbers(session)
