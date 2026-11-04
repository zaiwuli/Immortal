import threading
import time

import requests

from app.enums import PusherEnum
from app.modules.notification.base import BaseSender
from app.utils.log import logger

REQUEST_TIMEOUT = 15
ACCESS_TOKEN_REFRESH_BUFFER_SECONDS = 60
TOKEN_RETRY_ERRCODES = {40014, 42001}
DEFAULT_TOKEN_EXPIRES_IN = 7200


def _truncate_response_text(response) -> str:
    return str(getattr(response, 'text', '') or '')[:500]


class WeChatNotifier(BaseSender):
    conf: dict
    name = PusherEnum.WECHAT.value

    def __init__(self, conf: dict):
        self.conf = conf
        self._access_token: str | None = None
        self._access_token_expire_at = 0.0
        self._access_token_lock = threading.Lock()

    def _has_required_conf(self) -> bool:
        return bool(self.conf.get('corp_id') and self.conf.get('corp_secret') and self.conf.get('agent_id'))

    def _build_token_url(self) -> str:
        return (
            f"{self.conf.get('proxy', 'https://qyapi.weixin.qq.com').rstrip('/')}/cgi-bin/gettoken"
            f"?corpid={self.conf.get('corp_id')}&corpsecret={self.conf.get('corp_secret')}"
        )

    def _build_send_url(self, access_token: str) -> str:
        return (
            f"{self.conf.get('proxy', 'https://qyapi.weixin.qq.com').rstrip('/')}/cgi-bin/message/send"
            f"?access_token={access_token}"
        )

    def _build_send_payload(self, title=None, message=None, image_url=None) -> dict:
        return {
            'touser': self.conf.get('to_user'),
            'msgtype': 'news',
            'agentid': self.conf.get('agent_id'),
            'news': {
                'articles': [
                    {
                        'title': title,
                        'description': message,
                        'url': '',
                        'picurl': image_url if self.conf.get('push_image') else None,
                    }
                ]
            }
        }

    def _clear_cached_token(self) -> None:
        self._access_token = None
        self._access_token_expire_at = 0.0

    def _has_valid_cached_token(self) -> bool:
        return bool(self._access_token) and time.time() < self._access_token_expire_at

    def _cache_access_token(self, access_token: str, expires_in) -> None:
        try:
            expires_in_seconds = int(expires_in)
        except (TypeError, ValueError):
            expires_in_seconds = DEFAULT_TOKEN_EXPIRES_IN
        self._access_token = access_token
        self._access_token_expire_at = time.time() + max(expires_in_seconds - ACCESS_TOKEN_REFRESH_BUFFER_SECONDS, 0)

    def _refresh_access_token(self) -> str | None:
        response = None
        try:
            response = requests.get(self._build_token_url(), timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response_data = response.json()
        except requests.RequestException:
            logger.exception(
                f"企业微信获取 access token 失败: status_code={getattr(response, 'status_code', '')}, "
                f"response_text={_truncate_response_text(response)}"
            )
            self._clear_cached_token()
            return None
        except ValueError:
            logger.exception(
                f"企业微信获取 access token 失败: status_code={getattr(response, 'status_code', '')}, "
                f"response_text={_truncate_response_text(response)}"
            )
            self._clear_cached_token()
            return None

        if response_data.get('errcode') != 0:
            logger.error(
                f"企业微信获取 access token 失败: errcode={response_data.get('errcode')}, errmsg={response_data.get('errmsg')}"
            )
            self._clear_cached_token()
            return None

        access_token = response_data.get('access_token')
        if not access_token:
            logger.error('企业微信获取 access token 失败: access_token 为空')
            self._clear_cached_token()
            return None

        self._cache_access_token(access_token, response_data.get('expires_in'))
        return access_token

    def get_access_token(self):
        if not self._has_required_conf():
            return None

        if self._has_valid_cached_token():
            return self._access_token

        with self._access_token_lock:
            if self._has_valid_cached_token():
                return self._access_token
            return self._refresh_access_token()

    def _send_once(self, access_token: str, title=None, message=None, image_url=None) -> dict | None:
        response = None
        try:
            response = requests.post(
                self._build_send_url(access_token),
                json=self._build_send_payload(title, message, image_url),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            logger.exception(
                f"企业微信推送失败: agent_id={self.conf.get('agent_id')}, to_user={self.conf.get('to_user')}, "
                f"status_code={getattr(response, 'status_code', '')}, response_text={_truncate_response_text(response)}"
            )
            return None
        except ValueError:
            logger.exception(
                f"企业微信推送失败: agent_id={self.conf.get('agent_id')}, to_user={self.conf.get('to_user')}, "
                f"status_code={getattr(response, 'status_code', '')}, response_text={_truncate_response_text(response)}"
            )
            return None

    def send(self, message=None, image_url=None, title=None, **kwargs):
        if not self._has_required_conf():
            return

        access_token = self.get_access_token()
        if not access_token:
            return

        response_data = self._send_once(access_token, title, message, image_url)
        if not response_data:
            return

        if response_data.get('errcode') == 0:
            return

        if response_data.get('errcode') in TOKEN_RETRY_ERRCODES:
            with self._access_token_lock:
                self._clear_cached_token()
                access_token = self._refresh_access_token()
            if not access_token:
                return

            retry_response_data = self._send_once(access_token, title, message, image_url)
            if not retry_response_data:
                return
            if retry_response_data.get('errcode') == 0:
                return

            logger.error(
                f"企业微信推送失败: errcode={retry_response_data.get('errcode')}, errmsg={retry_response_data.get('errmsg')}"
            )
            return

        logger.error(
            f"企业微信推送失败: errcode={response_data.get('errcode')}, errmsg={response_data.get('errmsg')}"
        )
