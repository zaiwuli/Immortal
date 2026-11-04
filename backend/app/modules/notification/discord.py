import io
import json
from typing import Any

import requests

from app.core.config import config_manager
from app.enums import PusherEnum
from app.modules.notification.base import BaseSender
from app.utils.log import logger
from app.utils.proxy import build_requests_proxies

MAX_IMAGE_BYTES = 10 * 1024 * 1024


def download_discord_image(image_url: str) -> io.BytesIO | None:
    res = requests.get(
        image_url,
        proxies=build_requests_proxies(),
        stream=True,
        timeout=10,
        headers={
            'Referer': 'https://agaghhh.cc/' if 'hxmmdd' in image_url else 'https://sehuatang.org/'
        },
    )
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
                    logger.warning(f'Discord 图片过大，已跳过: image_url={image_url}, size={total_bytes}')
                    return None
                chunks.append(chunk)
            content = b''.join(chunks)
        except Exception:
            logger.exception(f'Discord 图片流读取失败: image_url={image_url}')
            content = b''
        finally:
            try:
                res.close()
            except Exception:
                pass
    if not content:
        logger.warning(f'Discord 图片内容为空，跳过图片发送: image_url={image_url}')
        return None
    image = io.BytesIO(content)
    image.name = 'image.jpg'
    image.seek(0)
    return image


class DiscordNotifier(BaseSender):
    conf: dict
    name = PusherEnum.DISCORD.value

    def __init__(self, conf: dict):
        self.conf = conf

    def send(self, message=None, image_url=None, **kwargs):
        if not message and not image_url:
            return
        if self.conf.get('webhook_url'):
            self._send_webhook(message, image_url)
            return
        if self.conf.get('bot_token') and self.conf.get('channel_id'):
            self._send_bot_message(message, image_url)
            return
        logger.warning('Discord 推送已跳过，未配置 webhook_url 或 bot_token + channel_id')

    def _send_webhook(self, message: str | None, image_url: str | None):
        try:
            self._dispatch_request(
                url=self.conf.get('webhook_url'),
                headers={'Content-Type': 'application/json'},
                message=message,
                image_url=image_url,
            )
        except Exception:
            logger.exception('Discord Webhook 推送失败')

    def _send_bot_message(self, message: str | None, image_url: str | None):
        channel_id = str(self.conf.get('channel_id')).strip()
        if not channel_id:
            logger.warning('Discord 推送已跳过，channel_id 为空')
            return
        try:
            self._dispatch_request(
                url=f'https://discord.com/api/v10/channels/{channel_id}/messages',
                headers={
                    'Authorization': f'Bot {self.conf.get("bot_token")}',
                    'Content-Type': 'application/json',
                },
                message=message,
                image_url=image_url,
                channel_id=channel_id,
            )
        except Exception:
            logger.exception(f'Discord Bot 推送失败: channel_id={channel_id}')

    def _dispatch_request(
            self,
            url: str | None,
            headers: dict[str, str],
            message: str | None,
            image_url: str | None,
            channel_id: str | None = None,
    ):
        if not url:
            return
        multipart_payload = self._build_multipart_payload(message, image_url)
        if multipart_payload is not None:
            response = requests.post(
                url,
                data={'payload_json': json.dumps(multipart_payload['payload'], ensure_ascii=False)},
                files={
                    'files[0]': (
                        multipart_payload['filename'],
                        multipart_payload['content'],
                        multipart_payload['content_type'],
                    )
                },
                headers={key: value for key, value in headers.items() if key.lower() != 'content-type'},
                proxies=self._get_proxies(),
                timeout=20,
            )
        else:
            if self.conf.get('spoiler') and image_url and self.conf.get('push_image'):
                logger.warning(f'Discord 剧透图片下载失败，已降级为纯文本: image_url={image_url}')
            inline_image_url = None if self.conf.get('spoiler') else image_url
            payload = self._build_payload(message, inline_image_url)
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                proxies=self._get_proxies(),
                timeout=15,
            )
        if response is None or response.status_code >= 400:
            target = f' channel_id={channel_id},' if channel_id else ' '
            logger.error(
                f'Discord 推送失败 |{target} status={getattr(response, "status_code", None)}'
            )

    def _build_payload(self, message: str | None, image_url: str | None) -> dict[str, Any]:
        embed = self._build_embed(message, image_url)
        payload: dict[str, Any] = {}
        if message and embed is None:
            payload['content'] = message[:2000]
        if embed is not None:
            payload['embeds'] = [embed]
        username = str(self.conf.get('username') or '').strip()
        if username and self.conf.get('webhook_url'):
            payload['username'] = username[:80]
        return payload

    def _build_multipart_payload(self, message: str | None, image_url: str | None):
        if not self.conf.get('push_image') or not self.conf.get('spoiler') or not image_url:
            return None
        image = download_discord_image(image_url)
        if image is None:
            return None
        filename = 'SPOILER_image.jpg'
        payload = self._build_payload(message, None)
        embed = self._build_embed(message, None)
        if embed is None:
            embed = {}
        embed['image'] = {'url': f'attachment://{filename}'}
        payload['embeds'] = [embed]
        return {
            'payload': payload,
            'filename': filename,
            'content_type': 'image/jpeg',
            'content': image.getvalue(),
        }

    def _build_embed(self, message: str | None, image_url: str | None) -> dict[str, Any] | None:
        if not self.conf.get('push_image') and not message:
            return None

        embed: dict[str, Any] = {}
        if self.conf.get('push_image') and image_url:
            embed['image'] = {'url': image_url}
        description = str(message or '').strip()
        if description:
            embed['description'] = description[:4096]

        return embed or None

    def _get_proxies(self) -> dict[str, str] | None:
        proxy = str(config_manager.get().PROXY or '').strip()
        if not proxy:
            return None
        return {'https': proxy, 'http': proxy}
