"""Pydantic schema · 知识框架"""
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


# ===== 新草稿 / 发布 / 学员 maps =====


class KnowledgeTreeMetaOut(BaseModel):
    treeKey: str
    title: str
    sortOrder: int = 0
    isVisible: bool = False
    draftRevision: int = 0
    draftUpdatedAt: datetime | None = None
    latestVersion: int = 0
    liveVersion: int = 0
    hasUnpublishedChanges: bool = False
    liveNodeCount: int = 0
    livePublishedAt: datetime | None = None


_MD_MAX = 1_000_000  # 与 knowledge_md.MAX_MD_CHARS 一致


class KnowledgeTreeCreateBody(BaseModel):
    treeKey: str = Field(min_length=1, max_length=32, pattern=r"^[0-9A-Za-z_\-\u4e00-\u9fff]+$")
    title: str = Field(default="", max_length=64)
    md: str = Field(default="", max_length=_MD_MAX)


class KnowledgeTreePatchBody(BaseModel):
    title: str | None = None
    sortOrder: int | None = None
    isVisible: bool | None = None


class KnowledgeDocOut(BaseModel):
    treeKey: str
    title: str
    mdDraft: str
    draftRevision: int
    draftUpdatedAt: datetime | None = None
    draftUpdatedBy: str = ""
    liveVersion: int = 0
    liveMd: str = ""


class KnowledgeDocPutBody(BaseModel):
    md: str = Field(max_length=_MD_MAX)
    baseRevision: int


class KnowledgeDocPutOut(BaseModel):
    draftRevision: int
    draftUpdatedAt: datetime | None = None
    issues: list[dict[str, Any]] = Field(default_factory=list)


class KnowledgePreviewBody(BaseModel):
    md: str = Field(max_length=_MD_MAX)


class KnowledgeActivateBody(BaseModel):
    expectedLive: int | None = None
    allowNoAssets: bool = False


class KnowledgePublishBody(BaseModel):
    baseRevision: int
    note: str = Field(default="", max_length=256)


class KnowledgeUserStateUpdate(BaseModel):
    myNote: str | None = None
    isStarred: bool | None = None


class KnowledgeMapListItemOut(BaseModel):
    treeKey: str
    title: str
    version: int
    publishedAt: datetime | None = None
    nodeCount: int = 0
    cover: dict[str, Any] | None = None


class KnowledgeMapDetailOut(BaseModel):
    treeKey: str
    title: str
    version: int
    publishedAt: datetime | None = None
    tree: dict[str, Any]
    manifest: dict[str, Any] = Field(default_factory=dict)
