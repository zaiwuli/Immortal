from typing import List

from app.enums import MediaServerEnum
from app.modules.mediaserver.base import BaseMediaServer
from app.modules.mediaserver.emby import EmbyMediaServer
from app.modules.mediaserver.jellyfin import JellyfinMediaServer
from app.modules.mediaserver.plex import PlexMediaServer
from app.modules.mediaserver.zspace import ZSpaceMediaServer


class MediaServerManager:
    """
    媒体服务器管理器，统一查询接口
    """

    def __init__(self):
        self.servers: List[BaseMediaServer] = []

    def register(self, server: BaseMediaServer):
        self.servers.append(server)

    def any_movie_exists_by_number(self, number: str) -> bool:
        """
        查询番号是否存在于媒体库
        """
        if not number:
            return False

        for server in self.servers:
            if server.has_movie_by_number(number):
                return True
        return False

    def reload(self, name: str, config: dict):
        """
        根据名称重建并替换对应的媒体服务器实例
        """
        for server in list(self.servers):
            if server.name == name:
                self.servers.remove(server)

        if name == MediaServerEnum.EMBY.value:
            self.register(EmbyMediaServer(config))
        if name == MediaServerEnum.JELLYFIN.value:
            self.register(JellyfinMediaServer(config))
        if name == MediaServerEnum.PLEX.value:
            self.register(PlexMediaServer(config))
        if name == MediaServerEnum.ZSPACE.value:
            self.register(ZSpaceMediaServer(config))


mediaServerManager = MediaServerManager()
