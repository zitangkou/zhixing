"""公众号固定消息回复配置管理。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import AdminUser
from app.schemas.wechat_reply import WechatReplyConfig, WechatReplyPreviewIn
from app.services.wechat_reply_service import (
    get_admin_reply_state,
    preview_reply,
    publish_reply_draft,
    rollback_reply_release,
    save_reply_draft,
    validate_reply_config,
)
from app.config import get_settings

router = APIRouter(prefix="/wechat-replies", tags=["公众号消息回复"])


class RollbackBody(BaseModel):
    releaseId: str


@router.get("/config")
def read_config(
    _admin: AdminUser = Depends(require_permission("wechat_reply:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_admin_reply_state(db))


@router.put("/draft")
def update_draft(
    body: WechatReplyConfig,
    admin: AdminUser = Depends(require_permission("wechat_reply:write")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(save_reply_draft(db, body.model_dump(), admin.id, admin.nickname or admin.username))


@router.post("/validate")
def validate_draft(
    body: WechatReplyConfig,
    _admin: AdminUser = Depends(require_permission("wechat_reply:read")),
):
    return ApiResponse.ok(validate_reply_config(body.model_dump()))


@router.post("/preview")
def preview_draft(
    body: WechatReplyPreviewIn,
    _admin: AdminUser = Depends(require_permission("wechat_reply:read")),
    db: Session = Depends(get_db),
):
    config = body.config.model_dump() if body.config else get_admin_reply_state(db)["draft"]
    settings = get_settings()
    result = preview_reply(
        config=config,
        message=body.message,
        msg_type=body.msgType,
        event=body.event,
        public_base_url=settings.wechat_official_public_base_url,
    )
    return ApiResponse.ok(result)


@router.post("/publish")
def publish_draft(
    admin: AdminUser = Depends(require_permission("wechat_reply:publish")),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(publish_reply_draft(db, admin.id, admin.nickname or admin.username))
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)


@router.get("/releases")
def list_releases(
    _admin: AdminUser = Depends(require_permission("wechat_reply:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_admin_reply_state(db)["releases"])


@router.post("/rollback")
def rollback_release(
    body: RollbackBody,
    admin: AdminUser = Depends(require_permission("wechat_reply:publish")),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(
            rollback_reply_release(db, body.releaseId, admin.id, admin.nickname or admin.username)
        )
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)
