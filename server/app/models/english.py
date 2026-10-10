"""言遇口语内容与学习进度模型。"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
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
