"""时政采集审核、套题生成、审核与发布。"""
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import AdminUser, RmrbArchiveArticle, RmrbArchiveBatch, TheoryQuizPaper, TheorySourceReview
from app.services.rmrb_archive_service import create_manual_batch, run_collection_batch
from app.services.theory_workflow_service import (
    _review_row, ensure_source_body, generate_paper, list_sources, paper_out, publish_paper, review_paper_question,
)
from app.timezone import today

router = APIRouter(prefix="/theory-workflow", tags=["时政刷题工作流"])


class CollectBody(BaseModel):
    issueDate: date


class SourceReviewBody(BaseModel):
    status: str = Field(pattern="^(approved|rejected|pending)$")
    note: str = Field(default="", max_length=2000)


class GenerateBody(BaseModel):
    title: str = Field(min_length=2, max_length=256)


class QuestionReviewBody(BaseModel):
    reviewStatus: str = Field(pattern="^(approved|rejected|pending)$")
    reviewNote: str = Field(default="", max_length=1000)
    stem: str | None = None
    options: list[str] | None = None
    answer: str | None = None
    analysis: str | None = None
    sourceSentence: str | None = None
    topic: str | None = None


@router.get("/collections")
def collections(_admin=Depends(require_permission("article:read")), db: Session = Depends(get_db)):
    rows = (db.query(RmrbArchiveBatch)
            .filter(RmrbArchiveBatch.trigger_mode.in_(["manual", "theory_daily"]))
            .order_by(RmrbArchiveBatch.created_at.desc()).limit(10).all())
    return ApiResponse.ok([{
        "id": row.id, "issueDate": row.issue_date.isoformat(), "status": row.status,
        "discovered": row.discovered_article_count, "created": row.created_article_count,
        "failedPages": row.failed_page_count, "failedSources": row.failed_source_count,
        "error": row.error_summary, "startedAt": row.started_at, "finishedAt": row.finished_at,
    } for row in rows])


