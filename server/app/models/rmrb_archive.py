"""人民日报全量文章档案；与面向学员的时评精拆数据分域保存。"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, gen_id, utcnow


class RmrbArchiveIssue(Base):
    __tablename__ = "rmrb_archive_issues"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rmi"))
    issue_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    publication_code: Mapped[str] = mapped_column(String(32), default="rmrb", index=True)
    edition_label: Mapped[str] = mapped_column(String(128), default="")
    expected_page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="discovered", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    pages: Mapped[list["RmrbArchivePage"]] = relationship(back_populates="issue", cascade="all, delete-orphan")


class RmrbArchivePage(Base):
    __tablename__ = "rmrb_archive_pages"
    __table_args__ = (UniqueConstraint("issue_id", "page_no", name="uq_rmrb_archive_issue_page"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rmp"))
    issue_id: Mapped[str] = mapped_column(ForeignKey("rmrb_archive_issues.id", ondelete="CASCADE"), index=True)
    page_no: Mapped[str] = mapped_column(String(8), index=True)
    page_name: Mapped[str] = mapped_column(String(128), default="")
    page_title: Mapped[str] = mapped_column(String(256), default="")
    page_kind: Mapped[str] = mapped_column(String(32), default="regular")
    directory_url: Mapped[str] = mapped_column(String(1024), default="")
    directory_status: Mapped[str] = mapped_column(String(32), default="discovered")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    issue: Mapped[RmrbArchiveIssue] = relationship(back_populates="pages")
    articles: Mapped[list["RmrbArchiveArticle"]] = relationship(back_populates="page")


class RmrbArchiveArticle(Base):
    __tablename__ = "rmrb_archive_articles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rma"))
    issue_id: Mapped[str] = mapped_column(ForeignKey("rmrb_archive_issues.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[str | None] = mapped_column(ForeignKey("rmrb_archive_pages.id", ondelete="SET NULL"), nullable=True, index=True)
    page_no: Mapped[str] = mapped_column(String(8), default="", index=True)
    page_name: Mapped[str] = mapped_column(String(128), default="", index=True)
    page_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    primary_source_url: Mapped[str] = mapped_column(String(1024), default="")
    source_channel: Mapped[str] = mapped_column(String(64), default="people_daily_epaper", index=True)
    display_title: Mapped[str] = mapped_column(String(512), index=True)
    headline: Mapped[str] = mapped_column(String(512), default="", index=True)
    subtitle: Mapped[str] = mapped_column(String(512), default="")
    column_label: Mapped[str] = mapped_column(String(256), default="", index=True)
    series_label: Mapped[str] = mapped_column(String(256), default="")
    eyebrow: Mapped[str] = mapped_column(String(256), default="")
    author_line: Mapped[str] = mapped_column(String(512), default="")
    editor_line: Mapped[str] = mapped_column(String(512), default="")
    authors_json: Mapped[str] = mapped_column(Text, default="[]")
    publication_time: Mapped[str] = mapped_column(String(64), default="")
    record_class: Mapped[str] = mapped_column(String(32), default="article", index=True)
    source_article_type: Mapped[str] = mapped_column(String(40), default="undetermined", index=True)
    expression_modes_json: Mapped[str] = mapped_column(Text, default="[]")
    topics_json: Mapped[str] = mapped_column(Text, default="[]")
    exam_relevance: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    exam_relevance_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    retention_tier: Mapped[str] = mapped_column(String(24), default="metadata_only", index=True)
    body_status: Mapped[str] = mapped_column(String(32), default="not_fetched", index=True)
    source_status: Mapped[str] = mapped_column(String(32), default="unverified", index=True)
    rights_status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    review_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    classification_suggestion_json: Mapped[str] = mapped_column(Text, default="{}")
    classification_method: Mapped[str] = mapped_column(String(40), default="none", index=True)
    classification_feature_key: Mapped[str] = mapped_column(String(128), default="", index=True)
    classification_history_json: Mapped[str] = mapped_column(Text, default="[]")
    current_revision: Mapped[int] = mapped_column(Integer, default=0)
    extra_json: Mapped[str] = mapped_column(Text, default="{}")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    page: Mapped[RmrbArchivePage | None] = relationship(back_populates="articles")
    sources: Mapped[list["RmrbArchiveSource"]] = relationship(back_populates="article", cascade="all, delete-orphan")
    revisions: Mapped[list["RmrbArchiveRevision"]] = relationship(back_populates="article", cascade="all, delete-orphan")


class RmrbArchiveSource(Base):
    __tablename__ = "rmrb_archive_sources"
    __table_args__ = (UniqueConstraint("article_id", "source_url", name="uq_rmrb_archive_article_source_url"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rms"))
    article_id: Mapped[str] = mapped_column(ForeignKey("rmrb_archive_articles.id", ondelete="CASCADE"), index=True)
    source_channel: Mapped[str] = mapped_column(String(64), default="")
    source_url: Mapped[str] = mapped_column(String(1024))
    source_relation: Mapped[str] = mapped_column(String(40), default="directory")
    source_display_title: Mapped[str] = mapped_column(String(512), default="")
    evidence_type: Mapped[str] = mapped_column(String(32), default="directory")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    article: Mapped[RmrbArchiveArticle] = relationship(back_populates="sources")


class RmrbArchiveRevision(Base):
    __tablename__ = "rmrb_archive_revisions"
    __table_args__ = (UniqueConstraint("article_id", "revision_no", name="uq_rmrb_archive_article_revision"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rmv"))
    article_id: Mapped[str] = mapped_column(ForeignKey("rmrb_archive_articles.id", ondelete="CASCADE"), index=True)
    revision_no: Mapped[int] = mapped_column(Integer)
    body_storage_key: Mapped[str] = mapped_column(String(512))
    body_sha256: Mapped[str] = mapped_column(String(64), index=True)
    body_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    body_status: Mapped[str] = mapped_column(String(32), default="full")
    parser_version: Mapped[str] = mapped_column(String(64), default="manual-v1")
    change_note: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    article: Mapped[RmrbArchiveArticle] = relationship(back_populates="revisions")


class RmrbArchiveBatch(Base):
    __tablename__ = "rmrb_archive_batches"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rmb"))
    run_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    trigger_mode: Mapped[str] = mapped_column(String(24), default="manual")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    expected_page_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_page_count: Mapped[int] = mapped_column(Integer, default=0)
    discovered_article_count: Mapped[int] = mapped_column(Integer, default=0)
    created_article_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_page_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_source_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
