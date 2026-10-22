"""时政文章选用审核、套题生成与发布版本。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, gen_id, utcnow


class TheorySourceReview(Base):
    __tablename__ = "theory_source_reviews"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("tsr"))
    archive_article_id: Mapped[str] = mapped_column(ForeignKey("rmrb_archive_articles.id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    signal: Mapped[str] = mapped_column(String(8), default="S3")
    value_score: Mapped[int] = mapped_column(Integer, default=0)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    review_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(64), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class TheoryQuizPaper(Base):
    __tablename__ = "theory_quiz_papers"
    __table_args__ = (UniqueConstraint("archive_article_id", "version", name="uq_theory_paper_article_version"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("tqp"))
    archive_article_id: Mapped[str] = mapped_column(ForeignKey("rmrb_archive_articles.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    questions_json: Mapped[str] = mapped_column(Text, default="[]")
    report_json: Mapped[str] = mapped_column(Text, default="{}")
    review_history_json: Mapped[str] = mapped_column(Text, default="[]")
    error: Mapped[str] = mapped_column(Text, default="")
    rules_version: Mapped[str] = mapped_column(String(64), default="theory-rubric-2026-10-v1")
    point_id: Mapped[str | None] = mapped_column(ForeignKey("theory_points.id"), nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_by: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
