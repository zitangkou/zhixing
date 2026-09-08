"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class PlanTaskOut(BaseModel):
    id: str
    planDate: str
    timeSlot: str
    subject: str
    content: str
    priority: int = 3
    expectedMinutes: int
    actualMinutes: int
    status: str
    sortOrder: int
    note: str


class PlanTaskUpdate(BaseModel):
    status: str | None = None
    actualMinutes: int | None = None
    note: str | None = None


class PlanTaskCreate(BaseModel):
    planDate: str
    timeSlot: str = ""
    subject: str = ""
    content: str
    priority: int = 3
    expectedMinutes: int = 0


# ===== 学习计划模板 =====


class PlanTemplateOut(BaseModel):
    id: str
    dayType: str
    timeSlot: str
    subject: str
    content: str
    priority: int
    expectedMinutes: int
    sortOrder: int
    isActive: bool


class PlanTemplateCreate(BaseModel):
    dayType: str  # weekday | weekend
    timeSlot: str = ""
    subject: str = ""
    content: str
    priority: int = 3
    expectedMinutes: int = 0
    sortOrder: int = 0


class PlanTemplateUpdate(BaseModel):
    timeSlot: str | None = None
    subject: str | None = None
    content: str | None = None
    priority: int | None = None
    expectedMinutes: int | None = None
    sortOrder: int | None = None
    isActive: bool | None = None


class DailyReviewOut(BaseModel):
    reviewDate: str
    completion: int
    totalMinutes: int
    weakPoint: str
    tomorrowFocus: str
    mood: str
    note: str


class DailyReviewUpsert(BaseModel):
    reviewDate: str
    completion: int | None = None
    totalMinutes: int | None = None
    weakPoint: str | None = None
    tomorrowFocus: str | None = None
    mood: str | None = None
    note: str | None = None


class DayPlanOut(BaseModel):
    """单日清单 + 进度概览"""
    date: str
    isWeekend: bool
    tasks: list[PlanTaskOut]
    completion: int  # 0-100
    doneCount: int
    totalCount: int
    expectedMinutes: int
    actualMinutes: int
    review: DailyReviewOut | None = None


# ===== 知识框架 =====


