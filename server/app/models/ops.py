"""内容生产：流程、步骤、运行记录。"""
from datetime import datetime

from app.models.base import Base, Boolean, DateTime, ForeignKey, Integer, Mapped, String, Text, UniqueConstraint, gen_id, mapped_column, utcnow


class OpsStep(Base):
    __tablename__ = "ops_steps"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ost"))
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    product: Mapped[str] = mapped_column(String(32), index=True)
    step_type: Mapped[str] = mapped_column(String(32), default="script")
    command: Mapped[str] = mapped_column(Text, default="")
    cwd_rel: Mapped[str] = mapped_column(String(128), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_hint: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class OpsPipeline(Base):
    __tablename__ = "ops_pipelines"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("opl"))
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    product: Mapped[str] = mapped_column(String(32), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cron: Mapped[str] = mapped_column(String(64), default="")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class OpsPipelineStep(Base):
    __tablename__ = "ops_pipeline_steps"
    __table_args__ = (UniqueConstraint("pipeline_id", "step_id", name="uq_ops_pipeline_step"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ops"))
    pipeline_id: Mapped[str] = mapped_column(ForeignKey("ops_pipelines.id"), index=True)
    step_id: Mapped[str] = mapped_column(ForeignKey("ops_steps.id"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class OpsRun(Base):
    __tablename__ = "ops_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("orn"))
    pipeline_id: Mapped[str] = mapped_column(ForeignKey("ops_pipelines.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    log: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OpsRunStep(Base):
    __tablename__ = "ops_run_steps"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ors"))
    run_id: Mapped[str] = mapped_column(ForeignKey("ops_runs.id"), index=True)
    step_id: Mapped[str] = mapped_column(String(32), default="")
    step_name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
