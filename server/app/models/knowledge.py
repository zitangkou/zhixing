"""ORM 模型 · 知识框架

knowledge_nodes：发布后派生的节点索引（按 path upsert，稳定 id）。
knowledge_trees / knowledge_tree_versions：树文档草稿与版本。
user_knowledge_state：学员个人备注/星标/掌握度（与节点解耦）。
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
    utcnow,
)


class KnowledgeNode(Base):
    """知识框架节点（由 md 发布派生）"""

    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("kn"))
    tree_key: Mapped[str] = mapped_column(String(32), index=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("knowledge_nodes.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[str] = mapped_column(Text, default="")
    # 旧用户字段：已废弃，只保留列兼容老库；新代码不读不写，按产品决定旧数据丢弃、不迁移
    my_note: Mapped[str] = mapped_column(Text, default="")
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    mastery_level: Mapped[str] = mapped_column(String(16), default="new")
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    path: Mapped[str] = mapped_column(Text, default="")
    source_file: Mapped[str] = mapped_column(String(128), default="")
    source_line: Mapped[int] = mapped_column(Integer, default=0)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class KnowledgeTree(Base):
    """知识树文档元数据 + 草稿"""

    __tablename__ = "knowledge_trees"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("kt"))
    tree_key: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    md_draft: Mapped[str] = mapped_column(Text, default="")
    draft_revision: Mapped[int] = mapped_column(Integer, default=0)
    draft_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    draft_updated_by: Mapped[str] = mapped_column(String(32), default="")
    latest_version: Mapped[int] = mapped_column(Integer, default=0)
    live_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class KnowledgeTreeVersion(Base):
    """知识树已发布版本快照 + 导图资源 manifest"""

    __tablename__ = "knowledge_tree_versions"
    __table_args__ = (UniqueConstraint("tree_id", "version", name="uq_knowledge_tree_version"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("kv"))
    tree_id: Mapped[str] = mapped_column(String(32), ForeignKey("knowledge_trees.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    md_content: Mapped[str] = mapped_column(Text)
    md_sha256: Mapped[str] = mapped_column(String(64), default="")
    tree_json: Mapped[str] = mapped_column(Text, default="")
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    leaf_count: Mapped[int] = mapped_column(Integer, default=0)
    max_depth: Mapped[int] = mapped_column(Integer, default=0)
    manifest_json: Mapped[str] = mapped_column(Text, default="")
    assets_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(256), default="")
    created_by: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserKnowledgeState(Base):
    """学员个人知识点状态（备注/星标/掌握度）"""

    __tablename__ = "user_knowledge_state"
    __table_args__ = (UniqueConstraint("user_id", "node_id", name="uq_user_knowledge_state"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ks"))
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    node_id: Mapped[str] = mapped_column(String(32), index=True)
    tree_key: Mapped[str] = mapped_column(String(32), default="")
    path: Mapped[str] = mapped_column(Text, default="")
    my_note: Mapped[str] = mapped_column(Text, default="")
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    mastery_level: Mapped[str] = mapped_column(String(16), default="new")
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
