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
class EventImpression(Base):
    """时事新闻 · 事件印象（挂知识框架，加深考点联系）"""
    __tablename__ = "event_impressions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ei"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    event_date: Mapped[str] = mapped_column(String(10), default="", index=True)  # YYYY-MM-DD
    place: Mapped[str] = mapped_column(String(128), default="")
    core_content: Mapped[str] = mapped_column(Text, default="")  # 核心印象/要点
    note: Mapped[str] = mapped_column(Text, default="")  # 补充联想（可选）
    # 挂知识框架：如 常识判断 / 航天常识/神舟系列
    knowledge_node_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    knowledge_tree_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    knowledge_path: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


