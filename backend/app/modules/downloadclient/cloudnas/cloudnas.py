import posixpath

import grpc

from app import utils
from app.enums import DownloadClientEnum
from app.modules.downloadclient.base import BaseDownloader
from app.modules.downloadclient.cloudnas import clouddrive_pb2
from app.modules.downloadclient.cloudnas import clouddrive_pb2_grpc
from app.utils.log import logger


class CloudNas(BaseDownloader):
    config: dict = None
    name = DownloadClientEnum.CLOUDDRIVE.value
    stub = None
    jwt_token = None
    channel = None
    AUTH_ERRORS = {grpc.StatusCode.UNAUTHENTICATED, grpc.StatusCode.PERMISSION_DENIED}

    def __init__(self, conf):
        self.jwt_token = None
        self.config = conf
        self.channel = None
        self.stub = None
        self._init_client()

    def _init_client(self):
        options = [
            ('grpc.enable_http_proxy', 0),
        ]
        url = self.config.get('url')
        if not url:
            return

        self.channel = grpc.insecure_channel(utils.get_host_port(url), options=options)
        self.stub = clouddrive_pb2_grpc.CloudDriveFileSrvStub(self.channel)

        token = self.config.get('token')
        if token:
            self.jwt_token = token
            return

        username = self.config.get('username')
        password = self.config.get('password')
        if username and password:
            self.authenticate(username, password)

    def _reset_client(self):
        self.jwt_token = None if not self.config.get('token') else self.config.get('token')
        self.stub = None
        self.channel = None
        self._init_client()

    def _can_reauth(self):
        return bool(self.config.get('username') and self.config.get('password'))

    @classmethod
    def _is_auth_error(cls, exc: Exception) -> bool:
        return isinstance(exc, grpc.RpcError) and exc.code() in cls.AUTH_ERRORS

    def _call_with_reauth(self, action: str, callback, **context):
        try:
            return callback()
        except Exception as exc:
            if not self._is_auth_error(exc):
                raise
            logger.warning(self.build_log_context(action, retry='relogin', reason='auth_session', **context))
            if not self._can_reauth():
                raise
            self._reset_client()
            if not self.jwt_token:
                raise
            return callback()

    def authenticate(self, username, password):
        if not self.stub:
            logger.error(self.build_log_context('authenticate', reason='stub_unavailable'))
            return False

        request = clouddrive_pb2.GetTokenRequest(userName=username, password=password)
        try:
            response = self.stub.GetToken(request)
        except Exception:
            logger.exception(self.build_log_context('authenticate', url=self.config.get('url')))
            return False

        if response.success and response.token:
            self.jwt_token = response.token
            logger.success(self.build_log_context('authenticate', result='success', expiration=response.expiration))
            return True
        logger.error(self.build_log_context('authenticate', result='failed', error=response.errorMessage))
        return False

    def _create_authorized_metadata(self):
        if not self.jwt_token:
            return []
        return [('authorization', f'Bearer {self.jwt_token}')]

    def download(self, magnets, save_path) -> tuple[bool, str | None]:
        if not self.stub:
            logger.error(self.build_log_context('download', magnet=magnets, save_path=save_path, reason='stub_unavailable'))
            return False, '无法连接到 CloudDrive，请检查配置'
        if not self.jwt_token:
            logger.error(self.build_log_context('download', magnet=magnets, save_path=save_path, reason='token_unavailable'))
            return False, 'CloudDrive 认证失败，请检查 Token'
        if not save_path:
            logger.error(self.build_log_context('download', magnet=magnets, reason='save_path_empty'))
            return False, '保存路径为空'

        self.create_folder(save_path)
        logger.info(self.build_log_context('add_offline_download', magnet=magnets, save_path=save_path))
        request = clouddrive_pb2.AddOfflineFileRequest(urls=magnets, toFolder=save_path)
        try:
            response = self._call_with_reauth(
                'add_offline_download',
                lambda: self.stub.AddOfflineFiles(request, metadata=self._create_authorized_metadata()),
                magnet=magnets,
                save_path=save_path,
            )
            if response.success:
                return True, None
            logger.error(self.build_log_context('add_offline_download', magnet=magnets, save_path=save_path, reason='rejected'))
            return False, 'CloudDrive 拒绝了离线下载请求'
        except Exception:
            logger.exception(self.build_log_context('add_offline_download', magnet=magnets, save_path=save_path))
            return False, 'CloudDrive 添加任务失败'

    def create_sub_folder(self, parent_path, folder_name):
        if not self.stub or not self.jwt_token:
            logger.error(self.build_log_context('create_sub_folder', parent_path=parent_path, folder_name=folder_name, reason='auth_unavailable'))
            return False
        if not folder_name:
            logger.error(self.build_log_context('create_sub_folder', parent_path=parent_path, reason='folder_name_empty'))
            return False

        request = clouddrive_pb2.CreateFolderRequest(parentPath=parent_path, folderName=folder_name)
        try:
            self._call_with_reauth(
                'create_sub_folder',
                lambda: self.stub.CreateFolder(request, metadata=self._create_authorized_metadata()),
                parent_path=parent_path,
                folder_name=folder_name,
            )
            return True
        except grpc.RpcError as exc:
            if exc.code() == grpc.StatusCode.ALREADY_EXISTS:
                return True
            logger.exception(self.build_log_context('create_sub_folder', parent_path=parent_path, folder_name=folder_name))
        except Exception:
            logger.exception(self.build_log_context('create_sub_folder', parent_path=parent_path, folder_name=folder_name))
        return False

    def create_folder(self, save_path):
        if not self.stub or not self.jwt_token:
            logger.error(self.build_log_context('create_folder', save_path=save_path, reason='auth_unavailable'))
            return False

        save_path = posixpath.normpath(save_path)
        if save_path in ('', '.'):
            logger.error(self.build_log_context('create_folder', save_path=save_path, reason='invalid_path'))
            return False
        if save_path == '/':
            return True

        parts = [p for p in save_path.split('/') if p]
        parent_path = '/'
        for part in parts:
            if not self.create_sub_folder(parent_path, part):
                return False
            parent_path = posixpath.join(parent_path, part)
        return True

    def analyze_size(self, magnet: str):
        return None
