"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class ExamCountdownOut(BaseModel):
    id: str
    examName: str
    examDate: str
    note: str = ""
    daysLeft: int = 0
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class ExamCountdownUpsert(BaseModel):
    examName: str
    examDate: str
    note: str = ""
