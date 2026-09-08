"""统一题库 ORM 模型：逻辑题目、版本、试卷、题位、材料、导入批次。

设计依据：docs/architecture/question-bank-persistence-admin-design.md §4
"""
from datetime import datetime

from sqlalchemy import JSON, Index, Integer, String, Text

from app.models.base import (
    Base,
    Boolean,
    DateTime,
    ForeignKey,
    Mapped,
    UniqueConstraint,
    gen_id,
    mapped_column,
    relationship,
    utcnow,
)


class QuestionItem(Base):
    """逻辑题目实体（一道独立题目，不含试卷题号）。"""

    __tablename__ = "question_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("qi"))
    origin_type: Mapped[str] = mapped_column(String(16), default="real", index=True)  # real/generated/manual
    subject: Mapped[str] = mapped_column(String(32), default="行测", index=True)  # 行测/申论/公基
    module: Mapped[str] = mapped_column(String(32), default="", index=True)  # 政治理论/言语/数量/判断/资料
    subtype: Mapped[str] = mapped_column(String(32), default="")  # 选词填空/定义判断/增长率等
    response_type: Mapped[str] = mapped_column(String(16), default="single")  # single/multiple/judge/subjective
    current_version_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    canonical_hash: Mapped[str] = mapped_column(String(64), default="", index=True)  # 去重哈希
    difficulty: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    lifecycle_status: Mapped[str] = mapped_column(String(16), default="active")  # active/retired/disputed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    versions: Mapped[list["QuestionVersion"]] = relationship(
        "QuestionVersion", back_populates="question", cascade="all, delete-orphan"
    )
    positions: Mapped[list["PaperQuestionPosition"]] = relationship(
        "PaperQuestionPosition", back_populates="question"
    )
    material_links: Mapped[list["QuestionMaterialLink"]] = relationship(
        "QuestionMaterialLink", back_populates="question", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_qi_module_origin", "module", "origin_type"),
    )


