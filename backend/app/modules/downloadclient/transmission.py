import transmission_rpc
from transmission_rpc.error import TransmissionAuthError

from app import utils
from app.enums import DownloadClientEnum
from app.modules.downloadclient.base import BaseDownloader
from app.utils.log import logger


class TransmissionClient(BaseDownloader):
    config: dict = None
    name = DownloadClientEnum.TRANSMISSION.value
    client: transmission_rpc.Client = None
    anti_leech: bool = True
    AUTH_ERRORS = (TransmissionAuthError,)

    def __init__(self, conf):
        self.config = conf

    def _reset_client(self):
        self.client = None

    @staticmethod
    def _get_torrent_files(torrent_info):
        get_files = getattr(torrent_info, 'get_files', None)
        if callable(get_files):
            return get_files()

        legacy_files = getattr(torrent_info, 'files', None)
        if callable(legacy_files):
            return legacy_files()
        if isinstance(legacy_files, list):
            return legacy_files
        return []

    def login_transmission(self, force=False):
        if force:
            self._reset_client()

        if self.client is not None:
            return True

        if self.config.get('url') and self.config.get('username') and self.config.get('password'):
            host, port = utils.get_host_and_port(self.config.get('url'))
            try:
                self.client = transmission_rpc.Client(
                    host=host,
                    port=port,
                    username=self.config.get('username'),
                    password=self.config.get('password')
                )
                self.client.session_stats()
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
            if not self.login_transmission(force=True):
                raise
            return callback()

    def _get_torrent(self, torrent_hash, arguments=None):
        return self._call_with_relogin(
            'fetch_torrent',
            lambda: self.client.get_torrent(
                torrent_hash,
                arguments=arguments or ['id', 'files', 'priorities', 'wanted', 'metadataPercentComplete'],
            ),
            hash=torrent_hash,
        )

    def _wait_for_torrent_info(self, torrent_hash, timeout=BaseDownloader.DEFAULT_POLL_TIMEOUT):
        def fetch_torrent():
            try:
                return self._get_torrent(torrent_hash)
            except Exception:
                logger.exception(self.build_log_context('fetch_torrent_info', hash=torrent_hash))
                return None

        return self.wait_until(
            fetcher=fetch_torrent,
            predicate=lambda torrent: torrent is not None,
            timeout=timeout,
        )

    def _wait_for_torrent_files(self, torrent_hash, timeout=BaseDownloader.DEFAULT_POLL_TIMEOUT):
        def fetch_torrent():
            try:
                return self._get_torrent(torrent_hash)
            except Exception:
                logger.exception(self.build_log_context('fetch_torrent_files', hash=torrent_hash))
                return None

        torrent_info = self.wait_until(
            fetcher=fetch_torrent,
            predicate=lambda torrent: bool(
                torrent and (
                    self._get_torrent_files(torrent)
                    or getattr(torrent, 'metadata_percent_complete', 0) == 1
                )
            ),
            timeout=timeout,
        )
        if not torrent_info:
            return None, []
        return torrent_info, self._get_torrent_files(torrent_info)

    def _wait_for_torrent_size(self, torrent_hash, timeout=BaseDownloader.DEFAULT_POLL_TIMEOUT):
        def fetch_torrent():
            try:
                return self._call_with_relogin(
                    'fetch_torrent_size',
                    lambda: self.client.get_torrent(torrent_hash),
                    hash=torrent_hash,
                )
            except Exception:
                logger.exception(self.build_log_context('fetch_torrent_size', hash=torrent_hash))
                return None

        return self.wait_until(
            fetcher=fetch_torrent,
            predicate=lambda torrent: bool(torrent and getattr(torrent, 'total_size', 0) > 0),
            timeout=timeout,
        )

    def download(self, magnet, save_path) -> tuple[bool, str | None]:
        if not self.login_transmission():
            return False, '无法连接到 Transmission，请检查配置'

        try:
            logger.info(self.build_log_context('add_magnet', magnet=magnet, save_path=save_path))
            self._call_with_relogin(
                'add_magnet',
                lambda: self.client.add_torrent(torrent=magnet, download_dir=save_path),
                magnet=magnet,
                save_path=save_path,
            )
            torrent_hash = utils.extract_infohash(magnet)
            if not torrent_hash:
                logger.warning(self.build_log_context('extract_info_hash', magnet=magnet, result='empty'))
                return True, None

            torrent_info = self._wait_for_torrent_info(torrent_hash)
            if not torrent_info:
                logger.warning(self.build_log_context('fetch_torrent_info_timeout', hash=torrent_hash))
                return True, None

            torrent_id = torrent_info.id
            torrent_info, torrent_files = self._wait_for_torrent_files(torrent_hash)
            if not torrent_files:
                logger.warning(self.build_log_context('fetch_torrent_files_timeout', hash=torrent_hash))

            small_file_ids = self.collect_small_file_ids(
                torrent_files,
                size_getter=lambda file_info: getattr(file_info, 'size', None),
                id_getter=lambda file_info: getattr(file_info, 'id', None),
            )

            if small_file_ids or self.anti_leech:
                change_kwargs = {'ids': [torrent_id]}
                if small_file_ids:
                    change_kwargs['files_unwanted'] = small_file_ids
                if self.anti_leech:
                    change_kwargs['seed_ratio_limit'] = 0
                self._call_with_relogin(
                    'change_torrent_settings',
                    lambda: self.client.change_torrent(**change_kwargs),
                    hash=torrent_hash,
                    file_count=len(small_file_ids),
                    anti_leech=self.anti_leech,
                )
            return True, None
        except Exception:
            logger.exception(self.build_log_context('download', magnet=magnet, save_path=save_path))
            return False, 'Transmission 添加任务失败'

    def analyze_size(self, magnet: str):
        info_hash = utils.extract_infohash(magnet)
        if not (self.login_transmission() and info_hash):
            return None

        torrent = None
        torrent_id = None
        try:
            added_torrent = self._call_with_relogin(
                'add_analyze_torrent',
                lambda: self.client.add_torrent(magnet, paused=True),
                magnet=magnet,
                hash=info_hash,
            )
            torrent_id = getattr(added_torrent, 'id', None)
            torrent = self._wait_for_torrent_size(info_hash)
            if torrent:
                torrent_id = torrent.id
                return int(torrent.total_size / 1000 / 1000)
        except Exception:
            logger.exception(self.build_log_context('analyze_size', magnet=magnet, hash=info_hash))
        finally:
            try:
                remove_target = torrent_id or info_hash
                self._call_with_relogin(
                    'cleanup_analyze_torrent',
                    lambda: self.client.remove_torrent(remove_target, delete_data=False),
                    hash=info_hash,
                    torrent_id=torrent_id,
                )
            except Exception:
                logger.exception(self.build_log_context('cleanup_analyze_torrent', hash=info_hash, torrent_id=torrent_id))
        return None
