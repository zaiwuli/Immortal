import hashlib
import json
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import SECRET_KEY, ALGORITHM
from app.core.permissions import required_permission
from app.models import Token, User


def token_digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def require_permission(principal, permission):
    if isinstance(principal, User): return
    permissions = set(json.loads(principal.permissions or '[]'))
    if '*' not in permissions and permission not in permissions:
        raise HTTPException(403, f'缺少权限：{permission}')


api_key_scheme = APIKeyHeader(name='X-API-Key', auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(request: Request, db: Session = Depends(get_db), api_key_header=Security(api_key_scheme), bearer_header=Security(bearer_scheme)):
    header = request.headers.get('Authorization', '')
    bearer = header[7:].strip() if header.lower().startswith('bearer ') else ''
    api_key = request.headers.get('X-API-Key')
    if api_key or bearer.startswith('im_'):
        raw = api_key or bearer
        token = db.query(Token).filter(Token.token_value == token_digest(raw)).first()
        if not token or not token.enabled:
            raise HTTPException(401, '令牌无效或已停用')
        expires = token.expires_at
        if expires and expires.replace(tzinfo=expires.tzinfo or timezone.utc) <= datetime.now(timezone.utc):
            raise HTTPException(401, '令牌已过期')
        request.state.token_id = token.id
        if request.url.path.rstrip('/') != '/api/v1/tokens/me':
            require_permission(token, required_permission(request))
        token.last_used_at = datetime.now(timezone.utc)
        request.state.token_id = token.id
        return token
    try:
        payload = jwt.decode(bearer, SECRET_KEY, algorithms=[ALGORITHM], options={'require_exp': True})
        if payload.get('purpose') != 'access': raise JWTError('wrong purpose')
        user = db.query(User).filter(User.username == payload.get('sub')).first()
    except JWTError:
        raise HTTPException(401, '登录令牌无效或已过期')
    if not user: raise HTTPException(401, '用户不存在')
    return user

api_key_or_jwt = get_current_user
verify_api_key = get_current_user
