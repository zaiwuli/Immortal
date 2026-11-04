import importlib
import json
import os
import traceback
from collections import Counter
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

import app.models  # noqa: F401
from app.core.config import config_manager, root_path
from app.core.database import Base, engine, session_scope
from app.enums import DownloadClientEnum, PusherEnum, SystemConfigEnum
from app.migration.schema_sync import sync_schema
from app.migration.setup import upgrade
from app.models import Config
from app.utils.log import logger


ROUTER_SPECS = [
    ('app.api.v1.tools', '/api/v1/tools', ['tools']),
    ('app.api.v1.article', '/api/v1/articles', ['article']),
    ('app.api.v1.user', '/api/v1/users', ['user']),
    ('app.api.v1.config', '/api/v1/config', ['config']),
    ('app.api.v1.task', '/api/v1/tasks', ['task']),
    ('app.api.v1.download_log', '/api/v1/download-log', ['download-log']),
    ('app.api.v1.rule', '/api/v1/rules', ['rule']),
    ('app.api.v1.token', '/api/v1/tokens', ['token']),
    ('app.api.v1.img_proxy', '/api/v1/img-proxy', ['img-proxy']),
    ('app.api.v1.log', '/api/v1/logs', ['logs']),
    ('app.api.v1.rank', '/api/v1/rank', ['rank']),
    ('app.api.v1.movie', '/api/v1/movies', ['movies']),
    ('app.api.v1.cast', '/api/v1/casts', ['casts']),
    ('app.api.v1.filter', '/api/v1/filters', ['filters']),
    ('app.api.v1.priority', '/api/v1/priorities', ['priorities']),
    ('app.api.v1.subscribe', '/api/v1/subscribes', ['subscribes']),
]


DOWNLOAD_CLIENT_SPECS = {
    DownloadClientEnum.TOOLS115.value: ('app.modules.downloadclient.tools115', 'Tools115'),
    DownloadClientEnum.QBITTORRENT.value: ('app.modules.downloadclient.qbittorrent', 'QBitTorrentClient'),
    DownloadClientEnum.TRANSMISSION.value: ('app.modules.downloadclient.transmission', 'TransmissionClient'),
    DownloadClientEnum.THUNDER.value: ('app.modules.downloadclient.thunder', 'Thunder'),
    DownloadClientEnum.CLOUDDRIVE.value: ('app.modules.downloadclient.cloudnas.cloudnas', 'CloudNas'),
}


PUSHER_SPECS = {
    PusherEnum.WECHAT.value: ('app.modules.notification.wechat', 'WeChatNotifier'),
    PusherEnum.TELEGRAM.value: ('app.modules.notification.telegram', 'TelegramNotifier'),
    PusherEnum.DISCORD.value: ('app.modules.notification.discord', 'DiscordNotifier'),
}


DIST_DIR = os.path.join(root_path, 'frontend', 'dist')


def _safe_import(module_path: str):
    try:
        return importlib.import_module(module_path)
    except Exception:
        logger.exception(f'模块加载失败，已跳过 | module={module_path}')
        return None


