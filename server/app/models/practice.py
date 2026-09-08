"""ORM 模型 · 域模块

按业务域拆分，统一由 app/models/__init__.py re-export，保持 from app.models import X 兼容。
"""
from datetime import datetime

from app.models.account import AppUser
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
class PointsLog(Base):
    __tablename__ = "points_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("log"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    log_type: Mapped[str] = mapped_column(String(16))  # income | expense
    source: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[AppUser] = relationship(back_populates="points_logs")


class SignRecord(Base):
    __tablename__ = "sign_records"
    __table_args__ = (UniqueConstraint("user_id", "sign_date", name="uq_user_sign_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    sign_date: Mapped[str] = mapped_column(String(10))
    points: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[AppUser] = relationship(back_populates="sign_records")


class WrongAnswer(Base):
    __tablename__ = "wrong_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), index=True)
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    user_answer: Mapped[str] = mapped_column(Text, default="")
    # 艾宾浩斯调度：答对推进间隔，答错重置；跑完全部间隔后移除
    review_stage: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class StudyRecord(Base):
    __tablename__ = "study_records"
    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_user_article_study"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), index=True)
    study_date: Mapped[str] = mapped_column(String(10))
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_review_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class SectionRead(Base):
    __tablename__ = "section_reads"
    __table_args__ = (UniqueConstraint("user_id", "article_id", "section_id", name="uq_user_section_read"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"), index=True)
    section_id: Mapped[str] = mapped_column(String(64))
    read_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("qa"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    article_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("articles.id"), nullable=True, index=True)
    quiz_mode: Mapped[str] = mapped_column(String(16), default="article")
    total_count: Mapped[int] = mapped_column(Integer)
    correct_count: Mapped[int] = mapped_column(Integer)
    accuracy: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ManualWrong(Base):
    """手动录入的错题（行测刷题，区别于App自动生成的 WrongAnswer）"""
    __tablename__ = "manual_wrongs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("mw"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(32), default="")  # 常识/言语/数量/判断/资料/申论
    question_type: Mapped[str] = mapped_column(String(64), default="")
    stem: Mapped[str] = mapped_column(Text, default="")
    options: Mapped[str] = mapped_column(Text, default="")  # 文本
    my_answer: Mapped[str] = mapped_column(Text, default="")
    correct_answer: Mapped[str] = mapped_column(Text, default="")
    analysis: Mapped[str] = mapped_column(Text, default="")
    wrong_reason: Mapped[str] = mapped_column(String(64), default="")  # 粗心/方法不会/知识点盲/时间不够
    note: Mapped[str] = mapped_column(Text, default="")
    images: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of URL
    source: Mapped[str] = mapped_column(String(32), default="manual")  # manual | photo | ocr
    # 关联知识框架（可选；path + tree_key 在节点重同步后可重绑 id）
    knowledge_node_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    knowledge_tree_key: Mapped[str] = mapped_column(String(32), default="")
    knowledge_path: Mapped[str] = mapped_column(Text, default="")  # 节点 path，如 选词填空/词语辨析
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    review_stage: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# ===== 真题/题库模块 =====


class PracticeAnswer(Base):
    """练习作答记录（Q7 学习闭环持久化，P3 学习反馈数据源）。

    user_id 可匿名（设备级/演示用户），不存储个人身份信息。
    source 标记数据来源：real（真实用户）/ demo（演示数据）。
    """
    __tablename__ = "practice_answers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("pa"))
    user_id: Mapped[str] = mapped_column(String(64), default="anonymous", index=True)
    question_id: Mapped[str] = mapped_column(String(64), index=True)
    daily_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    user_answer: Mapped[str] = mapped_column(String(8), default="")
    correct_answer: Mapped[str] = mapped_column(String(8), default="")
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    time_spent_ms: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), default="real", index=True)  # real | demo
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

