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
class KnowledgeNode(Base):
    """知识框架节点（由 Obsidian md 解析而来）"""
    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("kn"))
    tree_key: Mapped[str] = mapped_column(String(32), index=True)  # 如 "申论"、"判断推理"
    parent_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("knowledge_nodes.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[str] = mapped_column(Text, default="")
    my_note: Mapped[str] = mapped_column(Text, default="")  # 用户在App/后台加的备注，同步时按 path 保留
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)  # 标记重点
    # App 侧掌握度（Obsidian 同步时按 path 保留，不覆盖）
    mastery_level: Mapped[str] = mapped_column(String(16), default="new")  # new|learning|familiar|mastered
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    path: Mapped[str] = mapped_column(Text, default="")  # 父链路 "申论/题型/归纳概括题"
    source_file: Mapped[str] = mapped_column(String(128), default="")
    source_line: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


