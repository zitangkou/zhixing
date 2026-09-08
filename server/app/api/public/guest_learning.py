"""登录后合并与读取游客练习快照。"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_app_user
from app.core.response import ApiResponse
from app.database import get_db
from app.models import AppUser
from app.product import ProductContext, get_product_context
from app.services.guest_learning_service import list_records, merge_records

router = APIRouter(prefix="/learning/guest-records")


class GuestLearningRecordIn(BaseModel):
    recordType: str = Field(min_length=1, max_length=32)
    contentId: str = Field(min_length=1, max_length=64)
    revision: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any]
    updatedAt: datetime


class GuestLearningMergeIn(BaseModel):
    deviceId: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    records: list[GuestLearningRecordIn] = Field(max_length=100)


@router.get("")
def guest_records(
    product: ProductContext = Depends(get_product_context),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(list_records(db, user.id, product.key))


@router.post("/merge")
def guest_records_merge(
    body: GuestLearningMergeIn,
    product: ProductContext = Depends(get_product_context),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(merge_records(db, user.id, product.key, body.deviceId, body.records))