@router.post("/collect")
def collect(body: CollectBody, tasks: BackgroundTasks,
            _admin=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    if body.issueDate.isoformat() > today():
        return ApiResponse.fail("不能采集未来日期", code=400)
    active = (db.query(RmrbArchiveBatch).filter(
        RmrbArchiveBatch.issue_date == body.issueDate,
        RmrbArchiveBatch.trigger_mode.in_(["manual", "theory_daily"]),
        RmrbArchiveBatch.status.in_(["queued", "running"]),
    ).order_by(RmrbArchiveBatch.created_at.desc()).first())
    if active:
        return ApiResponse.ok({"id": active.id, "issueDate": active.issue_date, "status": active.status}, message="该刊期已有采集任务运行中")
    batch = create_manual_batch(db, body.issueDate)
    tasks.add_task(run_collection_batch, batch["id"])
    return ApiResponse.ok(batch, message="人民日报版面采集已提交")


@router.get("/sources")
def sources(issue_date: date | None = None, status: str = "", page: int = Query(1, ge=1),
            page_size: int = Query(30, ge=1, le=100),
            _admin=Depends(require_permission("article:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(list_sources(db, issue_date=issue_date, status=status, page=page, page_size=page_size))


@router.get("/sources/{article_id}")
def source_detail(article_id: str, _admin=Depends(require_permission("article:read")), db: Session = Depends(get_db)):
    source = db.get(RmrbArchiveArticle, article_id)
    if not source:
        return ApiResponse.fail("文章不存在", code=404)
    from app.services.rmrb_archive_service import get_article
    try:
        ensure_source_body(db, source)
    except Exception as exc:
        return ApiResponse.fail(f"原文暂无法读取：{str(exc)[:250]}", code=502)
    return ApiResponse.ok(get_article(db, article_id, include_body=True))


@router.put("/sources/{article_id}/review")
def review_source(article_id: str, body: SourceReviewBody, admin: AdminUser = Depends(require_permission("article:write")),
                  db: Session = Depends(get_db)):
    source = db.get(RmrbArchiveArticle, article_id)
    if not source:
        return ApiResponse.fail("文章不存在", code=404)
    row = db.query(TheorySourceReview).filter_by(archive_article_id=article_id).first()
    if not row:
        row = _review_row(db, source)
    if body.status != "approved" and db.query(TheoryQuizPaper).filter_by(archive_article_id=article_id, status="published").first():
        return ApiResponse.fail("已有上线套题，不能撤销来源审核；请先发布替代版本", code=409)
    row.status, row.review_note, row.reviewed_by = body.status, body.note.strip(), admin.username
    from app.models.base import utcnow
    row.reviewed_at = utcnow()
    db.commit()
    return ApiResponse.ok({"id": row.id, "status": row.status, "note": row.review_note})


@router.post("/sources/{article_id}/papers")
def start_generation(article_id: str, body: GenerateBody, tasks: BackgroundTasks,
                     _admin=Depends(require_permission("question:write")), db: Session = Depends(get_db)):
    source = db.get(RmrbArchiveArticle, article_id)
    review = db.query(TheorySourceReview).filter_by(archive_article_id=article_id).first()
    if not source or not review:
        return ApiResponse.fail("请先审核文章", code=400)
    if review.status != "approved":
        return ApiResponse.fail("只有审核通过的文章可以生成套题", code=400)
    latest = db.query(TheoryQuizPaper).filter_by(archive_article_id=article_id).order_by(TheoryQuizPaper.version.desc()).first()
    if latest and latest.status in {"queued", "generating"}:
        return ApiResponse.ok(paper_out(latest), message="该文章已有套题生成任务正在运行")
    version = (latest.version if latest else 0) + 1
    paper = TheoryQuizPaper(archive_article_id=article_id, version=version, title=body.title.strip(), status="queued")
    db.add(paper)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        latest = db.query(TheoryQuizPaper).filter_by(archive_article_id=article_id).order_by(TheoryQuizPaper.version.desc()).first()
        if latest and latest.status in {"queued", "generating"}:
            return ApiResponse.ok(paper_out(latest), message="该文章已有套题生成任务正在运行")
        return ApiResponse.fail("套题版本已被其他请求创建，请刷新后重试", code=409)
    db.refresh(paper)
    tasks.add_task(generate_paper, paper.id)
    return ApiResponse.ok(paper_out(paper), message="套题生成已提交")


@router.get("/papers/{paper_id}")
def paper_detail(paper_id: str, _admin=Depends(require_permission("question:read")), db: Session = Depends(get_db)):
    paper = db.get(TheoryQuizPaper, paper_id)
    if not paper:
        return ApiResponse.fail("套题不存在", code=404)
    import json
    return ApiResponse.ok({**paper_out(paper), "questions": json.loads(paper.questions_json or "[]"),
                           "reviewHistory": json.loads(paper.review_history_json or "[]")})


@router.put("/papers/{paper_id}/questions/{index}")
def review_question(paper_id: str, index: int, body: QuestionReviewBody,
                    admin: AdminUser = Depends(require_permission("question:write")), db: Session = Depends(get_db)):
    paper = db.get(TheoryQuizPaper, paper_id)
    if not paper:
        return ApiResponse.fail("套题不存在", code=404)
    try:
        values = body.model_dump(exclude_none=True)
        return ApiResponse.ok(review_paper_question(db, paper, index, values, admin.username))
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)


@router.post("/papers/{paper_id}/publish")
def publish(paper_id: str, admin: AdminUser = Depends(require_permission("article:write")),
            _admin=Depends(require_permission("question:write")), db: Session = Depends(get_db)):
    paper = db.get(TheoryQuizPaper, paper_id)
    if not paper:
        return ApiResponse.fail("套题不存在", code=404)
    try:
        return ApiResponse.ok(publish_paper(db, paper, admin.username), message="套题已发布到时政要点")
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
