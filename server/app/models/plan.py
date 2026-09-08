"""ORM 模型 · 域模块

按业务域拆分，统一由 app/models/__init__.py re-export，保持 from app.models import X 兼容。
"""
from datetime import datetime

from app.models.base import (
    Base,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Mapped,
    gen_id,
    mapped_column,
    relationship,
    utcnow,
)
class PlanTask(Base):
    """每日学习清单任务"""
    __tablename__ = "plan_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("pt"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    plan_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    time_slot: Mapped[str] = mapped_column(String(32), default="")  # 如 "06:45-07:45"
    subject: Mapped[str] = mapped_column(String(32), default="")  # 行测/申论/英语/健身/阅读
    content: Mapped[str] = mapped_column(String(256))
    priority: Mapped[int] = mapped_column(Integer, default=3)  # 1-5，重要级
    expected_minutes: Mapped[int] = mapped_column(Integer, default=0)
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | done | skipped
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class PlanTemplate(Base):
    """每日清单模板（后台维护，工作日/周末两套）"""
    __tablename__ = "plan_templates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("plt"))
    day_type: Mapped[str] = mapped_column(String(16), index=True)  # weekday | weekend
    time_slot: Mapped[str] = mapped_column(String(32), default="")
    subject: Mapped[str] = mapped_column(String(32), default="")
    content: Mapped[str] = mapped_column(String(256))
    priority: Mapped[int] = mapped_column(Integer, default=3)
    expected_minutes: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class DailyReview(Base):
    """每日复盘"""
    __tablename__ = "daily_reviews"
    __table_args__ = (UniqueConstraint("user_id", "review_date", name="uq_user_review_date"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("dr"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    review_date: Mapped[str] = mapped_column(String(10))
    completion: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    total_minutes: Mapped[int] = mapped_column(Integer, default=0)
    weak_point: Mapped[str] = mapped_column(Text, default="")
    tomorrow_focus: Mapped[str] = mapped_column(Text, default="")
    mood: Mapped[str] = mapped_column(String(16), default="")  # good/ok/bad
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


