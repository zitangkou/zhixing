"""人民日报全量档案管理接口 schema。"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

RmrbArticleType = Literal[
    "news_brief", "news_report", "feature_investigation", "profile", "interview",
    "commentary", "editorial", "theory", "policy_qa", "data_report", "picture_report",
    "cultural_work", "notice", "other", "undetermined",
]
RecordClass = Literal["article", "notice", "advertisement", "non_article", "undetermined"]
ExamRelevance = Literal["high", "medium", "low", "not_applicable", "pending"]
RetentionTier = Literal["full_text", "metadata_only", "temporary", "excluded"]
ManualReviewStatus = Literal["pending", "approved", "auto_approved", "revise"]


class RmrbArchiveArticleCreate(BaseModel):
    issueDate: date
    pageNo: str = Field(default="", max_length=8)
    pageName: str = Field(default="", max_length=128)
    pageTitle: str = Field(default="", max_length=256)
    pageKind: str = "regular"
    directoryUrl: str = ""
    primarySourceUrl: str = ""
    sourceChannel: str = "people_daily_epaper"
    displayTitle: str = Field(min_length=1, max_length=512)
    headline: str = Field(default="", max_length=512)
    subtitle: str = Field(default="", max_length=512)
    columnLabel: str = Field(default="", max_length=256)
    seriesLabel: str = Field(default="", max_length=256)
    eyebrow: str = Field(default="", max_length=256)
    authorLine: str = Field(default="", max_length=512)
    editorLine: str = Field(default="", max_length=512)
    authors: list[dict] = Field(default_factory=list)
    publicationTime: str = ""
    recordClass: RecordClass = "article"
    sourceArticleType: RmrbArticleType = "undetermined"
    expressionModes: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    examRelevance: ExamRelevance = "pending"
    examRelevanceReasons: list[str] = Field(default_factory=list)
    retentionTier: RetentionTier = "metadata_only"
    bodyText: str | None = Field(default=None, max_length=1_000_000)
    rightsStatus: str = "unknown"
    reviewStatus: ManualReviewStatus = "pending"
    sourceRelation: str = "primary_source"
    extra: dict = Field(default_factory=dict)


class RmrbArchiveArticleUpdate(BaseModel):
    pageNo: str | None = Field(default=None, max_length=8)
    pageName: str | None = Field(default=None, max_length=128)
    primarySourceUrl: str | None = None
    displayTitle: str | None = Field(default=None, min_length=1, max_length=512)
    headline: str | None = Field(default=None, max_length=512)
    subtitle: str | None = Field(default=None, max_length=512)
    columnLabel: str | None = Field(default=None, max_length=256)
    seriesLabel: str | None = Field(default=None, max_length=256)
    eyebrow: str | None = Field(default=None, max_length=256)
    authorLine: str | None = Field(default=None, max_length=512)
    editorLine: str | None = Field(default=None, max_length=512)
    authors: list[dict] | None = None
    publicationTime: str | None = None
    recordClass: RecordClass | None = None
    sourceArticleType: RmrbArticleType | None = None
    expressionModes: list[str] | None = None
    topics: list[str] | None = None
    examRelevance: ExamRelevance | None = None
    examRelevanceReasons: list[str] | None = None
    retentionTier: RetentionTier | None = None
    bodyText: str | None = Field(default=None, max_length=1_000_000)
    rightsStatus: str | None = None
    reviewStatus: ManualReviewStatus | None = None
    extra: dict | None = None


class RmrbArchiveSourceOut(BaseModel):
    id: str
    sourceChannel: str
    sourceUrl: str
    sourceRelation: str
    sourceDisplayTitle: str
    evidenceType: str
    fetchedAt: datetime


class RmrbArchiveRevisionOut(BaseModel):
    id: str
    revisionNo: int
    bodyStorageKey: str
    bodySha256: str
    bodySizeBytes: int
    bodyStatus: str
    parserVersion: str
    changeNote: str
    createdAt: datetime


class RmrbArchiveArticleOut(BaseModel):
    id: str
    issueDate: date
    pageNo: str
    pageName: str
    pageRefs: list[dict] = Field(default_factory=list)
    primarySourceUrl: str
    sourceChannel: str
    displayTitle: str
    headline: str
    subtitle: str
    columnLabel: str
    seriesLabel: str
    eyebrow: str
    authorLine: str
    editorLine: str
    authors: list[dict]
    publicationTime: str
    recordClass: str
    sourceArticleType: str
    expressionModes: list[str]
    topics: list[str]
    examRelevance: str
    examRelevanceReasons: list[str]
    classificationSuggestion: dict = Field(default_factory=dict)
    classificationMethod: str
    classificationFeatureKey: str
    classificationHistory: list[dict] = Field(default_factory=list)
    retentionTier: str
    bodyStatus: str
    sourceStatus: str
    rightsStatus: str
    reviewStatus: str
    currentRevision: int
    bodyText: str | None = None
    bodySizeBytes: int = 0
    bodySha256: str = ""
    sources: list[RmrbArchiveSourceOut] = Field(default_factory=list)
    revisions: list[RmrbArchiveRevisionOut] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime


class RmrbArchiveArticlePage(BaseModel):
    items: list[RmrbArchiveArticleOut]
    total: int
    page: int
    pageSize: int


class RmrbArchiveBatchRunBody(BaseModel):
    issueDate: date
