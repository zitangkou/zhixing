"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class KnowledgeNodeOut(BaseModel):
    id: str
    treeKey: str
    parentId: str | None = None
    title: str
    content: str
    myNote: str = ""
    isStarred: bool = False
    masteryLevel: str = "new"
    nextReviewAt: datetime | None = None
    reviewCount: int = 0
    lastReviewedAt: datetime | None = None
    depth: int
    sortOrder: int
    path: str
    sourceFile: str = ""
    children: list["KnowledgeNodeOut"] | None = None


class KnowledgeTreeOut(BaseModel):
    treeKey: str
    title: str
    nodes: list[KnowledgeNodeOut]


class KnowledgeNodeUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    myNote: str | None = None
    isStarred: bool | None = None


class KnowledgeNodeCreate(BaseModel):
    treeKey: str
    parentId: str | None = None
    title: str
    content: str = ""


class KnowledgeReviewDueOut(BaseModel):
    dueCount: int
    candidates: list["KnowledgeReviewCardOut"] = []


class KnowledgeReviewCardOut(BaseModel):
    id: str
    title: str
    path: str
    treeKey: str
    content: str = ""
    myNote: str = ""
    masteryLevel: str = "new"
    hint: str | None = None


class KnowledgeReviewSessionBody(BaseModel):
    count: int = 5


class KnowledgeReviewSessionOut(BaseModel):
    cards: list[KnowledgeReviewCardOut]


class KnowledgeReviewAnswerBody(BaseModel):
    nodeId: str
    result: str  # again|hard|good|easy


class KnowledgeReviewAnswerOut(BaseModel):
    id: str
    masteryLevel: str
    nextReviewAt: datetime | None = None
    reviewCount: int
    lastReviewedAt: datetime | None = None