def _safe_call(label: str, func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        logger.exception(f'启动步骤执行失败，已跳过 | step={label}')
        return None


def ensure_database_schema(bind=None):
    Base.metadata.create_all(bind=bind or engine)


def _log_schema_drift(drift):
    total_count = len(drift)
    applied_items = [item for item in drift if getattr(item, 'applied', False)]
    pending_items = [item for item in drift if not getattr(item, 'applied', False)]
    kind_counter = Counter(item.kind for item in drift)
    applied_counter = Counter(item.kind for item in applied_items)
    pending_counter = Counter(item.kind for item in pending_items)

    kind_text = ', '.join(f'{kind}={count}' for kind, count in sorted(kind_counter.items())) or 'none'
    logger.info(
        f'数据库结构检查完成 | drift_count={total_count}, applied_count={len(applied_items)}, '
        f'pending_count={len(pending_items)}, kinds={kind_text}'
    )

    for kind in sorted(kind_counter):
        items = [item for item in drift if item.kind == kind]
        examples = ', '.join(f'{item.table}.{item.name}' for item in items[:5])
        logger.info(
            f'数据库结构漂移明细 | kind={kind}, total={kind_counter[kind]}, '
            f'applied={applied_counter.get(kind, 0)}, pending={pending_counter.get(kind, 0)}, '
            f'examples={examples or "none"}'
        )

    if pending_items:
        for item in pending_items[:20]:
            logger.warning(
                f'数据库结构未自动修复 | kind={item.kind}, target={item.table}.{item.name}, detail={item.detail or ""}'
            )
        if len(pending_items) > 20:
            logger.warning(f'数据库结构未自动修复项过多，已省略其余 {len(pending_items) - 20} 条')



def repair_database_schema():
    drift = sync_schema(apply=True)
    if not drift:
        logger.info('数据库结构检查完成，未发现可修复项')
        return []

    _log_schema_drift(drift)
    return drift


def load_system_config():
    with session_scope() as session:
        config = session.query(Config).filter(Config.key == SystemConfigEnum.SYSTEM_CONFIG.value).first()
        if config and config.content:
            system_config = json.loads(config.content)
            config_manager.reload(system_config)


def load_downloader_manager():
    manager_module = _safe_import('app.modules.downloadclient.manager')
    if manager_module is None:
        return
    download_manager = getattr(manager_module, 'downloadManager', None)
    if download_manager is None:
        logger.warning('下载器管理器不可用，已跳过加载')
        return

    with session_scope() as session:
        configs = session.query(Config).filter(Config.key.ilike('Downloader.%')).all()
        for config in configs:
            spec = DOWNLOAD_CLIENT_SPECS.get(config.key)
            if not spec:
                continue
            module = _safe_import(spec[0])
            if module is None:
                continue
            client_cls = getattr(module, spec[1], None)
            if client_cls is None:
                logger.warning(f'下载器类不存在，已跳过 | key={config.key}, class={spec[1]}')
                continue
            try:
                download_manager.register(client_cls(json.loads(config.content)))
            except Exception:
                logger.exception(f'下载器注册失败，已跳过 | key={config.key}')


def load_pusher_manager():
    manager_module = _safe_import('app.modules.notification.manager')
    if manager_module is None:
        return
    push_manager = getattr(manager_module, 'pushManager', None)
    if push_manager is None:
        logger.warning('推送管理器不可用，已跳过加载')
        return

    with session_scope() as session:
        configs = session.query(Config).filter(Config.key.ilike('Notification.%')).all()
        for config in configs:
            spec = PUSHER_SPECS.get(config.key)
            if not spec:
                continue
            module = _safe_import(spec[0])
            if module is None:
                continue
            notifier_cls = getattr(module, spec[1], None)
            if notifier_cls is None:
                logger.warning(f'推送器类不存在，已跳过 | key={config.key}, class={spec[1]}')
                continue
            try:
                push_manager.register(notifier_cls(json.loads(config.content)))
            except Exception:
                logger.exception(f'推送器注册失败，已跳过 | key={config.key}')


def load_media_server_manager():
    media_module = _safe_import('app.modules.mediaserver')
    if media_module is None:
        return
    media_server_manager = getattr(media_module, 'mediaServerManager', None)
    if media_server_manager is None:
        logger.warning('媒体库管理器不可用，已跳过加载')
        return

    with session_scope() as session:
        configs = session.query(Config).filter(Config.key.ilike('MediaServer.%')).all()
        for config in configs:
            try:
                media_server_manager.reload(config.key, json.loads(config.content))
            except Exception:
                logger.exception(f'媒体库配置加载失败，已跳过 | key={config.key}')


def include_routers(app: FastAPI):
    for module_path, prefix, tags in ROUTER_SPECS:
        module = _safe_import(module_path)
        if module is None:
            continue
        router = getattr(module, 'router', None)
        if router is None:
            logger.warning(f'路由对象不存在，已跳过 | module={module_path}')
            continue
        app.include_router(router, prefix=prefix, tags=tags)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_database_schema()
    _safe_call('upgrade', upgrade)
    repair_database_schema()
    from app.migration.access_tokens import migrate_access_tokens
    migrate_access_tokens()
    _safe_call('load_system_config', load_system_config)
    _safe_call('load_downloader_manager', load_downloader_manager)
    _safe_call('load_pusher_manager', load_pusher_manager)
    _safe_call('load_media_server_manager', load_media_server_manager)

    scheduler_module = _safe_import('app.scheduler')
    if scheduler_module is not None:
        _safe_call('start_scheduler', getattr(scheduler_module, 'start_scheduler'))

    logger.success('服务已启动 http://127.0.0.1:8000')
    from app.core.version import get_current_version
    logger.success(f'当前版本号:{get_current_version()}')
    yield

    if scheduler_module is not None:
        scheduler = getattr(scheduler_module, 'scheduler', None)
        if scheduler is not None and getattr(scheduler, 'running', False):
            _safe_call('scheduler_shutdown', scheduler.shutdown, wait=True)


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.middleware('http')
async def prepare_request_and_audit(request: Request, call_next):
    # Inspect the config namespace before checking a POST config permission.
    if request.method == 'POST' and request.url.path.rstrip('/') == '/api/v1/config':
        try:
            request.state.config_key = (await request.json()).get('key', '')
        except (ValueError, AttributeError):
            return JSONResponse(status_code=422, content={'detail': 'Invalid config payload'})
    response = await call_next(request)
    token_id = getattr(request.state, 'token_id', None)
    if token_id:
        from app.models.token import TokenAudit
        try:
            with session_scope() as db:
                db.add(TokenAudit(token_id=token_id, method=request.method, path=request.url.path, status_code=response.status_code))
        except Exception:
            logger.exception('令牌操作记录写入失败')
    return response

include_routers(app)

if os.path.isdir(DIST_DIR):
    app.mount('/', StaticFiles(directory=DIST_DIR), name='frontend')
else:
    logger.warning(f'前端静态目录不存在，已跳过挂载 | dir={DIST_DIR}')


@app.exception_handler(StarletteHTTPException)
async def not_found_exception_handler(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith('/api'):
        return JSONResponse(
            status_code=exc.status_code,
            content={'code': exc.status_code, 'message': exc.detail},
        )

    if os.path.isdir(DIST_DIR):
        return FileResponse(os.path.join(DIST_DIR, 'index.html'))
    return JSONResponse(status_code=404, content={'code': 404, 'message': exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={'code': 500, 'message': 'internal server error', 'data': None},
    )


@app.get('/')
async def read_index():
    if os.path.isdir(DIST_DIR):
        return FileResponse(os.path.join(DIST_DIR, 'index.html'))
    return JSONResponse(status_code=404, content={'code': 404, 'message': 'frontend dist not found'})
