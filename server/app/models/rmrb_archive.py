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


class RmrbCommentArticle(Base):
    """评论文章学习物料流水；文章正文仍以全量档案版本为唯一来源。"""
    __tablename__ = "rmrb_comment_articles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rmc"))
    article_id: Mapped[str] = mapped_column(ForeignKey("rmrb_archive_articles.id", ondelete="CASCADE"), unique=True, index=True)
    article: Mapped[RmrbArchiveArticle] = relationship()
    inclusion_reason: Mapped[str] = mapped_column(String(256), default="")
    workflow_status: Mapped[str] = mapped_column(String(32), default="identified", index=True)
    article_review_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    article_review_note: Mapped[str] = mapped_column(Text, default="")
    article_reviewed_by: Mapped[str] = mapped_column(String(128), default="")
    article_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    analysis_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    original_md_key: Mapped[str] = mapped_column(String(512), default="")
    original_html_key: Mapped[str] = mapped_column(String(512), default="")
    analysis_md_key: Mapped[str] = mapped_column(String(512), default="")
    analysis_html_key: Mapped[str] = mapped_column(String(512), default="")
    analysis_version: Mapped[str] = mapped_column(String(32), default="shenlun-v2.23-adapted")
    analysis_error: Mapped[str] = mapped_column(Text, default="")
    review_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(128), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class RmrbArticleEvaluation(Base):
    """全量档案文章的 AI 评估版本；每次重评保留独立结果和人工审核记录。"""
    __tablename__ = "rmrb_article_evaluations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rme"))
    article_id: Mapped[str] = mapped_column(ForeignKey("rmrb_archive_articles.id", ondelete="CASCADE"), index=True)
    article: Mapped[RmrbArchiveArticle] = relationship()
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    review_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    prompt_version: Mapped[str] = mapped_column(String(40), default="rmrb-eval-v1")
    model_name: Mapped[str] = mapped_column(String(128), default="")
    body_sha256: Mapped[str] = mapped_column(String(64), default="", index=True)
    body_char_count: Mapped[int] = mapped_column(Integer, default=0)
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    reviewed_result_json: Mapped[str] = mapped_column(Text, default="")
    review_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(128), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class RmrbCommentQuote(Base):
    """评论文章金句；保留 AI 草稿与人工审核状态，引用必须能回溯原文。"""
    __tablename__ = "rmrb_comment_quotes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rmq"))
    comment_article_id: Mapped[str] = mapped_column(ForeignKey("rmrb_comment_articles.id", ondelete="CASCADE"), index=True)
    comment_article: Mapped[RmrbCommentArticle] = relationship()
    text: Mapped[str] = mapped_column(Text, default="")
    quote_type: Mapped[str] = mapped_column(String(32), default="argument")
    topics_json: Mapped[str] = mapped_column(Text, default="[]")
    use_cases_json: Mapped[str] = mapped_column(Text, default="[]")
    application_example: Mapped[str] = mapped_column(Text, default="")
    source_evidence: Mapped[str] = mapped_column(Text, default="")
    collection_method: Mapped[str] = mapped_column(String(16), default="manual")
    review_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    review_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(128), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class RmrbCommentExclusionRule(Base):
    """Reusable article exclusion inferred from a manually rejected title series."""
    __tablename__ = "rmrb_comment_exclusion_rules"
    __table_args__ = (UniqueConstraint("rule_type", "rule_value", name="uq_rmrb_comment_exclusion_rule"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rmer"))
    rule_type: Mapped[str] = mapped_column(String(32), default="title_prefix", index=True)
    rule_value: Mapped[str] = mapped_column(String(64), default="", index=True)
    source_article_id: Mapped[str] = mapped_column(ForeignKey("rmrb_archive_articles.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(128), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RmrbQuoteOpsPackage(Base):
    """Approved quote collection and editable daily operations deliverables."""
    __tablename__ = "rmrb_quote_ops_packages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rqo"))
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    topic: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(256), default="")
    channels_json: Mapped[str] = mapped_column(Text, default='["wechat","xiaohongshu"]')
    xhs_title: Mapped[str] = mapped_column(String(256), default="")
    xhs_content: Mapped[str] = mapped_column(Text, default="")
    wechat_title: Mapped[str] = mapped_column(String(256), default="")
    wechat_summary: Mapped[str] = mapped_column(Text, default="")
    wechat_content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    xhs_published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    wechat_published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class RmrbQuoteOpsPackageItem(Base):
    __tablename__ = "rmrb_quote_ops_package_items"
    __table_args__ = (UniqueConstraint("package_id", "quote_id", name="uq_rmrb_quote_ops_item"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rqoi"))
    package_id: Mapped[str] = mapped_column(ForeignKey("rmrb_quote_ops_packages.id", ondelete="CASCADE"), index=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey("rmrb_comment_quotes.id", ondelete="CASCADE"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
