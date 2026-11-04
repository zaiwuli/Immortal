import uuid
from urllib.parse import urlparse, quote
import requests
from app.modules.downloadclient.base import BaseDownloader

class Tools115(BaseDownloader):
    name = 'Downloader.tools115'
    def __init__(self, config):
        self.config = config

    def call(self, method, path, **kwargs):
        base = str(self.config.get('url', '')).rstrip('/')
        parsed = urlparse(base)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError('请配置有效的 HTTP/HTTPS 服务地址')
        token = self.config.get('api_token')
        if not token: raise ValueError('请配置 115tools API 令牌')
        headers = {'Authorization': 'Bearer ' + token, **kwargs.pop('headers', {})}
        with requests.request(method, base + path, headers=headers, timeout=30, allow_redirects=False, **kwargs) as response:
            if not 200 <= response.status_code < 300:
                raise ValueError(f'115tools 请求失败，HTTP {response.status_code}')
            return response.json()

    def submit(self, text, idempotency_key):
        return self.call('POST', '/api/v1/offline/import', json={'text': text, 'auto_extract': self.config.get('auto_extract', True)}, headers={'Idempotency-Key': idempotency_key})

    def download(self, magnet, save_path):
        # Each business submission has one key; no automatic unsafe retry.
        try:
            result = self.submit(magnet, str(uuid.uuid4()))
            if result.get('queued', 0) > 0 or result.get('duplicates', 0) > 0:
                return True, None
            return False, '未登记任务，请检查链接是否有效'
        except (requests.RequestException, ValueError):
            return False, '115tools 提交失败或结果未知，请先在工具后台核实，再决定是否重新提交'

    def analyze_size(self, magnet):
        return None