class QuestionVersion(Base):
    """题目内容版本（题干/选项/答案/解析的不可变快照）。"""

    __tablename__ = "question_versions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("qv"))
    question_id: Mapped[str] = mapped_column(ForeignKey("question_items.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    stem: Mapped[str] = mapped_column(Text, default="")
    items_json: Mapped[list | None] = mapped_column(JSON, nullable=True)  # 组合条目
    options_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"A":"...","B":"..."}
    correct_answer_json: Mapped[object | None] = mapped_column(JSON, nullable=True)  # "B" or ["A","C"]
    explanation: Mapped[str] = mapped_column(Text, default="")
    analysis_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 题型专属结构
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    change_summary: Mapped[str] = mapped_column(String(256), default="")
    answer_source: Mapped[str] = mapped_column(String(128), default="")  # 答案来源
    media_json: Mapped[list | None] = mapped_column(JSON, nullable=True)  # 媒体引用
    formulas_json: Mapped[list | None] = mapped_column(JSON, nullable=True)  # 公式
    topic: Mapped[str] = mapped_column(String(64), default="")  # 考点
    tag: Mapped[str] = mapped_column(String(128), default="")  # 标签
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    question: Mapped["QuestionItem"] = relationship("QuestionItem", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("question_id", "version_no", name="uq_qv_question_version"),
        UniqueConstraint("question_id", "content_hash", name="uq_qv_question_content"),
    )


class ExamPaperUnified(Base):
    """试卷（统一题库版，与旧 exam_papers 并存）。"""

    __tablename__ = "qb_exam_papers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("qbp"))
    exam_year: Mapped[int] = mapped_column(Integer, default=0, index=True)
    exam_kind: Mapped[str] = mapped_column(String(32), default="国考")  # 国考/省考/事业单位
    paper_type: Mapped[str] = mapped_column(String(32), default="", index=True)  # 省级/市地级/行政执法类
    title: Mapped[str] = mapped_column(String(256), default="")
    source_document: Mapped[str] = mapped_column(String(512), default="")
    schema_version: Mapped[str] = mapped_column(String(16), default="")
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    import_batch_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    sections: Mapped[list["PaperSection"]] = relationship(
        "PaperSection", back_populates="paper", cascade="all, delete-orphan"
    )
    positions: Mapped[list["PaperQuestionPosition"]] = relationship(
        "PaperQuestionPosition", back_populates="paper", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("exam_year", "exam_kind", "paper_type", name="uq_qb_paper_year_kind_type"),
    )


class PaperSection(Base):
    """试卷模块（如政治理论、言语理解与表达）。"""

    __tablename__ = "qb_paper_sections"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("qbs"))
    paper_id: Mapped[str] = mapped_column(ForeignKey("qb_exam_papers.id"), index=True)
    name: Mapped[str] = mapped_column(String(64), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    number_start: Mapped[int] = mapped_column(Integer, default=0)
    number_end: Mapped[int] = mapped_column(Integer, default=0)
    question_count: Mapped[int] = mapped_column(Integer, default=0)

    paper: Mapped["ExamPaperUnified"] = relationship("ExamPaperUnified", back_populates="sections")
    positions: Mapped[list["PaperQuestionPosition"]] = relationship(
        "PaperQuestionPosition", back_populates="section"
    )

    __table_args__ = (
        UniqueConstraint("paper_id", "sort_order", name="uq_qb_section_paper_order"),
    )


class PaperQuestionPosition(Base):
    """试卷题位（题目在某份试卷中的位置，支持一题多卷共享）。"""

    __tablename__ = "qb_paper_question_positions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("qpos"))
    paper_id: Mapped[str] = mapped_column(ForeignKey("qb_exam_papers.id"), index=True)
    section_id: Mapped[str | None] = mapped_column(ForeignKey("qb_paper_sections.id"), nullable=True, index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("question_items.id"), index=True)
    number: Mapped[int] = mapped_column(Integer, default=0)  # 整卷题号
    section_index: Mapped[int] = mapped_column(Integer, default=0)  # 模块内序号
    sort_order: Mapped[int] = mapped_column(Integer, default=0)  # 展示顺序
    provenance_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # shared/diff_book等来源信息
    quality_flags_json: Mapped[list | None] = mapped_column(JSON, nullable=True)  # 数据质量标记
    source_key: Mapped[str] = mapped_column(String(128), default="", index=True)  # guokao:2025:省级:1
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    paper: Mapped["ExamPaperUnified"] = relationship("ExamPaperUnified", back_populates="positions")
    section: Mapped["PaperSection | None"] = relationship("PaperSection", back_populates="positions")
    question: Mapped["QuestionItem"] = relationship("QuestionItem", back_populates="positions")

    __table_args__ = (
        UniqueConstraint("paper_id", "number", name="uq_qb_pos_paper_number"),
        UniqueConstraint("paper_id", "section_id", "section_index", name="uq_qb_pos_paper_section_index"),
    )


class Material(Base):
    """材料（资料分析材料、逻辑题组材料等，独立于题目保存）。"""

    __tablename__ = "qb_materials"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("qbm"))
    source_key: Mapped[str] = mapped_column(String(128), default="", unique=True, index=True)  # guokao:2025:m106_110
    title: Mapped[str] = mapped_column(String(256), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    material_type: Mapped[str] = mapped_column(String(32), default="")  # text/table/chart/chart_table
    source_ref_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 原始来源引用
    table_data_json: Mapped[object | None] = mapped_column(JSON, nullable=True)  # 结构化表格数据
    media_json: Mapped[list | None] = mapped_column(JSON, nullable=True)  # 媒体引用
    note: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    question_links: Mapped[list["QuestionMaterialLink"]] = relationship(
        "QuestionMaterialLink", back_populates="material", cascade="all, delete-orphan"
    )


class QuestionMaterialLink(Base):
    """题目-材料关联（一篇材料可关联多题，一题可关联多材料）。"""

    __tablename__ = "qb_question_material_links"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("qbml"))
    question_id: Mapped[str] = mapped_column(ForeignKey("question_items.id"), index=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("qb_materials.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="primary")  # primary/supplementary
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    question: Mapped["QuestionItem"] = relationship("QuestionItem", back_populates="material_links")
    material: Mapped["Material"] = relationship("Material", back_populates="question_links")

    __table_args__ = (
        UniqueConstraint("question_id", "material_id", name="uq_qb_qml_question_material"),
    )


class ImportBatch(Base):
    """导入批次（记录每次导入的文件、统计和状态）。"""

    __tablename__ = "qb_import_batches"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("qib"))
    source_path: Mapped[str] = mapped_column(String(512), default="")
    source_hash: Mapped[str] = mapped_column(String(64), default="")
    schema_version: Mapped[str] = mapped_column(String(16), default="")
    parsed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    reused_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    warnings_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="completed")  # pending/completed/failed
    detail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 每卷统计明细
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
