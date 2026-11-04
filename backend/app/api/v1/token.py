from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.api.services.token_service import TokenCreate, TokenPatch, create_token, public_token
from app.core.permissions import RESOURCES, ACTIONS
from app.core.database import get_db
from app.models import Token, User
from app.models.token import TokenAudit
from app.schemas.response import success
router = APIRouter()

@router.get('/me')
def me(principal=Depends(get_current_user)):
    return success({'name': principal.username, 'permissions': ['*']} if isinstance(principal, User) else public_token(principal))

@router.get('/permissions')
def catalog(principal=Depends(get_current_user)):
    return success({'resources': RESOURCES, 'actions': ACTIONS})

@router.get('/')
def list_tokens(db: Session=Depends(get_db), principal=Depends(get_current_user)):
    return success([public_token(t) for t in db.query(Token).order_by(Token.create_time.desc()).all()])

@router.post('/')
def create(payload: TokenCreate, db: Session=Depends(get_db), principal=Depends(get_current_user)):
    return create_token(db, payload, principal)

@router.patch('/{token_id}')
def patch(token_id: int, payload: TokenPatch, db: Session=Depends(get_db), principal=Depends(get_current_user)):
    token = db.get(Token, token_id)
    if not token: raise HTTPException(404, '令牌不存在')
    token.enabled = payload.enabled
    return success(public_token(token))

@router.get('/{token_id}/audit')
def audit(token_id: int, limit: int=Query(50, ge=1, le=200), db: Session=Depends(get_db), principal=Depends(get_current_user)):
    return success(db.query(TokenAudit).filter(TokenAudit.token_id==token_id).order_by(TokenAudit.id.desc()).limit(limit).all())

@router.delete('/{token_id}')
def delete(token_id: int, db: Session=Depends(get_db), principal=Depends(get_current_user)):
    token = db.get(Token, token_id)
    if not token: raise HTTPException(404, '令牌不存在')
    db.delete(token)
    return success()
