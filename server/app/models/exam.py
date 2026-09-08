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
class ExamPaper(Base):
    """试卷（真题 / 自定义 / 模拟卷）"""
    __tablename__ = "exam_papers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("paper"))
    title: Mapped[str] = mapped_column(String(128))
    exam_type: Mapped[str] = mapped_column(String(16), default="real")  # real | custom | mock
    subject: Mapped[str] = mapped_column(String(32), default="行测")  # 行测 / 申论 / 公基
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    region: Mapped[str] = mapped_column(String(64), default="")  # 国考 / 江苏 / 山东
    level: Mapped[str] = mapped_column(String(32), default="")  # 省级 / 地市级
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    time_limit_min: Mapped[int] = mapped_column(Integer, default=120)
    source_url: Mapped[str] = mapped_column(String(512), default="")
    tags: Mapped[str] = mapped_column(String(256), default="[]")  # JSON
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ExamQuestion(Base):
    """试卷题目（独立于 Question，避免污染原模型）"""
    __tablename__ = "exam_questions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("eq"))
    paper_id: Mapped[str] = mapped_column(ForeignKey("exam_papers.id"), index=True)
    section: Mapped[str] = mapped_column(String(32), default="")  # 常识判断 / 言语理解 / 数量关系 / 判断推理 / 资料分析
    section_index: Mapped[int] = mapped_column(Integer, default=0)  # 在该模块内的序号 1-20
    sort_order: Mapped[int] = mapped_column(Integer, default=0)  # 整卷顺序 1-135
    type: Mapped[str] = mapped_column(String(16), default="single")  # single | multiple | judge
    material: Mapped[str] = mapped_column(Text, default="")  # 共享材料（资料分析/逻辑题）
    stem: Mapped[str] = mapped_column(Text)
    options: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    correct_answer: Mapped[str] = mapped_column(Text)  # JSON string or plain
    analysis: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    knowledge_tags: Mapped[str] = mapped_column(String(256), default="[]")  # JSON 旧标签，过渡用
    knowledge_node_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    knowledge_tree_key: Mapped[str] = mapped_column(String(32), default="")
    knowledge_path: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ExamAttempt(Base):
    """整卷作答记录"""
    __tablename__ = "exam_attempts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ea"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("exam_papers.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    time_used_sec: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)
    is_finished: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ExamAnswer(Base):
    """每题作答明细"""
    __tablename__ = "exam_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("exam_attempts.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("exam_questions.id"), index=True)
    user_answer: Mapped[str] = mapped_column(Text, default="")  # JSON
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    time_used_sec: Mapped[int] = mapped_column(Integer, default=0)
    marked: Mapped[bool] = mapped_column(Boolean, default=False)  # 考生标记存疑
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


