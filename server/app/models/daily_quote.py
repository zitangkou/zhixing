"""独立每日金句：不保存文章全文，不依赖旧采集档案。"""
from datetime import date, datetime
from sqlalchemy import Date
from app.models.base import Base, Mapped, mapped_column, String, Text, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, gen_id, utcnow


class DailyQuote(Base):
    __tablename__ = 'daily_quotes'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id('dq'))
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    collected_date: Mapped[date] = mapped_column(Date, index=True)
    text: Mapped[str] = mapped_column(Text)
    attributes_json: Mapped[str] = mapped_column(Text, default='{}')
    review_status: Mapped[str] = mapped_column(String(24), default='pending', index=True)
    audit_status: Mapped[str] = mapped_column(String(16), default='pending')  # pending | passed | rejected
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str] = mapped_column(String(128), default='')
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class DailyQuoteSelection(Base):
    __tablename__ = 'daily_quote_selections'
    __table_args__ = (UniqueConstraint('issue_date', 'quote_id'),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id('dqs'))
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey('daily_quotes.id', ondelete='CASCADE'))
    position: Mapped[int] = mapped_column(Integer, default=0)


class DailyQuoteFeedback(Base):
    """按刊期保存人工精选/淘汰反馈，供日后复盘与稳定规则迭代。"""
    __tablename__ = 'daily_quote_feedback'
    __table_args__ = (UniqueConstraint('issue_date', 'quote_id'),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id('dqf'))
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey('daily_quotes.id', ondelete='CASCADE'), index=True)
    decision: Mapped[str] = mapped_column(String(24), index=True)  # selected | not_selected | rejected
    reason_codes_json: Mapped[str] = mapped_column(Text, default='[]')
    note: Mapped[str] = mapped_column(Text, default='')
    reviewer: Mapped[str] = mapped_column(String(128), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class DailyQuoteJob(Base):
    __tablename__ = 'daily_quote_jobs'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id('dqj'))
    issue_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default='queued')
    progress_json: Mapped[str] = mapped_column(Text, default='{}')  # URLs/状态/计数，不含全文或模型响应
    error: Mapped[str] = mapped_column(String(256), default='')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
