import io
import time
from collections import defaultdict
from threading import Lock
from urllib.parse import urlparse

import requests
import telebot
from telebot import apihelper

from app.enums import PusherEnum
from app.modules.notification.base import BaseSender
from app.utils.log import logger
from app.utils.proxy import build_requests_proxies, build_telebot_proxy


MAX_IMAGE_BYTES = 10 * 1024 * 1024
DMM_IMAGE_MIN_INTERVAL_SECONDS = 1.2
DMM_IMAGE_RETRY_DELAYS = (0.0, 1.2, 2.5)
_HOST_FETCH_LOCKS: dict[str, Lock] = defaultdict(Lock)
_HOST_NEXT_REQUEST_AT: dict[str, float] = {}


def _extract_image_host(image_url: str) -> str:
    host = urlparse(str(image_url or '')).hostname or ''
    return host.strip().lower()


def _is_dmm_image_host(host: str) -> bool:
    return 'dmm' in (host or '')


def _wait_for_image_host_slot(host: str):
    if not _is_dmm_image_host(host):
        return
    lock = _HOST_FETCH_LOCKS[host]
    with lock:
        now = time.monotonic()
        next_allowed_at = _HOST_NEXT_REQUEST_AT.get(host, 0.0)
        wait_seconds = max(0.0, next_allowed_at - now)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        _HOST_NEXT_REQUEST_AT[host] = time.monotonic() + DMM_IMAGE_MIN_INTERVAL_SECONDS


def _fetch_image_response(image_url: str):
    host = _extract_image_host(image_url)
    delays = DMM_IMAGE_RETRY_DELAYS if _is_dmm_image_host(host) else (0.0,)
    last_response = None
    for attempt, delay_seconds in enumerate(delays, start=1):
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        _wait_for_image_host_slot(host)
        response = requests.get(
            image_url,
            proxies=build_requests_proxies(),
            stream=True,
            timeout=10,
            headers={
                'Referer': 'https://agaghhh.cc/' if 'hxmmdd' in image_url else 'https://sehuatang.org/'
            }
        )
        if response is None:
            continue
        last_response = response
        status_code = getattr(response, 'status_code', 200) or 200
        if status_code < 400:
            return response
        logger.warning(
            f'Telegram 图片请求失败 | image_url={image_url}, host={host or "unknown"}, status_code={status_code}, attempt={attempt}/{len(delays)}'
        )
        try:
            response.close()
        except Exception:
            pass
    return last_response


def _resolve_parse_mode(conf: dict) -> str | None:
    mode = str(conf.get('parse_mode') or 'text').strip().lower()
    if mode == 'markdown':
        return 'Markdown'
    if mode == 'markdownv2':
        return 'MarkdownV2'
    if mode == 'html':
        return 'HTML'
    return None


# Telegram MarkdownV2 特殊字符转义
_markdownv2_escape_chars = r'\_*[]()~`>#+-=|{}.!'
def _escape_markdownv2(text: str) -> str:
    for ch in _markdownv2_escape_chars:
        text = text.replace(ch, '\\' + ch)
    return text


def get_image(image_url):
    if not image_url:
        return None

    res = _fetch_image_response(image_url)
    content = b''
    if res is not None:
        try:
            chunks = []
            total_bytes = 0
            for chunk in res.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total_bytes += len(chunk)
                if total_bytes > MAX_IMAGE_BYTES:
                    logger.warning(f'Telegram 图片过大，已跳过: image_url={image_url}, size={total_bytes}')
                    return None
                chunks.append(chunk)
            content = b''.join(chunks)
        except Exception:
            logger.exception(f'Telegram 图片流读取失败: image_url={image_url}')
            content = b''
        finally:
            try:
                res.close()
            except Exception:
                pass

    if not content:
        logger.warning(f'Telegram 图片内容为空，跳过图片发送: image_url={image_url}')
        return None

    image = io.BytesIO(content)
    image.name = 'image.jpg'
    image.seek(0)
    return image



class TelegramNotifier(BaseSender):
    conf: dict
    name = PusherEnum.TELEGRAM.value
    bot: telebot.TeleBot | None = None

    def _resolve_parse_mode(self, parse_mode: str | None = None) -> str | None:
        if parse_mode is not None:
            return _resolve_parse_mode({'parse_mode': parse_mode})
        return _resolve_parse_mode(self.conf)

    def __init__(self, conf):
        self.conf = conf
        try:
            self.bot = telebot.TeleBot(self.conf.get('bot_token'))
            apihelper.proxy = build_telebot_proxy()
        except Exception:
            logger.exception('Telegram 初始化失败')
            self.bot = None

    def send(self, message=None, image_url=None, parse_mode=None, **kwargs):
        if not self.bot:
            return

        parse_mode = self._resolve_parse_mode(parse_mode)
        # MarkdownV2 需要转义特殊字符
        if parse_mode == 'MarkdownV2' and message:
            message = _escape_markdownv2(message)
        try:
            image = get_image(image_url) if image_url and self.conf.get('push_image') else None
            if image is not None:
                self.bot.send_photo(
                    self.conf.get('chat_id'),
                    photo=image,
                    has_spoiler=self.conf.get('spoiler', False),
                    caption=message,
                    parse_mode=parse_mode,
                )
                return

            if image_url and self.conf.get('push_image'):
                logger.warning(
                    f'Telegram 图片获取失败，已降级为文本消息: chat_id={self.conf.get("chat_id")}, image_url={image_url}'
                )
            self.bot.send_message(self.conf.get('chat_id'), message, parse_mode=parse_mode)
        except Exception:
            logger.exception(
                f'Telegram 推送失败: chat_id={self.conf.get("chat_id")}, has_image={bool(image_url)}'
            )
            if image_url:
                try:
                    self.bot.send_message(self.conf.get('chat_id'), message, parse_mode=parse_mode)
                    logger.warning(
                        f'Telegram 图片消息发送失败，已降级为文本消息: chat_id={self.conf.get("chat_id")}'
                    )
                except Exception:
                    logger.exception(
                        f'Telegram 文本兜底发送失败: chat_id={self.conf.get("chat_id")}'
                    )
