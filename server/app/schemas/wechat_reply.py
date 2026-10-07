"""微信公众号固定消息回复的后台配置契约。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WechatKeywordRule(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=64)
    keywords: list[str] = Field(default_factory=list, max_length=50)
    matchType: Literal["exact", "contains"] = "exact"
    responseText: str = Field(default="", max_length=4000)
    enabled: bool = True
    priority: int = Field(default=100, ge=-10000, le=10000)


class WechatReplyConfig(BaseModel):
    welcomeReply: str = Field(default="", max_length=4000)
    fallbackReply: str = Field(default="", max_length=4000)
    unsupportedMessageReply: str = Field(default="", max_length=4000)
    unsupportedEventReply: str = Field(default="", max_length=4000)
    keywordRules: list[WechatKeywordRule] = Field(default_factory=list, max_length=200)


class WechatReplyPreviewIn(BaseModel):
    message: str = Field(default="", max_length=1000)
    msgType: Literal["text", "event"] = "text"
    event: str = Field(default="", max_length=32)
    config: WechatReplyConfig | None = None


class WechatReplyPreviewOut(BaseModel):
    intent: str
    reply: str | None
    matchedRuleId: str = ""


class WechatReplyReleaseOut(BaseModel):
    id: str
    version: int
    publishedByName: str
    rollbackFromVersion: int | None = None
    publishedAt: datetime
    isCurrent: bool = False


class WechatReplyStateOut(BaseModel):
    draft: WechatReplyConfig
    active: WechatReplyConfig
    activeReleaseId: str | None = None
    activeVersion: int | None = None
    updatedByName: str = ""
    updatedAt: datetime | None = None
    releases: list[WechatReplyReleaseOut] = Field(default_factory=list)


class WechatReplyValidationOut(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
