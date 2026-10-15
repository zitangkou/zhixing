"""人民日报申论素材库。正文仅保存筛选后的结构化内容及来源元数据。"""
from datetime import date, datetime
from sqlalchemy import Date
from app.models.base import Base, Mapped, mapped_column, String, Text, Integer, DateTime, Boolean, utcnow


class ShenlunMaterial(Base):
    __tablename__ = 'shenlun_materials'
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_date: Mapped[date] = mapped_column(Date, index=True)
    collected_date: Mapped[date] = mapped_column(Date, index=True)
    source_title: Mapped[str] = mapped_column(String(300), index=True)
    source_section: Mapped[str] = mapped_column(String(100), default='')
    source_url: Mapped[str] = mapped_column(String(1000), default='')
    item_type: Mapped[str] = mapped_column(String(32), index=True)
    theme_code: Mapped[str] = mapped_column(String(16), index=True)
    scene_code: Mapped[str] = mapped_column(String(32), index=True)
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    veto: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String(24), default='pending', index=True)
    text: Mapped[str] = mapped_column(Text, default='')
    payload_json: Mapped[str] = mapped_column(Text, default='{}')
    created_by: Mapped[str] = mapped_column(String(128), default='')
    updated_by: Mapped[str] = mapped_column(String(128), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
