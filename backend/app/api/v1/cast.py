from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.services import cast_service
from app.core.database import get_db
from app.models import User
from app.schemas.cast import CastSearchParam

router = APIRouter()


@router.post('/search')
def search_casts(
    param: CastSearchParam,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cast_service.search_casts(param, db)


@router.post('/network-search')
def network_search_casts(
    param: CastSearchParam,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cast_service.network_search_casts(param, db)
