import requests

from app.enums import MediaServerEnum
from app.modules.mediaserver.base import BaseMediaServer
from app.utils.log import logger


class JellyfinMediaServer(BaseMediaServer):
    """
    Jellyfin 媒体服务器
    """

    name = MediaServerEnum.JELLYFIN.value

    def _build_url(self, path: str) -> str:
        base = (self.config.get("url") or "").rstrip("/")
        return f"{base}{path}"

    def has_movie_by_number(self, number: str) -> bool:
        if not self.config.get("url") or not self.config.get("api_key") or not number:
            return False

        try:
            user_id = self.config.get("user_id")
            if user_id:
                url = self._build_url(f"/Users/{user_id}/Items")
            else:
                url = self._build_url("/Items")

            params = {
                "SearchTerm": number,
                "Limit": 20,
                "Recursive": True,
                "api_key": self.config.get("api_key"),
            }

            resp = requests.get(url, params=params, timeout=10)
            if not resp:
                return False

            data = resp.json() or {}
            items = data.get("Items") or data.get("items") or []
            target = number.lower()

            for item in items:
                values = [
                    item.get("Name") or item.get("name") or "",
                    item.get("OriginalTitle") or item.get("originalTitle") or "",
                    item.get("Path") or item.get("path") or "",
                    item.get("FileName") or item.get("fileName") or "",
                ]
                combined = " ".join(str(value) for value in values if value).lower()
                if target in combined:
                    return True
            return False
        except Exception:
            logger.exception("")
            return False
