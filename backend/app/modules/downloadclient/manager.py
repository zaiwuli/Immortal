from typing import List
from app.modules.downloadclient.tools115 import Tools115

from app.enums import DownloadClientEnum
from app.modules.downloadclient.base import BaseDownloader
from app.modules.downloadclient.cloudnas.cloudnas import CloudNas
from app.modules.downloadclient.qbittorrent import QBitTorrentClient
from app.modules.downloadclient.thunder import Thunder
from app.modules.downloadclient.transmission import TransmissionClient
from app.utils.log import logger


class DownloadManager:
    def __init__(self):
        self.downloaders: List[BaseDownloader] = []

    def register(self, downloader: BaseDownloader):
        self.downloaders.append(downloader)

    def download(self, downloader_name, magnet, save_path) -> tuple[bool, str | None]:
        is_edk = isinstance(magnet, str) and magnet.startswith('ed2k://')
        if is_edk and downloader_name not in [DownloadClientEnum.THUNDER.value, DownloadClientEnum.CLOUDDRIVE.value, DownloadClientEnum.TOOLS115.value]:
            logger.warning(f'action=download | client={downloader_name} | magnet={magnet} | reason=edk_not_supported')
            return False, 'ed2k 链接不支持该下载器'
        for downloader in self.downloaders:
            if downloader_name == downloader.name:
                return downloader.download(magnet, save_path)
        logger.error(f'action=download | client={downloader_name} | magnet={magnet} | save_path={save_path} | reason=downloader_not_found')
        return False, f'下载器 {downloader_name} 未找到'

    def analyze_size(self, magnet):
        self.downloaders.sort(
            key=lambda downloader: 0 if downloader.name == DownloadClientEnum.THUNDER.value else 1
        )
        for downloader in self.downloaders:
            size = downloader.analyze_size(magnet)
            if size:
                return size
        logger.warning(f'action=analyze_size | magnet={magnet} | reason=all_downloaders_failed')
        return None

    def reload(self, name, config: dict):
        self.downloaders = [downloader for downloader in self.downloaders if downloader.name != name]
        if name == DownloadClientEnum.TOOLS115.value:
            self.register(Tools115(config))
        if name == DownloadClientEnum.QBITTORRENT.value:
            self.register(QBitTorrentClient(config))
        if name == DownloadClientEnum.TRANSMISSION.value:
            self.register(TransmissionClient(config))
        if name == DownloadClientEnum.THUNDER.value:
            self.register(Thunder(config))
        if name == DownloadClientEnum.CLOUDDRIVE.value:
            self.register(CloudNas(config))


downloadManager = DownloadManager()
