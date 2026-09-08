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
class ExamCountdown(Base):
    """考试倒计时 · 每个用户一条目标考试记录（upsert）"""

    __tablename__ = "exam_countdowns"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ecd"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    exam_name: Mapped[str] = mapped_column(String(128), default="")
    exam_date: Mapped[str] = mapped_column(String(10), default="")  # YYYY-MM-DD
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ActivityEvent(Base):
    """用户行为事件 · M4 成长/能力雷达/里程碑统计的数据底座（本期仅写入）"""

    __tablename__ = "activity_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("aev"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    event_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Feedback(Base):
    """学员反馈 · 纠错与建议，供管理端查看与处理（反馈采纳后人工加分）"""

    __tablename__ = "feedbacks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("fb"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    product_key: Mapped[str] = mapped_column(String(32), default="", index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)  # new|adopted|rejected
    note: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
