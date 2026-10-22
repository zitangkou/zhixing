"""言遇口语内容与学习进度模型。"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, gen_id, utcnow


class EnglishScene(Base):
    __tablename__ = "english_scenes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ens"))
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(512), default="")
    level: Mapped[str] = mapped_column(String(32), default="A1 入门")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class EnglishUnit(Base):
    __tablename__ = "english_units"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("enu"))
    scene_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(128))
    level: Mapped[str] = mapped_column(String(32), default="A1 入门")
    duration_min: Mapped[int] = mapped_column(Integer, default=8)
    goal: Mapped[str] = mapped_column(String(512), default="")
    content_json: Mapped[str] = mapped_column(Text, default="{}")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class EnglishStudyRecord(Base):
    __tablename__ = "english_study_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("enr"))
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    unit_id: Mapped[str] = mapped_column(String(32), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    next_review_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    review_stage: Mapped[int] = mapped_column(Integer, default=0)


class EnglishUnitProgress(Base):
    """每位学习者每节课一条掌握/复习状态；历史尝试仍保留在 EnglishStudyRecord。"""
    __tablename__ = "english_unit_progress"
    __table_args__ = (UniqueConstraint("user_id", "unit_id", name="uq_english_progress_user_unit"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("enp"))
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    unit_id: Mapped[str] = mapped_column(String(32), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_studied_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    next_review_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=utcnow)
    review_stage: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_result: Mapped[str] = mapped_column(String(16), default="")


class EnglishStudyAttempt(Base):
    """幂等学习提交，网络重试不会重复生成练习历史或推进复习阶段。"""
    __tablename__ = "english_study_attempts"
    __table_args__ = (UniqueConstraint("user_id", "attempt_id", name="uq_english_attempt_user_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ena"))
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    unit_id: Mapped[str] = mapped_column(String(32), index=True)
    attempt_id: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(16), default="independent")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class EnglishASRJob(Base):
    """Server-side ASR job; generated captions stay in editable draft state."""
    __tablename__ = "english_asr_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    input_path: Mapped[str] = mapped_column(String(512), default="")
    filename: Mapped[str] = mapped_column(String(255), default="")
    transcript_json: Mapped[str] = mapped_column(Text, default="[]")
    error_message: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
