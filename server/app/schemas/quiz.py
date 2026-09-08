"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class AnswerSubmit(BaseModel):
    questionId: str
    answer: str | list[str]


class AnswerResult(BaseModel):
    correct: bool
    analysis: str
    correctAnswer: str | list[str]
    pointsEarned: int


class PointsLogOut(BaseModel):
    id: str
    amount: int
    type: str
    source: str
    description: str
    createdAt: str


class RankItemOut(BaseModel):
    rank: int
    userId: str
    nickname: str
    avatar: str
    score: int
    isSelf: bool | None = None


class QuizCompleteBody(BaseModel):
    articleId: str | None = None
    mode: str = "article"
    total: int = Field(ge=1)
    correct: int = Field(ge=0)


class QuizCompleteResult(BaseModel):
    accuracy: int
    rank: int
    totalParticipants: int
    bestAccuracy: int | None = None


class QuizRankItemOut(BaseModel):
    rank: int
    userId: str
    nickname: str
    avatar: str
    accuracy: int
    correctCount: int
    totalCount: int
    isSelf: bool | None = None


class QuizStatsOut(BaseModel):
    attemptCount: int
    bestAccuracy: int
    bestCorrect: int
    bestTotal: int
    lastAccuracy: int
    rank: int
    totalParticipants: int


