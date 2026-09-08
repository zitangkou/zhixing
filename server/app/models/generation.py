"""生成工作台 ORM 模型：生成批次、审核记录。

设计依据：docs/architecture/question-bank-persistence-admin-design.md §4.11
生成题源数据为只读 JSON（xingce-structured-data/generated/），
本表用于追踪批次元信息与教研审核结论，不修改原始产出。
"""
from datetime import datetime

from sqlalchemy import JSON, Index, Integer, String, Text

from app.models.base import (
    Base,
    DateTime,
    ForeignKey,
    Mapped,
    mapped_column,
    relationship,
    utcnow,
)


class GenerationBatch(Base):
    """生成批次：每次引擎运行产出的一批题目的元信息与校验摘要。"""

    __tablename__ = "generation_batches"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    engine_type: Mapped[str] = mapped_column(String(32), index=True)  # qa_data_analysis / qa_quantity
    template_version: Mapped[str] = mapped_column(String(64), default="")
    skill: Mapped[str] = mapped_column(String(64), default="")  # 基期量/工程问题等
    source_file: Mapped[str] = mapped_column(String(512), default="")  # 只读 JSON 路径
    param_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="completed")  # pending/running/completed/failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    review_records: Mapped[list["ReviewRecord"]] = relationship(
        "ReviewRecord", back_populates="batch", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_gb_engine_status", "engine_type", "status"),
    )


class ReviewRecord(Base):
    """教研审核记录：针对单道生成题的审核结论。

    question_id 存生成 JSON 中的原始题号（如 Q2-DA-BASE-001），
    若该题已导入 question_items，则同步更新其 lifecycle_status。
    """

    __tablename__ = "review_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    batch_id: Mapped[str | None] = mapped_column(ForeignKey("generation_batches.id"), nullable=True, index=True)
    question_id: Mapped[str] = mapped_column(String(64), index=True)  # 生成 JSON 原始题号
    question_item_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)  # 关联 question_items.id（如有）
    action: Mapped[str] = mapped_column(String(16), default="pending")  # pending/approve/reject
    comment: Mapped[str] = mapped_column(Text, default="")
    reviewer: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    batch: Mapped["GenerationBatch | None"] = relationship("GenerationBatch", back_populates="review_records")

    __table_args__ = (
        Index("ix_rr_question_action", "question_id", "action"),
    )
