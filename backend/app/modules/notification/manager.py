import atexit
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List

from jinja2 import Template

from .base import BaseSender
from .discord import DiscordNotifier
from .telegram import TelegramNotifier
from .wechat import WeChatNotifier
from ...enums import PusherEnum
from ...utils.log import logger


def _to_template_number(value: Any) -> int | float | None:
    if value is None or value == '' or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _build_numeric_template_fields(**fields: Any) -> dict[str, int | float | None]:
    return {
        f'{key}_number': _to_template_number(value)
        for key, value in fields.items()
    }


class PushManager:
    def __init__(self):
        self.senders: List[BaseSender] = []
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='push-notify')
        atexit.register(self._shutdown_executor)

    def register(self, sender: BaseSender):
        self.senders.append(sender)

    def _build_message(self, sender: BaseSender, data: dict | str, template_key: str = 'template',
                       event_name: str | None = None):
        if isinstance(data, dict):
            template_text = sender.conf.get(template_key) or sender.conf.get('template') or ''
            if template_text:
                try:
                    message = Template(template_text).render(**data)
                except Exception:
                    preview_lines = [str(line) for line in str(template_text).splitlines()[:12]]
                    logger.exception(
                        '通知模板渲染失败 | '
                        f'sender={sender.name}, event={event_name or "unknown"}, template_key={template_key}, '
                        f'template_preview={preview_lines}'
                    )
                    raise
                return message, data.get('image')
            return str(data.get('message') or ''), data.get('image')
        return str(data), None

    def _dispatch(self, sender: BaseSender, message: str, image_url: str | None, **kwargs):
        try:
            sender.send(message, image_url, **kwargs)
        except Exception:
            logger.exception(
                f"推送失败: sender={sender.name}, has_image={bool(image_url)}"
            )

    def _submit_dispatch(self, sender: BaseSender, message: str, image_url: str | None, **kwargs):
        try:
            self.executor.submit(self._dispatch, sender, message, image_url, **kwargs)
        except RuntimeError:
            self._dispatch(sender, message, image_url, **kwargs)

    def send(self, message: str, image_url: str = None, title: str | None = None, **kwargs):
        for sender in self.senders:
            if not sender.conf.get('enable'):
                continue
            self._submit_dispatch(sender, str(message), image_url, title=title, **kwargs)

    def send_event(self, event_name: str, data: dict):
        enable_key = f'{event_name}_enable'
        template_key = f'{event_name}_template'
        for sender in self.senders:
            if not sender.conf.get('enable'):
                continue
            if enable_key in sender.conf and not sender.conf.get(enable_key):
                continue
            message, sender_image_url = self._build_message(sender, data, template_key, event_name=event_name)
            if sender.name == PusherEnum.WECHAT.value:
                if event_name in ['download', 'movie_subscribe', 'subscribe_completed', 'cast_subscribe']:
                    title_map = {
                        'download': '📥 新下载任务',
                        'movie_subscribe': '🔔 影片订阅成功',
                        'subscribe_completed': '✅ 订阅任务完成',
                        'cast_subscribe': '🎭 演员订阅成功'
                    }

                    title = title_map.get(event_name, '📢 新消息')
                    self._submit_dispatch(sender, message, sender_image_url, title=title)
                else:
                    logger.warning(f"微信推送渠道缺少事件推送：{event_name}")
            else:
                self._submit_dispatch(sender, message, sender_image_url)

    def reload(self, name, config: dict):
        for sender in list(self.senders):
            if sender.name == name:
                self.senders.remove(sender)
        if name == PusherEnum.WECHAT.value:
            self.register(WeChatNotifier(config))
        if name == PusherEnum.TELEGRAM.value:
            self.register(TelegramNotifier(config))
        if name == PusherEnum.DISCORD.value:
            self.register(DiscordNotifier(config))

    def _shutdown_executor(self):
        self.executor.shutdown(wait=True)


pushManager = PushManager()
