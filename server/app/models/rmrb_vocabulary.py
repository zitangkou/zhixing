"""人民日报词汇素材与可恢复采集批次。"""
from datetime import date, datetime
from sqlalchemy import Date, Integer
from app.models.base import Base, Mapped, mapped_column, String, Text, DateTime, utcnow, gen_id

class RmrbVocabulary(Base):
    __tablename__ = 'rmrb_vocabulary'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id('rv'))
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    phrase: Mapped[str] = mapped_column(String(100), index=True)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    source_title: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(1000))
    review_status: Mapped[str] = mapped_column(String(24), default='pending', index=True)
    review_note: Mapped[str] = mapped_column(Text, default='')
    reviewed_by: Mapped[str] = mapped_column(String(128), default='')
    payload_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

class RmrbVocabularyJob(Base):
    __tablename__ = 'rmrb_vocabulary_jobs'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id('rvj'))
    issue_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default='pending')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    progress_json: Mapped[str] = mapped_column(Text, default='{}')
    error: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
