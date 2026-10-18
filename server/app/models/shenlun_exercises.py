"""申论每日自动出题批次。"""
from datetime import date, datetime
from sqlalchemy import Date
from app.models.base import Base, Mapped, mapped_column, String, Text, Integer, DateTime, utcnow, gen_id


class ShenlunExerciseJob(Base):
    __tablename__ = "shenlun_exercise_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("sej"))
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    trigger_mode: Mapped[str] = mapped_column(String(24), default="manual")
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    progress_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
