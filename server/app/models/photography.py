"""摄影学习课程与知识地图。"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, gen_id, utcnow


class PhotographyStage(Base):
    __tablename__ = "photography_stages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("phs"))
    title: Mapped[str] = mapped_column(String(128))
    items: Mapped[str] = mapped_column(String(512), default="")
    description: Mapped[str] = mapped_column(String(512), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class PhotographyLesson(Base):
    __tablename__ = "photography_lessons"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("phl"))
    stage_id: Mapped[str] = mapped_column(ForeignKey("photography_stages.id", ondelete="RESTRICT"), index=True)
    category: Mapped[str] = mapped_column(String(64), default="光线")
    title: Mapped[str] = mapped_column(String(160))
    subtitle: Mapped[str] = mapped_column(String(256), default="")
    level: Mapped[str] = mapped_column(String(32), default="入门")
    duration_min: Mapped[int] = mapped_column(Integer, default=10)
    principle: Mapped[str] = mapped_column(Text, default="")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    task: Mapped[str] = mapped_column(Text, default="")
    review: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class PhotographyCase(Base):
    """Curated photo case with reviewed analysis and a single practice goal."""
    __tablename__ = "photography_cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("phc"))
    title: Mapped[str] = mapped_column(String(160))
    image_url: Mapped[str] = mapped_column(String(1024), default="")
    source_url: Mapped[str] = mapped_column(String(1024), default="")
    author: Mapped[str] = mapped_column(String(160), default="")
    license_type: Mapped[str] = mapped_column(String(32), default="")
    license_note: Mapped[str] = mapped_column(String(512), default="")
    category: Mapped[str] = mapped_column(String(64), default="光线")
    level: Mapped[str] = mapped_column(String(32), default="入门")
    observation_json: Mapped[str] = mapped_column(Text, default="[]")
    exif_json: Mapped[str] = mapped_column(Text, default="{}")
    inference_json: Mapped[str] = mapped_column(Text, default="[]")
    practice_title: Mapped[str] = mapped_column(String(160), default="")
    practice_goal: Mapped[str] = mapped_column(Text, default="")
    practice_steps_json: Mapped[str] = mapped_column(Text, default="[]")
    practice_variable: Mapped[str] = mapped_column(String(256), default="")
    criteria_json: Mapped[str] = mapped_column(Text, default="[]")
    duration_min: Mapped[int] = mapped_column(Integer, default=15)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
