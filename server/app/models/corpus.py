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
class CorpusItem(Base):
    """语料本 · 跨来源词句素材（捕获 → 内化 → 运用）"""
    __tablename__ = "corpus_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("cps"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    original: Mapped[str] = mapped_column(Text, default="")  # 原文
    kind: Mapped[str] = mapped_column(String(16), default="句")  # 词|专名|成语|诗典|短语|句|结构
    source_type: Mapped[str] = mapped_column(String(16), default="其他")  # 报纸|视频|…
    source_title: Mapped[str] = mapped_column(String(256), default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")  # 场景标签
    plain_note: Mapped[str] = mapped_column(Text, default="")  # 白话解释
    rewrite: Mapped[str] = mapped_column(Text, default="")  # 我的改写
    practice: Mapped[str] = mapped_column(Text, default="")  # 仿写/造句
    status: Mapped[str] = mapped_column(String(16), default="inbox", index=True)  # inbox|clarified|owned|used
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    promoted_term_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 挂知识框架：专名/语料归入考点树，便于串联复习
    knowledge_node_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    knowledge_tree_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    knowledge_path: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


