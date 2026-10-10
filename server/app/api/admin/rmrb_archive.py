"""人民日报全量文章档案管理 API。"""
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.schemas.rmrb_archive import RmrbArchiveArticleCreate, RmrbArchiveArticleUpdate, RmrbArchiveBatchRunBody
from app.services.rmrb_archive_service import (
    archive_article, create_article, create_manual_batch, get_article,
    list_articles, list_batches, run_collection_batch, update_article,
)

router = APIRouter(tags=["人民日报文章档案"])


@router.get("/rmrb-archive/batches")
def admin_list_rmrb_archive_batches(
    _admin=Depends(require_permission("rmrb:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(list_batches(db))


@router.post("/rmrb-archive/batches/run")
def admin_start_rmrb_archive_batch(
    body: RmrbArchiveBatchRunBody,
    background_tasks: BackgroundTasks,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        batch = create_manual_batch(db, body.issueDate)
    except (TypeError, ValueError) as exc:
        return ApiResponse.fail(f"出版日期格式无效：{exc}", code=400)
    background_tasks.add_task(run_collection_batch, batch["id"])
    return ApiResponse.ok(batch, message="采集批次已提交后台运行")


@router.get("/rmrb-archive/articles")
def admin_list_rmrb_archive_articles(
    issue_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page_no: str | None = None,
    page_name: str | None = None,
    title: str | None = None,
    article_type: str | None = None,
    record_class: str | None = None,
    exam_relevance: str | None = None,
    retention_tier: str | None = None,
    author: str | None = None,
    editor: str | None = None,
    body_status: str | None = None,
    review_status: str | None = None,
    source_channel: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin=Depends(require_permission("rmrb:read")),
    db: Session = Depends(get_db),
):
    data = list_articles(
        db, issue_date=issue_date, date_from=date_from, date_to=date_to, page_no=page_no,
        page_name=page_name, title=title, article_type=article_type, record_class=record_class,
        exam_relevance=exam_relevance, retention_tier=retention_tier, author=author, editor=editor,
        body_status=body_status, review_status=review_status, source_channel=source_channel,
        page=page, page_size=page_size,
    )
    return ApiResponse.ok(data)


@router.get("/rmrb-archive/articles/{article_id}")
def admin_get_rmrb_archive_article(
    article_id: str,
    _admin=Depends(require_permission("rmrb:read")),
    db: Session = Depends(get_db),
):
    data = get_article(db, article_id, include_body=True)
    return ApiResponse.ok(data) if data else ApiResponse.fail("文章不存在", code=404)


@router.post("/rmrb-archive/articles")
def admin_create_rmrb_archive_article(
    body: RmrbArchiveArticleCreate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(create_article(db, body), message="文章档案已创建")
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)


@router.put("/rmrb-archive/articles/{article_id}")
def admin_update_rmrb_archive_article(
    article_id: str,
    body: RmrbArchiveArticleUpdate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        data = update_article(db, article_id, body)
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(data) if data else ApiResponse.fail("文章不存在", code=404)


@router.delete("/rmrb-archive/articles/{article_id}")
def admin_archive_rmrb_archive_article(
    article_id: str,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok({"ok": True}) if archive_article(db, article_id) else ApiResponse.fail("文章不存在", code=404)
