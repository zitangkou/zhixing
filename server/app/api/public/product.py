"""多产品通用学习任务接口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_app_user
from app.core.response import ApiResponse
from app.database import get_db
from app.models import AppUser
from app.product import ProductContext, get_product_context
from app.schemas import DailyTaskProgressBody, TopicItem, TopicListOut
from app.services.daily_task_service import list_daily_tasks, update_task_progress
from app.services.topic_service import list_topics
from app.timezone import today as today_str

router = APIRouter()


@router.get("/product/topics")
def product_topics(
    user: AppUser = Depends(get_app_user),
    product: ProductContext = Depends(get_product_context),
    db: Session = Depends(get_db),
):
    """专题列表。内容由 system_settings 的 `topics.<product_key>` 下发，可后台切换而不发版。"""
    items = [TopicItem(**t) for t in list_topics(db, product.key)]
    return ApiResponse.ok(TopicListOut(productKey=product.key, items=items).model_dump())


@router.get("/product/daily-tasks")
def daily_tasks(
    date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    user: AppUser = Depends(get_app_user),
    product: ProductContext = Depends(get_product_context),
    db: Session = Depends(get_db),
):
    task_date = date or today_str()
    return ApiResponse.ok(list_daily_tasks(db, user, product, task_date).model_dump())


@router.post("/product/daily-tasks/{task_id}/progress")
def daily_task_progress(
    task_id: str,
    body: DailyTaskProgressBody,
    user: AppUser = Depends(get_app_user),
    product: ProductContext = Depends(get_product_context),
    db: Session = Depends(get_db),
):
    try:
        out = update_task_progress(db, user, product, task_id, body)
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(out.model_dump())
