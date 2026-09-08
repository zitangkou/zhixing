"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class RmrbArticleOut(BaseModel):
    id: str
    title: str
    source: str
    sourceUrl: str = ""
    publishDate: str
    summary: str
    content: str
    tags: list[str] = []
    isPublished: bool
    sortOrder: int
    readCount: int
    createdAt: datetime
    updatedAt: datetime


class RmrbArticleCreate(BaseModel):
    title: str
    source: str = "人民时评"
    sourceUrl: str = ""
    publishDate: str = ""
    summary: str = ""
    content: str = ""
    tags: list[str] = []
    isPublished: bool = True
    sortOrder: int = 0


class RmrbArticleUpdate(BaseModel):
    title: str | None = None
    source: str | None = None
    sourceUrl: str | None = None
    publishDate: str | None = None
    summary: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    isPublished: bool | None = None
    sortOrder: int | None = None


class ShenlunMineTermItem(BaseModel):
    term: str
    category: str = "其他"
    plainWord: str = ""


class ShenlunQuoteItem(BaseModel):
    text: str = ""
    source: str = ""  # 来源，如：清代万斯大
    meaning: str = ""  # 释义


class ShenlunVerbItem(BaseModel):
    verb: str = ""
    usage: str = ""
    category: str = "其他"


class ShenlunArgumentFieldValue(BaseModel):
    key: str
    label: str = ""
    content: str = ""


class ShenlunArgumentPoint(BaseModel):
    title: str = ""  # 分论点正文
    claim: str = ""  # 兼容旧数据
    evidence: str = ""
    summary: str = ""
    method: str = ""  # 论证方法名，如：点例排比 + 类比延伸
    methodNote: str = ""  # 方法说明
    template: str = ""  # 套用模板


class ShenlunArgumentSkeleton(BaseModel):
    templateId: str = ""
    templateName: str = ""
    mode: str = "points"  # linear | points
    overview: str = ""  # 总论点
    conclusion: str = ""  # 总结
    overviewMethod: str = ""  # 总论点论证方法
    overviewTemplate: str = ""  # 总论点论证模板
    fields: list[ShenlunArgumentFieldValue] = []
    points: list[ShenlunArgumentPoint] = []


class ShenlunTemplateItem(BaseModel):
    type: str = "dialectic"  # sentence type code
    typeName: str = ""
    original: str = ""
    template: str = ""
    imitate: str = ""


class ShenlunMineLogOut(BaseModel):
    id: str
    mineDate: str
    articleId: str | None = None
    articleTitle: str
    sourceExcerpt: str = ""
    argumentChain: str = ""
    templateSentence: str = ""
    terms: list[ShenlunMineTermItem] = []
    quotes: list[ShenlunQuoteItem] = []
    verbs: list[ShenlunVerbItem] = []
    argument: ShenlunArgumentSkeleton = ShenlunArgumentSkeleton()
    templates: list[ShenlunTemplateItem] = []
    createdAt: datetime
    updatedAt: datetime


class ShenlunMineLogUpsert(BaseModel):
    mineDate: str | None = None
    articleId: str | None = None
    articleTitle: str = ""
    sourceExcerpt: str = ""
    argumentChain: str = ""
    templateSentence: str = ""
    terms: list[ShenlunMineTermItem | str] = []
    quotes: list[ShenlunQuoteItem] = []
    verbs: list[ShenlunVerbItem] = []
    argument: ShenlunArgumentSkeleton | None = None
    templates: list[ShenlunTemplateItem] = []


class ShenlunMineLogUpdate(BaseModel):
    articleId: str | None = None
    articleTitle: str | None = None
    sourceExcerpt: str | None = None
    argumentChain: str | None = None
    templateSentence: str | None = None
    terms: list[ShenlunMineTermItem | str] | None = None
    quotes: list[ShenlunQuoteItem] | None = None
    verbs: list[ShenlunVerbItem] | None = None
    argument: ShenlunArgumentSkeleton | None = None
    templates: list[ShenlunTemplateItem] | None = None


class ShenlunSkeletonFieldDef(BaseModel):
    key: str
    label: str
    placeholder: str = ""


