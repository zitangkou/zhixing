"""时政要点：关联原文、重点、原文下已有套题。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import Article, TheoryPoint
from app.services.theory_brief_service import approved_count

router = APIRouter(prefix="/theory-briefs", tags=["时政要点"])


class PointBody(BaseModel):
    title: str
    articleId: str | None = None
    highlights: str = ""
    isPublished: bool = False
    isKey: bool = False
    sortOrder: int = 0


def _row(db: Session, row: TheoryPoint) -> dict:
    article = db.get(Article, row.article_id) if row.article_id else None
    return {
        "id": row.id,
        "title": row.title,
        "articleId": row.article_id or "",
        "articleTitle": article.title if article else "",
        "highlights": row.highlights or "",
        "isPublished": row.is_published,
        "isKey": bool(row.is_key),
        "sortOrder": row.sort_order,
        "questionCount": approved_count(db, row.article_id) if row.article_id else 0,
    }


def _apply(row: TheoryPoint, body: PointBody, db: Session) -> None:
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "请填写标题")
    if body.articleId and not db.get(Article, body.articleId):
        raise HTTPException(400, "原文不存在")
    row.title = title
    row.article_id = body.articleId or None
    row.highlights = body.highlights.strip()
    row.is_published = body.isPublished
    row.is_key = body.isKey
    row.sort_order = body.sortOrder


@router.get("")
def list_points(
    _admin=Depends(require_permission("article:read")),
    db: Session = Depends(get_db),
):
    rows = db.query(TheoryPoint).order_by(TheoryPoint.sort_order, TheoryPoint.created_at.desc()).all()
    return ApiResponse.ok({"items": [_row(db, row) for row in rows]})


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


@router.delete("/{point_id}")
def delete_point(
    point_id: str,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    row = db.get(TheoryPoint, point_id)
    if row:
        db.delete(row)
        db.commit()
    return ApiResponse.ok(True)
