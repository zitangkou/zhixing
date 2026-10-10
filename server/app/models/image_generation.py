"""Persistent status and diagnostic records for image generation jobs."""

from datetime import datetime

from app.models.base import Base, Boolean, DateTime, Mapped, String, Text, mapped_column, utcnow


class ImageGenerationJob(Base):
    __tablename__ = "image_generation_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    product_key: Mapped[str] = mapped_column(String(32), default="general")
    style_id: Mapped[str] = mapped_column(String(64))
    model_id: Mapped[str] = mapped_column(String(64), default="")
    provider: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    allow_draft: Mapped[bool] = mapped_column(Boolean, default=False)
    input_path: Mapped[str] = mapped_column(String(512), default="")
    result_id: Mapped[str] = mapped_column(String(32), default="")
    error_code: Mapped[str] = mapped_column(String(64), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