class ShenlunSkeletonStructure(BaseModel):
    mode: str = "linear"  # linear | points
    fields: list[ShenlunSkeletonFieldDef] = []
    overviewLabel: str = "全文总骨架"
    overviewPlaceholder: str = ""
    pointFields: list[ShenlunSkeletonFieldDef] = []


class ShenlunTermCategoryOut(BaseModel):
    id: str
    name: str
    kind: str = "term"  # term | verb
    sortOrder: int = 0
    isEnabled: bool = True


class ShenlunTermCategoryCreate(BaseModel):
    name: str
    kind: str = "term"
    sortOrder: int = 0
    isEnabled: bool = True


class ShenlunTermCategoryUpdate(BaseModel):
    name: str | None = None
    kind: str | None = None
    sortOrder: int | None = None
    isEnabled: bool | None = None


class ShenlunSkeletonTemplateOut(BaseModel):
    id: str
    name: str
    description: str = ""
    mode: str = "linear"
    structure: ShenlunSkeletonStructure
    sortOrder: int = 0
    isEnabled: bool = True


class ShenlunSkeletonTemplateCreate(BaseModel):
    name: str
    description: str = ""
    mode: str = "linear"
    structure: ShenlunSkeletonStructure | None = None
    sortOrder: int = 0
    isEnabled: bool = True


class ShenlunSkeletonTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    mode: str | None = None
    structure: ShenlunSkeletonStructure | None = None
    sortOrder: int | None = None
    isEnabled: bool | None = None


class ShenlunSentenceTypeOut(BaseModel):
    id: str
    code: str
    name: str
    tip: str = ""
    sortOrder: int = 0
    isEnabled: bool = True


class ShenlunSentenceTypeCreate(BaseModel):
    code: str
    name: str
    tip: str = ""
    sortOrder: int = 0
    isEnabled: bool = True


class ShenlunSentenceTypeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    tip: str | None = None
    sortOrder: int | None = None
    isEnabled: bool | None = None


class ShenlunArgumentMethodOut(BaseModel):
    id: str
    name: str
    scope: str = "point"  # overview | point
    note: str = ""
    template: str = ""
    sortOrder: int = 0
    isEnabled: bool = True


class ShenlunArgumentMethodCreate(BaseModel):
    name: str
    scope: str = "point"
    note: str = ""
    template: str = ""
    sortOrder: int = 0
    isEnabled: bool = True


class ShenlunArgumentMethodUpdate(BaseModel):
    name: str | None = None
    scope: str | None = None
    note: str | None = None
    template: str | None = None
    sortOrder: int | None = None
    isEnabled: bool | None = None


class ShenlunMetaOut(BaseModel):
    termCategories: list[ShenlunTermCategoryOut] = []
    verbCategories: list[ShenlunTermCategoryOut] = []
    skeletonTemplates: list[ShenlunSkeletonTemplateOut] = []
    sentenceTypes: list[ShenlunSentenceTypeOut] = []
    argumentMethodPresets: list[ShenlunArgumentMethodOut] = []


class ShenlunNormTermOut(BaseModel):
    id: str
    term: str
    category: str = "其他"
    usageNote: str
    sourceTitle: str
    exampleSentence: str
    articleId: str | None = None
    familiarity: int
    mastered: bool
    createdAt: datetime


class ShenlunNormTermAdd(BaseModel):
    term: str
    category: str = "其他"
    usageNote: str = ""
    sourceTitle: str = ""
    exampleSentence: str = ""
    articleId: str | None = None


class ShenlunNormTermUpdate(BaseModel):
    category: str | None = None
    usageNote: str | None = None
    exampleSentence: str | None = None
    familiarity: int | None = None
    mastered: bool | None = None
    sourceTitle: str | None = None


class ShenlunStatsOut(BaseModel):
    weekMineDays: int
    weekMineTarget: int = 7
    termCount: int
    learningTermCount: int
    todayMined: bool
    weekDrillCount: int = 0


class ShenlunDrillLogOut(BaseModel):
    id: str
    drillType: str
    content: str
    prompt: str
    refMineId: str | None = None
    refTermIds: list[str] = []
    createdAt: datetime


class ShenlunDrillCreate(BaseModel):
    drillType: str  # sentence | imitate | oral
    content: str
    prompt: str = ""
    refMineId: str | None = None
    refTermIds: list[str] = []


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

