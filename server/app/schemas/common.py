"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class MindMapNode(BaseModel):
    id: str
    title: str
    content: str | None = None
    children: list["MindMapNode"] | None = None


class ArticleSection(BaseModel):
    id: str
    title: str
    level: int
    content: str | None = None
    highlight: str | None = None
    children: list["ArticleSection"] | None = None


