"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ArticleSection, MindMapNode
class CategoryOut(BaseModel):
    id: str
    name: str
    parentId: str | None = None
    sortOrder: int = 0
    children: list["CategoryOut"] = Field(default_factory=list)


class CategoryCreate(BaseModel):
    name: str
    parent_id: str | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class ArticleCreate(BaseModel):
    title: str
    source: str
    source_url: str = ""
    publish_date: str
    summary: str
    content: str = ""
    sections: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    mind_map: dict[str, Any] = Field(default_factory=dict)
    category_id: str | None = None
    importance: int = 3
    status: str = "draft"
    allow_quiz: bool = True
    is_published: bool = False
    is_daily: bool = False
    auto_generate_questions: bool = False


class ArticleInferMetadataBody(BaseModel):
    content: str = Field(min_length=1)
    title: str = ""


class ArticleInferMetadataOut(BaseModel):
    title: str
    content: str
    source: str
    source_url: str = ""
    publish_date: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    category_id: str | None = None
    category_name: str | None = None
    importance: int = 3


class ArticleUpdate(BaseModel):
    title: str | None = None
    source: str | None = None
    source_url: str | None = None
    publish_date: str | None = None
    summary: str | None = None
    content: str | None = None
    sections: list[dict[str, Any]] | None = None
    tags: list[str] | None = None
    mind_map: dict[str, Any] | None = None
    category_id: str | None = None
    importance: int | None = None
    status: str | None = None
    allow_quiz: bool | None = None
    is_published: bool | None = None
    is_daily: bool | None = None
    is_featured: bool | None = None


class QuestionOut(BaseModel):
    id: str
    articleId: str
    type: str
    stem: str
    options: list[str] | None = None
    correctAnswer: str | list[str]
    analysis: str
    sourceSentence: str
    status: str = "approved"
    origin: str = "manual"
    isActive: bool = True


class QuestionCreate(BaseModel):
    article_id: str
    type: str
    stem: str
    options: list[str] = Field(default_factory=list)
    correct_answer: str | list[str]
    analysis: str
    source_sentence: str = ""
    status: str = "approved"
    origin: str = "manual"
    is_active: bool = True


class QuestionUpdate(BaseModel):
    type: str | None = None
    stem: str | None = None
    options: list[str] | None = None
    correct_answer: str | list[str] | None = None
    analysis: str | None = None
    source_sentence: str | None = None
    status: str | None = None
    is_active: bool | None = None


class QuestionBatchApprove(BaseModel):
    question_ids: list[str] = Field(default_factory=list)


class QuestionBatchDelete(BaseModel):
    question_ids: list[str] = Field(default_factory=list)


class ArticleBatchIds(BaseModel):
    article_ids: list[str] = Field(default_factory=list)


class ArticleBatchPublish(BaseModel):
    article_ids: list[str] = Field(default_factory=list)
    approve_questions: bool = True


class ArticleBatchCategory(BaseModel):
    article_ids: list[str] = Field(default_factory=list)
    category_id: str | None = None


class AiGenerateQuestionsBody(BaseModel):
    section_ids: list[str] | None = None
    single: int = Field(default=8, ge=0, le=50)
    multiple: int = Field(default=4, ge=0, le=50)
    judge: int = Field(default=2, ge=0, le=20)


class ImportQuestionsBody(BaseModel):
    markdown: str = Field(min_length=10)
    pending: bool = True
    replace_existing: bool = False


class ImportArticleMarkdownBody(BaseModel):
    markdown: str = Field(min_length=20)
    status: str = "pending"
    category_id: str | None = None
    is_featured: bool = False
    source: str = ""
    publish_date: str = ""
    tags: list[str] = Field(default_factory=list)


class ArticleOut(BaseModel):
    id: str
    title: str
    source: str
    publishDate: str
    summary: str
    sections: list[ArticleSection] = Field(default_factory=list)
    content: str
    tags: list[str]
    mindMap: MindMapNode
    readCount: int | None = None
    isFeatured: bool = False
    categoryId: str | None = None
    categoryName: str | None = None
    categoryPath: list[str] = Field(default_factory=list)
    importance: int = 3
    importanceLabel: str = "掌握"
    status: str = "published"
    allowQuiz: bool = True
    isDaily: bool = False


