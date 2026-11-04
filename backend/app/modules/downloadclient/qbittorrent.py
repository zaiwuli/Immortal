import qbittorrentapi
from qbittorrentapi.exceptions import Forbidden403Error, LoginFailed, Unauthorized401Error

from app import utils
from app.enums import DownloadClientEnum
from app.modules.downloadclient.base import BaseDownloader
from app.utils.log import logger


class QBitTorrentClient(BaseDownloader):
    config: dict = None
    name = DownloadClientEnum.QBITTORRENT.value
    anti_leech: bool = True
    client: qbittorrentapi.Client = None
    AUTH_ERRORS = (LoginFailed, Unauthorized401Error, Forbidden403Error)

    def __init__(self, conf):
        self.config = conf

    def _reset_client(self):
        self.client = None

    def login_qb(self, force=False):
        if force:
            self._reset_client()

        if self.client is not None:
            return True

        if self.config.get('url') and self.config.get('username') and self.config.get('password'):
            self.client = qbittorrentapi.Client(
                host=self.config.get('url'),
                username=self.config.get('username'),
                password=self.config.get('password')
            )
            try:
                self.client.auth_log_in()
                return True
            except Exception:
                logger.exception(self.build_log_context('login', url=self.config.get('url')))
                self._reset_client()
        return False

    def _call_with_relogin(self, action: str, callback, **context):
        try:
            return callback()
        except self.AUTH_ERRORS:
            logger.warning(self.build_log_context(action, retry='relogin', reason='auth_session', **context))
            if not self.login_qb(force=True):
                raise
            return callback()

    def _wait_for_torrent_files(self, torrent_hash, timeout=BaseDownloader.DEFAULT_POLL_TIMEOUT):
        def fetch_files():
            try:
                return self._call_with_relogin(
                    'fetch_torrent_files',
                    lambda: self.client.torrents_files(torrent_hash),
                    hash=torrent_hash,
                )
            except Exception:
                logger.exception(self.build_log_context('fetch_torrent_files', hash=torrent_hash))
                return None

        files_info = self.wait_until(
            fetcher=fetch_files,
            predicate=lambda files: bool(files),
            timeout=timeout,
        )
        return files_info or []

    def _wait_for_torrent_size(self, torrent_hash, timeout=BaseDownloader.DEFAULT_POLL_TIMEOUT):
        def fetch_torrent():
            try:
                torrents = self._call_with_relogin(
                    'fetch_torrent_info',
                    lambda: self.client.torrents_info(torrent_hashes=torrent_hash),
                    hash=torrent_hash,
                )
                return torrents[0] if torrents else None
            except Exception:
                logger.exception(self.build_log_context('fetch_torrent_info', hash=torrent_hash))
                return None

        return self.wait_until(
            fetcher=fetch_torrent,
            predicate=lambda torrent: bool(torrent and getattr(torrent, 'total_size', 0) > 0),
            timeout=timeout,
        )

    def download(self, magnet, save_path) -> tuple[bool, str | None]:
        if not self.login_qb():
            return False, '无法连接到 qBittorrent，请检查配置'

        try:
            logger.info(self.build_log_context('add_magnet', magnet=magnet, save_path=save_path))
            self._call_with_relogin(
                'add_magnet',
                lambda: self.client.torrents_add(
                    urls=magnet,
                    save_path=save_path,
                    seeding_time_limit=0 if self.anti_leech else None,
                ),
                magnet=magnet,
                save_path=save_path,
            )
            torrent_hash = utils.extract_infohash(magnet)
            if not torrent_hash:
                logger.warning(self.build_log_context('extract_info_hash', magnet=magnet, result='empty'))
                return True, None

            files_info = self._wait_for_torrent_files(torrent_hash)
            small_file_ids = self.collect_small_file_ids(
                files_info,
                size_getter=lambda file_info: file_info.get('size') if isinstance(file_info, dict) else None,
                id_getter=lambda file_info: file_info.get('index') if isinstance(file_info, dict) else None,
            )

            if small_file_ids:
                self._call_with_relogin(
                    'set_file_priority',
                    lambda: self.client.torrents_file_priority(torrent_hash, small_file_ids, 0),
                    hash=torrent_hash,
                    file_count=len(small_file_ids),
                )
            elif not files_info:
                logger.warning(self.build_log_context('fetch_torrent_files_timeout', hash=torrent_hash))
            return True, None
        except Exception:
            logger.exception(self.build_log_context('download', magnet=magnet, save_path=save_path))
            return False, 'qBittorrent 添加任务失败'

    def analyze_size(self, magnet: str):
        info_hash = utils.extract_infohash(magnet)
        if not (self.login_qb() and info_hash):
            return None

        torrent = None
        try:
            self._call_with_relogin(
                'add_analyze_torrent',
                lambda: self.client.torrents_add(
                    urls=magnet,
                    paused=True,
                    skip_checking=True,
                    save_path='/analyze_size_temp'
                ),
                magnet=magnet,
                hash=info_hash,
            )
            torrent = self._wait_for_torrent_size(info_hash)
            if torrent:
                return int(torrent.total_size / 1000 / 1000)
        except Exception:
            logger.exception(self.build_log_context('analyze_size', magnet=magnet, hash=info_hash))
        finally:
            try:
                self._call_with_relogin(
                    'cleanup_analyze_torrent',
                    lambda: self.client.torrents_delete(
                        torrent_hashes=info_hash,
                        delete_files=True,
                    ),
                    hash=info_hash,
                )
            except Exception:
                logger.exception(self.build_log_context('cleanup_analyze_torrent', hash=info_hash))
        return None
