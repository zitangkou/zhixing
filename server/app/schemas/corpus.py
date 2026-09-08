"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class CorpusItemOut(BaseModel):
    id: str
    original: str
    kind: str = "句"
    sourceType: str = "其他"
    sourceTitle: str = ""
    tags: list[str] = []
    plainNote: str = ""
    rewrite: str = ""
    practice: str = ""
    status: str = "inbox"
    usedCount: int = 0
    promotedTermId: str | None = None
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str = ""
    knowledgePath: str = ""
    createdAt: datetime
    updatedAt: datetime


class CorpusItemCreate(BaseModel):
    original: str
    kind: str = "句"
    sourceType: str = "其他"
    sourceTitle: str = ""
    tags: list[str] = []
    plainNote: str = ""
    rewrite: str = ""
    practice: str = ""
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str = ""
    knowledgePath: str = ""


class CorpusItemUpdate(BaseModel):
    original: str | None = None
    kind: str | None = None
    sourceType: str | None = None
    sourceTitle: str | None = None
    tags: list[str] | None = None
    plainNote: str | None = None
    rewrite: str | None = None
    practice: str | None = None
    markUsed: bool | None = None
    knowledgeNodeId: str | None = None
    knowledgeTreeKey: str | None = None
    knowledgePath: str | None = None


class CorpusStatsOut(BaseModel):
    inboxCount: int = 0
    clarifiedCount: int = 0
    ownedCount: int = 0
    usedCount: int = 0
    total: int = 0
    kinds: list[str] = []
    sourceTypes: list[str] = []
    tagPresets: list[str] = []


# ===== 财富 / 投资大脑 =====



CORPUS_KINDS = ["词", "专名", "成语", "诗典", "短语", "句", "结构"]
CORPUS_SOURCE_TYPES = ["报纸", "视频", "播客", "书", "聊天", "其他"]
CORPUS_TAG_PRESETS = ["民生", "治理", "收束", "过渡", "对比", "金句", "问题", "对策", "其他"]
# 可晋升为申论规范词的类型
CORPUS_TERM_KINDS = ("词", "专名", "成语", "诗典", "短语")
CORPUS_STATUSES = ["inbox", "clarified", "owned", "used"]

