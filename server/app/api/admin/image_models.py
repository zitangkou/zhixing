"""Admin API for selectable image generation models."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.schemas.image_style import ImageModelConfigUpdate
from app.services.image_model_service import get_image_model_config, save_image_model_config

router = APIRouter()


@router.get("/image-models")
def admin_list_image_models(_admin=Depends(require_permission("setting:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(get_image_model_config(db))


@router.put("/image-models")
def admin_save_image_models(
    body: ImageModelConfigUpdate,
    _admin=Depends(require_permission("setting:write")),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(save_image_model_config(db, body.items))
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)
