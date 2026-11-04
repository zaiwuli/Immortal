from urllib.parse import urlencode

import requests

from app.enums import MediaServerEnum
from app.modules.mediaserver.base import BaseMediaServer
from app.utils.log import logger


class PlexMediaServer(BaseMediaServer):
    """
    Plex 媒体服务器
    """

    name = MediaServerEnum.PLEX.value

    def _build_url(self, path: str, query: dict | None = None) -> str:
        base = (self.config.get("url") or "").rstrip("/")
        url = f"{base}{path}"
        if query:
            qs = urlencode(query)
            url = f"{url}?{qs}"
        return url

    def has_movie_by_number(self, number: str) -> bool:
        if not self.config.get("url") or not self.config.get("token") or not number:
            return False

        try:
            library_id = self.config.get("library_id")
            query = {
                "query": number,
                "X-Plex-Token": self.config.get("token"),
            }

            if library_id:
                path = f"/library/sections/{library_id}/all"
            else:
                path = "/search"

            url = self._build_url(path, query)
            resp = requests.get(url, timeout=10)
            if not resp:
                return False

            text = (resp.text or "").lower()
            return number.lower() in text
        except Exception:
            logger.exception("")
            return False
