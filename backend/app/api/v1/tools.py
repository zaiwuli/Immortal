import json
import uuid
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Config
from app.modules.downloadclient.tools115 import Tools115
from app.schemas.response import success
router = APIRouter(dependencies=[Depends(get_current_user)])

def client(db):
    config = db.query(Config).filter(Config.key == 'Downloader.tools115').first()
    if not config: raise HTTPException(409, '请先保存 115tools 连接配置')
    return Tools115(json.loads(config.content))

def invoke(callback):
    try: return success(callback())
    except Exception: raise HTTPException(502, '115tools 请求失败，请检查地址、令牌和远端状态')

@router.post('/115tools/test')
def test(db: Session=Depends(get_db)):
    invoke(lambda: client(db).call('GET', '/api/status'))
    return success({'connected': True})

class ImportLinks(BaseModel):
    text: str = Field(min_length=1, max_length=100000)
    idempotency_key: str = Field(min_length=1, max_length=128)

@router.post('/115tools/import')
def links(payload: ImportLinks, db: Session=Depends(get_db)):
    return invoke(lambda: client(db).submit(payload.text, payload.idempotency_key))

@router.post('/115tools/import/torrent')
async def torrent(file: UploadFile=File(...), idempotency_key: str=Form(..., min_length=1, max_length=128), db: Session=Depends(get_db)):
    content = await file.read(2*1024*1024+1)
    if len(content)>2*1024*1024 or not (file.filename or '').lower().endswith('.torrent'):
        raise HTTPException(422, '仅支持不超过 2 MiB 的 torrent 文件')
    tool = client(db)
    return invoke(lambda: tool.call('POST', '/api/v1/offline/import', headers={'Idempotency-Key': idempotency_key}, files={'file': (file.filename, content, 'application/x-bittorrent')}, data={'auto_extract': str(tool.config.get('auto_extract', True)).lower()}))

@router.get('/115tools/batches/{batch_id}')
def batch(batch_id: str, db: Session=Depends(get_db)):
    return invoke(lambda: client(db).call('GET', '/api/v1/import/batches/' + quote(batch_id, safe='')))
