"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class EventImpressionOut(BaseModel):
    id: str
    title: str
    eventDate: str
    place: str
    coreContent: str
    note: str = ""
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str = ""
    knowledgePath: str = ""
    createdAt: datetime
    updatedAt: datetime


class EventImpressionCreate(BaseModel):
    title: str
    eventDate: str = ""
    place: str = ""
    coreContent: str = ""
    note: str = ""
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str = ""
    knowledgePath: str = ""


class EventImpressionUpdate(BaseModel):
    title: str | None = None
    eventDate: str | None = None
    place: str | None = None
    coreContent: str | None = None
    note: str | None = None
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str | None = None
    knowledgePath: str | None = None


class EventFrameworkGroup(BaseModel):
    treeKey: str
    path: str
    label: str
    count: int
    items: list[EventImpressionOut]


class EventHubOut(BaseModel):
    total: int = 0
    linkedCount: int = 0
    unlinkedCount: int = 0
    recentCount: int = 0  # 近 7 天
    frameworkGroups: list[EventFrameworkGroup] = []


