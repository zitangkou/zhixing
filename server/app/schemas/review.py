"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class ReviewHubOut(BaseModel):
    knowledgeDueCount: int = 0
    articleReviewCount: int = 0
    corpusInboxCount: int = 0
    articleWrongCount: int = 0
    manualWrongCount: int = 0
    wrongReviewCount: int = 0
    # 未到期错题：今日可跳过
    wrongWaitingCount: int = 0
    # 今日智能推荐题量（到期题封顶）
    wrongRecommendCount: int = 0
    # 全局复习调度：今日预算 / 今日推荐 / 积压
    todayBudget: int = 0
    todayRecommended: int = 0
    backlogCount: int = 0
    estimatedClearDays: int = 0
    reviewPlan: list[dict] = []
    totalCount: int = 0


# ===== 手动错题 =====


class ManualWrongOut(BaseModel):
    id: str
    subject: str
    questionType: str
    stem: str
    options: str
    myAnswer: str
    correctAnswer: str
    analysis: str
    wrongReason: str
    note: str
    images: list[str]
    source: str
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str = ""
    knowledgePath: str = ""
    reviewCount: int
    reviewStage: int = 0
    nextReviewAt: datetime | None = None
    due: bool = False
    mastered: bool
    lastWrongAt: datetime
    createdAt: datetime


class ManualWrongCreate(BaseModel):
    subject: str = ""
    questionType: str = ""
    stem: str = ""
    options: str = ""
    myAnswer: str = ""
    correctAnswer: str = ""
    analysis: str = ""
    wrongReason: str = ""
    note: str = ""
    source: str = "manual"  # manual | photo | ocr
    images: list[str] = []
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str = ""
    knowledgePath: str = ""


class ManualWrongUpdate(BaseModel):
    subject: str | None = None
    questionType: str | None = None
    stem: str | None = None
    options: str | None = None
    myAnswer: str | None = None
    correctAnswer: str | None = None
    analysis: str | None = None
    wrongReason: str | None = None
    note: str | None = None
    mastered: bool | None = None
    reviewCount: int | None = None
    images: list[str] | None = None
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str | None = None
    knowledgePath: str | None = None


# ===== 真题/题库模块 =====


