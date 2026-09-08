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
class ZiliaoFormula(Base):
    """资料分析 · 公式库"""
    __tablename__ = "ziliao_formulas"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("zf"))
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # F001
    name: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32), default="")  # 增长/比重/倍数/...
    definition: Mapped[str] = mapped_column(Text, default="")
    latex: Mapped[str] = mapped_column(Text, default="")  # KaTeX / LaTeX 源码
    formula_plain: Mapped[str] = mapped_column(Text, default="")  # 中文可读式，兜底展示
    scenarios: Mapped[str] = mapped_column(Text, default="")  # 适用场景
    pitfalls: Mapped[str] = mapped_column(Text, default="")  # 易错点
    related_type_codes: Mapped[str] = mapped_column(Text, default="[]")  # JSON [type codes]
    related_trick_codes: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    keywords: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    exam_freq: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ZiliaoQuestionType(Base):
    """资料分析 · 题型模型"""
    __tablename__ = "ziliao_question_types"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("zt"))
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # T001
    name: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    ability: Mapped[str] = mapped_column(Text, default="")  # 考查能力
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    exam_freq: Mapped[int] = mapped_column(Integer, default=3)
    formula_codes: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    trick_codes: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    keywords: Mapped[str] = mapped_column(Text, default="[]")  # 用于材料组弱匹配
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ZiliaoTrick(Base):
    """资料分析 · 速算技巧"""
    __tablename__ = "ziliao_tricks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("zk"))
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # K001
    name: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32), default="")
    principle: Mapped[str] = mapped_column(Text, default="")
    when_to_use: Mapped[str] = mapped_column(Text, default="")
    when_not: Mapped[str] = mapped_column(Text, default="")
    error_note: Mapped[str] = mapped_column(Text, default="")
    formula_codes: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    example: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ZiliaoPracticeLog(Base):
    """资料分析 · 材料组练习记录"""
    __tablename__ = "ziliao_practice_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("zpl"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    set_id: Mapped[str] = mapped_column(String(64), index=True)
    paper_id: Mapped[str] = mapped_column(String(32), default="")
    type_code: Mapped[str] = mapped_column(String(32), default="")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    time_used_sec: Mapped[int] = mapped_column(Integer, default=0)
    practice_date: Mapped[str] = mapped_column(String(10), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


