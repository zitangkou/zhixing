"""时政要点：一条要点一套题，题目直接挂在要点上。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import Question, TheoryPoint
from app.services.question_factory import add_point_questions
from app.services.question_import import parse_questions_markdown
from app.services.theory_brief_service import approved_count_for_point

router = APIRouter(prefix="/theory-briefs", tags=["时政要点"])


class PointBody(BaseModel):
    title: str
    articleId: str | None = None
    highlights: str = ""
    isPublished: bool = False
    isKey: bool = False
    sortOrder: int = 0
    parentId: str | None = None


class PointImportBody(BaseModel):
    markdown: str = Field(min_length=10)
    pending: bool = False
    replaceExisting: bool = True


def _row(db: Session, row: TheoryPoint) -> dict:
    parent = db.get(TheoryPoint, row.parent_id) if row.parent_id else None
    return {
        "id": row.id,
        "title": row.title,
        "highlights": row.highlights or "",
        "isPublished": row.is_published,
        "isKey": bool(row.is_key),
        "sortOrder": row.sort_order,
        "questionCount": approved_count_for_point(db, row.id),
        "parentId": row.parent_id or "",
        "parentTitle": parent.title if parent else "",
    }


def _apply(row: TheoryPoint, body: PointBody, db: Session) -> None:
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "请填写标题")
    parent_id = (body.parentId or "").strip() or None
    if parent_id:
        if row.id and parent_id == row.id:
            raise HTTPException(400, "不能挂到自己下面")
        parent = db.get(TheoryPoint, parent_id)
        if not parent or parent.parent_id:
            raise HTTPException(400, "只能挂到一级要点下面")
        if row.id and db.query(TheoryPoint).filter(TheoryPoint.parent_id == row.id).first():
            raise HTTPException(400, "已有小节的要点不能再挂到别的要点下面")
    row.title = title
    row.highlights = body.highlights.strip()
    row.is_published = body.isPublished
    row.is_key = body.isKey
    row.sort_order = body.sortOrder
    row.parent_id = parent_id


@router.get("")
def list_points(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin=Depends(require_permission("article:read")),
    db: Session = Depends(get_db),
):
    query = db.query(TheoryPoint)
    total = query.count()
    ordering = (TheoryPoint.sort_order, TheoryPoint.created_at.desc())
    rows = query.order_by(*ordering).offset((page - 1) * page_size).limit(page_size).all()
    parents = db.query(TheoryPoint).filter(TheoryPoint.parent_id.is_(None)).order_by(*ordering).all()
    return ApiResponse.ok({
        "items": [_row(db, row) for row in rows],
        "parents": [{"id": row.id, "title": row.title} for row in parents],
        "total": total,
        "page": page,
        "pageSize": page_size,
    })


@router.post("")
def create_point(
    body: PointBody,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    row = TheoryPoint(title="未命名")
    _apply(row, body, db)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiResponse.ok(_row(db, row))


@router.put("/{point_id}")
def update_point(
    point_id: str,
    body: PointBody,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    row = db.get(TheoryPoint, point_id)
    if not row:
        raise HTTPException(404, "不存在")
    _apply(row, body, db)
    db.commit()
    return ApiResponse.ok(_row(db, row))


@router.post("/preview-questions")
def preview_point_questions(
    body: PointImportBody,
    _admin=Depends(require_permission("article:read")),
):
    parsed, parse_errors = parse_questions_markdown(body.markdown)
    return ApiResponse.ok({
        "count": len(parsed),
        "parseWarnings": parse_errors,
    })


@router.post("/{point_id}/import-questions")
def import_point_questions(
    point_id: str,
    body: PointImportBody,
    _admin=Depends(require_permission("question:write")),
    db: Session = Depends(get_db),
):
    row = db.get(TheoryPoint, point_id)
    if not row:
        raise HTTPException(404, "不存在")
    parsed, parse_errors = parse_questions_markdown(body.markdown)
    if not parsed:
        msg = "；".join(parse_errors[:8]) if parse_errors else "未解析到题目"
        return ApiResponse.fail(msg, code=400)
    if body.replaceExisting:
        db.query(Question).filter(Question.theory_point_id == row.id).delete()
    count = add_point_questions(db, row.id, parsed, pending=body.pending)
    db.commit()
    result = _row(db, row)
    result["count"] = count
    result["parseWarnings"] = parse_errors
    msg = f"已导入 {count} 道题目"
    if parse_errors:
        msg += f"（{len(parse_errors)} 条解析提示）"
    return ApiResponse.ok(result, message=msg)


@router.delete("/{point_id}")
def delete_point(
    point_id: str,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    row = db.get(TheoryPoint, point_id)
    if row:
        if db.query(TheoryPoint).filter(TheoryPoint.parent_id == row.id).first():
            raise HTTPException(400, "请先删除下面的小节")
        db.query(Question).filter(Question.theory_point_id == row.id).delete()
        db.delete(row)
        db.commit()
    return ApiResponse.ok(True)
