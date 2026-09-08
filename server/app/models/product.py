"""多产品共享学习任务模型。"""

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
    utcnow,
)


class DailyLearningTask(Base):
    """按产品和日期编排的学习任务。"""

    __tablename__ = "daily_learning_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("dlt"))
    product_key: Mapped[str] = mapped_column(String(32), index=True)
    task_date: Mapped[str] = mapped_column(String(10), index=True)
    task_type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(512), default="")
    content_type: Mapped[str] = mapped_column(String(32), default="")
    content_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=15)
    total_steps: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class UserDailyTaskProgress(Base):
    """用户任务状态与草稿；服务端是跨端断点恢复的真值源。"""

    __tablename__ = "user_daily_task_progress"
    __table_args__ = (UniqueConstraint("user_id", "task_id", name="uq_user_daily_task"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("dtp"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("daily_learning_tasks.id"), index=True)
    product_key: Mapped[str] = mapped_column(String(32), index=True)
    state: Mapped[str] = mapped_column(String(16), default="not_started", index=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=1)
    draft_json: Mapped[str] = mapped_column(Text, default="{}")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class UserGuestLearningRecord(Base):
    """游客练习登录后的版本化快照；不等同积分、错题或个人开采记录。"""

    __tablename__ = "user_guest_learning_records"
    __table_args__ = (
        UniqueConstraint("user_id", "product_key", "record_key", name="uq_user_product_guest_record"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("glr"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    product_key: Mapped[str] = mapped_column(String(32), index=True)
    record_key: Mapped[str] = mapped_column(String(180), index=True)
    record_type: Mapped[str] = mapped_column(String(32), index=True)
    content_id: Mapped[str] = mapped_column(String(64), index=True)
    revision: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    source_device_id: Mapped[str] = mapped_column(String(64), default="")
    client_updated_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class TheoryLearningEntry(Base):
    """时政学习入口编排；不是试卷，只组织单篇文章的分辑练习。"""

    __tablename__ = "theory_learning_entries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("tle"))
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(String(512), default="")
    is_daily: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_evergreen: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    parts_json: Mapped[str] = mapped_column(Text, default="[]")
    collection_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    publish_start: Mapped[str] = mapped_column(String(10), default="", index=True)
    publish_end: Mapped[str] = mapped_column(String(10), default="", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
