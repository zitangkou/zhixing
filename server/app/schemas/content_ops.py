from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class ContentEntryTarget(BaseModel):
    topicType: Literal["daily", "evergreen", "review"] = "daily"
    entryId: str = Field(default="", max_length=64)
    h5Path: str = Field(default="", max_length=512)
    miniappPath: str = Field(default="", max_length=512)
    qrScene: str = Field(default="", max_length=64)
    officialAccountKeyword: str = Field(default="", max_length=32)


class ContentPublishPackageCreate(BaseModel):
    productKey: Literal["shenlun", "theory"]
    templateId: str
    sourceType: str = Field(min_length=1, max_length=32)
    sourceId: str = Field(min_length=1, max_length=32)
    sourceTitle: str = ""
    campaignKey: str = ""
    deepLink: str = ""
    entryTarget: ContentEntryTarget = Field(default_factory=ContentEntryTarget)
    slotValues: dict[str, str] = Field(default_factory=dict)
    variants: dict[str, dict[str, Any]] = Field(default_factory=dict)
    plannedAt: datetime | None = None


class ContentPublishStatusBody(BaseModel):
    status: Literal["draft", "teaching_review", "ops_review", "ready", "published", "rejected"]
    reviewNote: str = ""
    checklist: dict[str, bool] = Field(default_factory=dict)


class ContentPublishPackageUpdate(BaseModel):
    sourceTitle: str | None = None
    campaignKey: str | None = None
    deepLink: str | None = None
    entryTarget: ContentEntryTarget | None = None
    slotValues: dict[str, str] | None = None
    variants: dict[str, dict[str, Any]] | None = None
    plannedAt: datetime | None = None


class ContentPackageGenerateFromArticle(BaseModel):
    productKey: Literal["shenlun", "theory"]
    templateId: str
    articleId: str
    campaignKey: str = ""
    deepLink: str = ""
    entryTarget: ContentEntryTarget = Field(default_factory=ContentEntryTarget)
    plannedAt: datetime | None = None


class EntryAttributionEventCreate(BaseModel):
    eventType: Literal["entry_link_opened", "miniapp_learning_started", "miniapp_learning_completed"]
    clientEventId: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    visitorId: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    entry: str = Field(min_length=1, max_length=64)
    content: str = Field(default="", max_length=64)
    section: str = Field(default="", max_length=32)
    channel: str = Field(default="direct", max_length=32)
    campaign: str = Field(default="", max_length=64)
    scene: str = Field(default="", max_length=64)
    platform: Literal["h5", "weapp", "unknown"] = "unknown"
    payload: dict[str, Any] = Field(default_factory=dict)
