"""ORM 模型 · 域模块

按业务域拆分，统一由 app/models/__init__.py re-export，保持 from app.models import X 兼容。
"""
from datetime import datetime

from app.models.base import (
    Base,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Mapped,
    gen_id,
    mapped_column,
    relationship,
    utcnow,
)
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("cat"))
    parent_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("categories.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id", back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("art"))
    title: Mapped[str] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(String(512), default="")
    publish_date: Mapped[str] = mapped_column(String(10))
    summary: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    sections: Mapped[str] = mapped_column(Text, default="[]")  # JSON 多层级小节
    tags: Mapped[str] = mapped_column(String(256), default="[]")  # JSON
    mind_map: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    category_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("categories.id"), nullable=True, index=True)
    category_path: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    importance: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    status: Mapped[str] = mapped_column(String(16), default="published")
    allow_quiz: Mapped[bool] = mapped_column(Boolean, default=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    is_daily: Mapped[bool] = mapped_column(Boolean, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    read_count: Mapped[int] = mapped_column(Integer, default=0)
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    questions: Mapped[list["Question"]] = relationship(back_populates="article")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("q"))
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), index=True)
    type: Mapped[str] = mapped_column(String(16))  # single | multiple | judge
    stem: Mapped[str] = mapped_column(Text)
    options: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    correct_answer: Mapped[str] = mapped_column(Text)  # JSON string or plain
    analysis: Mapped[str] = mapped_column(Text)
    source_sentence: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="approved")  # pending | approved | rejected
    origin: Mapped[str] = mapped_column(String(16), default="manual")  # crawl_auto | manual | seed | ai
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    article: Mapped[Article] = relationship(back_populates="questions")


