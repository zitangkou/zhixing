from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.database import get_db
from app.services.photography_service import photography_catalog

router = APIRouter(prefix="/photography", tags=["摄影学习"])


@router.get("/catalog")
def catalog(db: Session = Depends(get_db)):
    return ApiResponse.ok(photography_catalog(db))
