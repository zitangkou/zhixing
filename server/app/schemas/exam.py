"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class ExamPaperOut(BaseModel):
    id: str
    title: str
    examType: str
    subject: str
    year: int | None = None
    region: str
    level: str
    totalCount: int
    timeLimitMin: int
    tags: list[str]
    isPublished: bool
    isFree: bool
    sortOrder: int
    description: str
    createdAt: datetime


class ExamPaperCreate(BaseModel):
    title: str
    examType: str = "real"  # real | custom | mock
    subject: str = "行测"
    year: int | None = None
    region: str = ""
    level: str = ""
    timeLimitMin: int = 120
    tags: list[str] = []
    isPublished: bool = True
    isFree: bool = True
    sortOrder: int = 0
    description: str = ""


class ExamPaperUpdate(BaseModel):
    title: str | None = None
    examType: str | None = None
    subject: str | None = None
    year: int | None = None
    region: str | None = None
    level: str | None = None
    timeLimitMin: int | None = None
    tags: list[str] | None = None
    isPublished: bool | None = None
    isFree: bool | None = None
    sortOrder: int | None = None
    description: str | None = None


class ExamQuestionOut(BaseModel):
    id: str
    paperId: str
    section: str
    sectionIndex: int
    sortOrder: int
    type: str
    material: str
    stem: str
    options: list[str]
    correctAnswer: str | list[str]
    analysis: str
    difficulty: int
    knowledgeTags: list[str]
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str = ""
    knowledgePath: str = ""
    isActive: bool


class ExamQuestionCreate(BaseModel):
    section: str = ""
    sectionIndex: int = 0
    sortOrder: int = 0
    type: str = "single"
    material: str = ""
    stem: str
    options: list[str]
    correctAnswer: str | list[str]
    analysis: str = ""
    difficulty: int = 3
    knowledgeTags: list[str] = []
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str = ""
    knowledgePath: str = ""


class ExamQuestionUpdate(BaseModel):
    section: str | None = None
    sectionIndex: int | None = None
    sortOrder: int | None = None
    type: str | None = None
    material: str | None = None
    stem: str | None = None
    options: list[str] | None = None
    correctAnswer: str | list[str] | None = None
    analysis: str | None = None
    difficulty: int | None = None
    knowledgeTags: list[str] | None = None
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str | None = None
    knowledgePath: str | None = None
    isActive: bool | None = None


class ExamPaperDetailOut(BaseModel):
    """试卷详情（含所有题目，按 section 分组）"""
    id: str
    title: str
    examType: str
    subject: str
    year: int | None = None
    region: str
    level: str
    totalCount: int
    timeLimitMin: int
    tags: list[str]
    isPublished: bool
    isFree: bool
    description: str
    sections: list[dict]  # [{section, questions: [ExamQuestionOut]}]


class ExamAnswerSubmit(BaseModel):
    """单题作答提交"""
    questionId: str
    answer: str | list[str]
    timeUsedSec: int = 0
    marked: bool = False


class ExamAttemptOut(BaseModel):
    """作答记录"""
    id: str
    paperId: str
    paperTitle: str
    startedAt: datetime
    finishedAt: datetime | None
    timeUsedSec: int
    totalCount: int
    answeredCount: int
    correctCount: int
    score: int
    isFinished: bool


class ExamAttemptDetailOut(ExamAttemptOut):
    """作答详情（含每题对错）"""
    answers: list[dict]  # [{questionId, userAnswer, isCorrect, timeUsedSec, marked, stem, correctAnswer, analysis}]
    sectionStats: list[dict]  # [{section, total, correct, accuracy}]


RMRB_THEME_TAG_PRESETS = [
    "政绩观",
    "社会治理",
    "乡村振兴",
    "县域经济",
    "高质量发展",
    "民生保障",
    "作风建设",
    "基层减负",
    "科技创新",
    "文化建设",
    "生态文明",
    "依法治国",
]


