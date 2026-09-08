"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class StudyRecordOut(BaseModel):
    articleId: str
    studyDate: str
    reviewCount: int
    lastReviewDate: str | None = None
    mastered: bool
    updatedAt: str | None = None


class SectionReadBody(BaseModel):
    articleId: str
    sectionId: str


class ReviewCompleteBody(BaseModel):
    articleId: str


class WrongRedoBody(BaseModel):
    questionId: str
    answer: str | list[str]


