from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, HttpUrl, field_validator

IDEA_TYPES = {"unclassified", "quick_idea", "project", "series", "content_topic", "product_feature", "method"}
STATUSES = {"inbox", "to_validate", "in_progress", "settled", "paused"}

class IdeaCreate(BaseModel):
    title: str = Field(default="", max_length=120)
    originalText: str = Field(default="", max_length=20000)
    description: str = Field(default="", max_length=30000)
    ideaType: str = "unclassified"
    status: str = "inbox"
    priority: str = "normal"
    starred: bool = False
    parentId: str | None = None
    visibility: str = "private"
    nextAction: str = Field(default="", max_length=500)
    plannedAt: datetime | None = None
    reviewAt: datetime | None = None
    conclusion: str = Field(default="", max_length=10000)
    pauseReason: str = Field(default="", max_length=2000)
    tagNames: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("ideaType")
    @classmethod
    def valid_type(cls, value):
        if value not in IDEA_TYPES: raise ValueError("创意类型无效")
        return value
    @field_validator("status")
    @classmethod
    def valid_status(cls, value):
        if value not in STATUSES: raise ValueError("创意状态无效")
        return value
    @field_validator("priority")
    @classmethod
    def valid_create_priority(cls, value):
        if value not in {"normal", "important", "urgent"}: raise ValueError("优先级无效")
        return value
    @field_validator("tagNames")
    @classmethod
    def valid_tag_names(cls, value):
        if any(not name.strip() or len(name.strip())>48 for name in value): raise ValueError("标签不能为空且不能超过 48 字")
        return value
    @field_validator("visibility")
    @classmethod
    def valid_visibility(cls, value):
        if value not in {"private", "shared"}: raise ValueError("可见范围无效")
        return value

class IdeaPatch(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=30000)
    ideaType: str | None = None
    priority: str | None = None
    starred: bool | None = None
    parentId: str | None = None
    visibility: str | None = None
    nextAction: str | None = Field(default=None, max_length=500)
    plannedAt: datetime | None = None
    reviewAt: datetime | None = None
    conclusion: str | None = Field(default=None, max_length=10000)
    pauseReason: str | None = Field(default=None, max_length=2000)
    tagNames: list[str] | None = Field(default=None, max_length=20)
    version: int

    @field_validator("ideaType")
    @classmethod
    def valid_patch_type(cls, value):
        if value is not None and value not in IDEA_TYPES: raise ValueError("创意类型无效")
        return value
    @field_validator("priority")
    @classmethod
    def valid_priority(cls, value):
        if value is not None and value not in {"normal", "important", "urgent"}: raise ValueError("优先级无效")
        return value
    @field_validator("title", "description", "ideaType", "priority", "starred", "visibility", "nextAction", "conclusion", "pauseReason", "tagNames")
    @classmethod
    def reject_null_nonnullable(cls, value):
        if value is None: raise ValueError("此字段不能设为空值")
        return value
    @field_validator("visibility")
    @classmethod
    def valid_patch_visibility(cls, value):
        if value is not None and value not in {"private", "shared"}: raise ValueError("可见范围无效")
        return value

class TransitionBody(BaseModel):
    status: str
    reason: str = Field(default="", max_length=2000)
    version: int

class CaptureBody(BaseModel):
    text: str = Field(default="", max_length=20000)
    title: str = Field(default="", max_length=120)
    url: str = Field(default="", max_length=2048)
    idempotencyKey: str = Field(default="", max_length=100)

class MaterialIn(BaseModel):
    kind: str = "note"
    title: str = Field(default="", max_length=240)
    sourceName: str = Field(default="", max_length=160)
    author: str = Field(default="", max_length=120)
    url: str = Field(default="", max_length=2048)
    excerpt: str = Field(default="", max_length=30000)
    insight: str = Field(default="", max_length=10000)
    locator: str = Field(default="", max_length=240)
    visibility: str = "private"
    referenceType: str = Field(default="", max_length=32)
    referenceId: str = Field(default="", max_length=64)

    @field_validator("kind", "title", "sourceName", "author", "url", "excerpt", "insight", "locator", "visibility")
    @classmethod
    def reject_null_material_fields(cls, value):
        if value is None: raise ValueError("此字段不能设为空值")
        return value

class PracticeIn(BaseModel):
    kind: str = "research"
    title: str = Field(default="", max_length=240)
    occurredAt: datetime | None = None
    action: str = Field(default="", max_length=20000)
    expectation: str = Field(default="", max_length=10000)
    result: str = Field(default="", max_length=20000)
    decision: str = Field(default="", max_length=24)
    nextAction: str = Field(default="", max_length=500)
    metrics: list[dict[str, Any]] = Field(default_factory=list, max_length=30)
    resultLinks: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    minutes: int | None = Field(default=None, ge=0, le=100000)
    cost: float | None = Field(default=None, ge=0, le=100000000)
    updateNextAction: bool = False
    version: int | None = None

    @field_validator("kind")
    @classmethod
    def valid_practice_kind(cls, value):
        if value not in {"research", "production", "test", "publish", "review"}: raise ValueError("实践类型无效")
        return value
    @field_validator("decision")
    @classmethod
    def valid_decision(cls, value):
        if value not in {"", "continue", "adjust", "stop"}: raise ValueError("实践判断无效")
        return value

class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=48)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value):
        if not value.strip(): raise ValueError("标签不能为空")
        return value.strip()

class MaterialPatch(BaseModel):
    kind: str | None = None
    title: str | None = Field(default=None, max_length=240)
    sourceName: str | None = Field(default=None, max_length=160)
    author: str | None = Field(default=None, max_length=120)
    url: str | None = Field(default=None, max_length=2048)
    excerpt: str | None = Field(default=None, max_length=30000)
    insight: str | None = Field(default=None, max_length=10000)
    locator: str | None = Field(default=None, max_length=240)
    visibility: str | None = None
    version: int

    @field_validator("kind", "title", "sourceName", "author", "url", "excerpt", "insight", "locator", "visibility")
    @classmethod
    def reject_null_patch_fields(cls, value):
        if value is None: raise ValueError("此字段不能设为空值")
        return value
