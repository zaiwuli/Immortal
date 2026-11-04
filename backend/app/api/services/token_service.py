import json
import secrets
from datetime import datetime, timezone
from fastapi import HTTPException
from pydantic import BaseModel, Field
from app.api.deps import token_digest, require_permission
from app.core.permissions import RESOURCES, ACTIONS, PERMISSIONS
from app.models import Token, User
from app.schemas.response import success

class TokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    permissions: list[str] = Field(min_length=1)
    expires_at: datetime | None = None

class TokenPatch(BaseModel):
    enabled: bool


def public_token(token):
    return {'id': token.id, 'token_key': token.token_key, 'permissions': json.loads(token.permissions or '[]'), 'enabled': token.enabled, 'expires_at': token.expires_at, 'last_used_at': token.last_used_at, 'create_time': token.create_time}


def create_token(db, payload, principal):
    permissions = set(payload.permissions)
    if not permissions <= PERMISSIONS | {'*'}: raise HTTPException(422, '包含未知权限')
    for permission in permissions: require_permission(principal, permission)
    if db.query(Token).filter(Token.token_key == payload.name.strip()).first(): raise HTTPException(409, '令牌名称已存在')
    if payload.expires_at and (payload.expires_at.tzinfo is None or payload.expires_at <= datetime.now(timezone.utc)):
        raise HTTPException(422, '有效期必须是未来的带时区时间')
    raw = 'im_' + secrets.token_urlsafe(32)
    token = Token(token_key=payload.name.strip(), token_value=token_digest(raw), permissions=json.dumps(sorted(permissions)), expires_at=payload.expires_at)
    if not token.token_key: raise HTTPException(422, '名称不能为空')
    db.add(token); db.flush()
    return success({**public_token(token), 'token_value': raw})
