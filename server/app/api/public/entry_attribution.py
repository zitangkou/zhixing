"""公开学习入口解析与归因事件接收。"""

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.core.security import decode_token
from app.database import get_db
from app.models import AppUser
from app.product import ProductContext, get_product_context
from app.schemas import EntryAttributionEventCreate
from app.services.entry_attribution_service import record_entry_event, resolve_entry

router = APIRouter(prefix="/entry", tags=["学习入口"])
optional_bearer = HTTPBearer(auto_error=False)


def optional_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: Session = Depends(get_db),
) -> str | None:
    if not creds:
        return None
    user_id = decode_token(creds.credentials)
    user = db.get(AppUser, user_id) if user_id else None
    return user.id if user and user.is_active and user.username else None


@router.get("/resolve")
def entry_resolve(
    product: str = Query(default="", max_length=32),
    entry: str = Query(default="", max_length=64),
    section: str = Query(default="", max_length=32),
    channel: str = Query(default="direct", max_length=32),
    campaign: str = Query(default="", max_length=64),
    content: str = Query(default="", max_length=64),
    scene: str = Query(default="", max_length=64),
    context: ProductContext = Depends(get_product_context),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(resolve_entry(
        db, context.key, product=product, entry=entry, section=section,
        channel=channel, campaign=campaign, content=content, scene=scene,
    ))


@router.post("/events")
def entry_event(
    body: EntryAttributionEventCreate,
    context: ProductContext = Depends(get_product_context),
    user_id: str | None = Depends(optional_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(record_entry_event(db, context.key, body, user_id))
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)
