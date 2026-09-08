"""时政单篇学习入口编排管理。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.services.theory_learning_entry_service import list_admin_entries, save_entry

router = APIRouter(prefix="/theory-learning")


class LearningPartIn(BaseModel):
    title: str = Field(default="", max_length=64)
    questionIds: list[str] = Field(max_length=5)


class LearningEntryIn(BaseModel):
    title: str = Field(default="", max_length=128)
    description: str = Field(default="", max_length=512)
    isDaily: bool = False
    isEvergreen: bool = False
    parts: list[LearningPartIn] = Field(default_factory=list, max_length=100)
    collectionEnabled: bool = False
    status: str = Field(pattern=r"^(draft|published)$")
    publishStart: str = Field(default="", pattern=r"^$|^\d{4}-\d{2}-\d{2}$")
    publishEnd: str = Field(default="", pattern=r"^$|^\d{4}-\d{2}-\d{2}$")
    sortOrder: int = Field(default=0, ge=-100000, le=100000)


@router.get("/entries")
def entries(
    _admin=Depends(require_permission("article:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(list_admin_entries(db))


@router.put("/entries/{article_id}")
def upsert_entry(
    article_id: str,
    body: LearningEntryIn,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(save_entry(db, article_id, body.model_dump()))
