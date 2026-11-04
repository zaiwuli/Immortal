import json

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.config import config_manager
from app.enums import DownloadClientEnum, PusherEnum, SystemConfigEnum, MediaServerEnum
from app.api.services import subscribe_preference_service
from app.models import Config
from app.modules.downloadclient.manager import downloadManager
from app.modules.mediaserver import mediaServerManager
from app.modules.notification.manager import pushManager
from app.schemas.config import JsonPayload
from app.schemas.response import success


REMOVED_KEYS = {'PageAgentConfig', 'TGBotConfig', 'DiscordBotConfig', 'WeComBotConfig'}

def ensure_supported(key):
    if key in REMOVED_KEYS: raise HTTPException(410, '该功能已移除')

def save_option(json_payload: JsonPayload, db: Session):
    ensure_supported(json_payload.key)
    key = json_payload.key
    payload = json_payload.payload
    if key == SystemConfigEnum.SUBSCRIBE_PREFERENCE_CONFIG.value:
        payload = subscribe_preference_service.normalize_subscribe_preference_config(payload)
    config = db.query(Config).filter(Config.key == key).first()
    if config is None:
        config = Config()
        config.key = key
        config.content = json.dumps(payload)
        db.add(config)
    else:
        config.content = json.dumps(payload)

    if json_payload.key in [item.value for item in DownloadClientEnum]:
        downloadManager.reload(json_payload.key, payload)
    if json_payload.key in [item.value for item in PusherEnum]:
        pushManager.reload(json_payload.key, payload)
    if json_payload.key in [item.value for item in MediaServerEnum]:
        mediaServerManager.reload(json_payload.key, payload)
    if json_payload.key == SystemConfigEnum.SYSTEM_CONFIG.value:
        config_manager.reload(payload)
    return success()


def get_option(key, db: Session):
    ensure_supported(key)
    config = db.query(Config).filter(Config.key == key).first()
    if config:
        data = json.loads(str(config.content))
        if key == SystemConfigEnum.SUBSCRIBE_PREFERENCE_CONFIG.value:
            data = subscribe_preference_service.normalize_subscribe_preference_config(data)
        return success(data)
    return success()


def delete_option(key, db: Session):
    ensure_supported(key)
    config = db.query(Config).filter(Config.key == key).first()
    if config:
        if key.startswith("Downloader."):
            downloadManager.downloaders = [d for d in downloadManager.downloaders if d.name != key]
        db.delete(config)
    return success()


def list_all_downloader(db: Session):
    configs = db.query(Config).filter(Config.key.ilike('Downloader.%')).all()
    downloaders = []
    for config in configs:
        content = config.content
        downloader = json.loads(str(content))
        if downloader.get("save_paths"):
            downloaders.append({'id': config.key.replace('Downloader.', ''), 'save_paths': downloader['save_paths']})
    return success(downloaders)
