"""统一题库 Pydantic schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QuestionItemOut(BaseModel):
    id: str
    origin_type: str
    subject: str
    module: str
    subtype: str
    response_type: str
    current_version_id: str | None = None
    canonical_hash: str
    difficulty: int
    lifecycle_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionVersionOut(BaseModel):
    id: str
    question_id: str
    version_no: int
    stem: str
    items_json: list | None = None
    options_json: dict | None = None
    correct_answer_json: Any = None
    explanation: str
    analysis_payload_json: dict | None = None
    content_hash: str
    change_summary: str
    answer_source: str
    media_json: list | None = None
    formulas_json: list | None = None
    topic: str
    tag: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ExamPaperUnifiedOut(BaseModel):
    id: str
    exam_year: int
    exam_kind: str
    paper_type: str
    title: str
    source_document: str
    schema_version: str
    total_questions: int
    import_batch_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperSectionOut(BaseModel):
    id: str
    paper_id: str
    name: str
    sort_order: int
    number_start: int
    number_end: int
    question_count: int

    model_config = {"from_attributes": True}


class PaperQuestionPositionOut(BaseModel):
    id: str
    paper_id: str
    section_id: str | None = None
    question_id: str
    number: int
    section_index: int
    sort_order: int
    provenance_json: dict | None = None
    quality_flags_json: list | None = None
    source_key: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MaterialOut(BaseModel):
    id: str
    source_key: str
    title: str
    content: str
    material_type: str
    source_ref_json: dict | None = None
    table_data_json: Any = None
    media_json: list | None = None
    note: str
    content_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionMaterialLinkOut(BaseModel):
    id: str
    question_id: str
    material_id: str
    role: str
    sort_order: int

    model_config = {"from_attributes": True}


class ImportBatchOut(BaseModel):
    id: str
    source_path: str
    source_hash: str
    schema_version: str
    parsed_at: datetime
    new_count: int
    updated_count: int
    reused_count: int
    skipped_count: int
    error_count: int
    warnings_json: list | None = None
    status: str
    detail_json: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReconciliationReport(BaseModel):
    """对账报告。"""

    total_positions: int = 0
    by_paper: dict[str, int] = Field(default_factory=dict)
    shared_political_theory_entities: int = 0
    answer_coverage: float = 0.0
    answer_total: int = 0
    answer_with_answer: int = 0
    number_continuity_ok: dict[str, bool] = Field(default_factory=dict)
    materials_linked: int = 0
    questions_with_materials: int = 0
    flags_preserved: int = 0
    provenance_preserved: int = 0
    idempotent_rerun_new: int = 0
    idempotent_rerun_updated: int = 0
    total_question_entities: int = 0
