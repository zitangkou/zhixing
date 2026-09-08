"""统一题库管理 API：题目资产列表/详情、真题试卷列表/详情/题位/对账、发布门禁。

设计依据：docs/architecture/question-bank-persistence-admin-design.md §7.1-7.4, §10 P1
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.admin._deps import (
    ApiResponse,
    get_db,
    require_permission,
)
from app.models.question_bank import (
    ExamPaperUnified,
    ImportBatch,
    Material,
    PaperQuestionPosition,
    PaperSection,
    QuestionItem,
    QuestionMaterialLink,
    QuestionVersion,
)

router = APIRouter(prefix="/question-bank", tags=["统一题库"])

# ── 高风险质量 flag 集合（命中则禁止发布） ──────────────
HIGH_RISK_FLAGS = {
    "content_mismatch",
    "answer_conflict",
    "answer_mismatch",
    "missing_answer",
    "stem_incomplete",
    "options_incomplete",
    "ocr_error",
    "duplicate_question",
}


# ═══════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════

def _current_version(db: Session, question_id: str) -> QuestionVersion | None:
    """获取题目的当前版本（优先 current_version_id，否则最新 version_no）。"""
    item = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not item:
        return None
    if item.current_version_id:
        v = db.query(QuestionVersion).filter(QuestionVersion.id == item.current_version_id).first()
        if v:
            return v
    return (
        db.query(QuestionVersion)
        .filter(QuestionVersion.question_id == question_id)
        .order_by(QuestionVersion.version_no.desc())
        .first()
    )


def _question_has_high_risk_flag(db: Session, question_id: str) -> tuple[bool, list[str]]:
    """检查题目关联的所有题位是否有高风险 flag。"""
    positions = (
        db.query(PaperQuestionPosition)
        .filter(PaperQuestionPosition.question_id == question_id)
        .all()
    )
    flagged: list[str] = []
    for pos in positions:
        flags = pos.quality_flags_json or []
        for f in flags:
            flag_name = f if isinstance(f, str) else f.get("flag", "")
            if flag_name in HIGH_RISK_FLAGS:
                flagged.append(flag_name)
    return (len(flagged) > 0, flagged)


def _question_summary(item: QuestionItem, version: QuestionVersion | None, paper_count: int) -> dict:
    """构造题目列表项摘要。"""
    stem = version.stem if version else ""
    answer = version.correct_answer_json if version else None
    has_answer = bool(answer)
    # 答案展示：单选/判断取字符串，多选取数组拼接
    if isinstance(answer, list):
        answer_display = "".join(str(a) for a in answer)
    elif answer is not None:
        answer_display = str(answer)
    else:
        answer_display = ""
    return {
        "id": item.id,
        "origin_type": item.origin_type,
        "subject": item.subject,
        "module": item.module,
        "subtype": item.subtype,
        "response_type": item.response_type,
        "stem_summary": stem[:40] + ("…" if len(stem) > 40 else ""),
        "answer": answer_display,
        "has_answer": has_answer,
        "difficulty": item.difficulty,
        "lifecycle_status": item.lifecycle_status,
        "paper_count": paper_count,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


# ═══════════════════════════════════════════════════════
#  1. 题目资产列表
# ═══════════════════════════════════════════════════════

@router.get("/questions")
def admin_qb_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    origin_type: str | None = None,
    module: str | None = None,
    subtype: str | None = None,
    exam_year: int | None = None,
    paper_type: str | None = None,
    has_answer: bool | None = None,
    review_status: str | None = None,
    quality_flag: str | None = None,
    _admin=Depends(require_permission("exam:read")),
    db: Session = Depends(get_db),
):
    """分页题目资产列表，支持多维度筛选。"""
    query = db.query(QuestionItem)

    # 基础筛选
    if origin_type:
        query = query.filter(QuestionItem.origin_type == origin_type)
    if module:
        query = query.filter(QuestionItem.module == module)
    if subtype:
        query = query.filter(QuestionItem.subtype == subtype)

    # review_status 映射到 lifecycle_status
    if review_status:
        if review_status == "pending":
            query = query.filter(QuestionItem.lifecycle_status.in_(["pending_review", "disputed"]))
        elif review_status == "approved":
            query = query.filter(QuestionItem.lifecycle_status == "approved")
        elif review_status == "active":
            query = query.filter(QuestionItem.lifecycle_status == "active")
        elif review_status == "retired":
            query = query.filter(QuestionItem.lifecycle_status == "retired")

    # 年份/卷种筛选：通过题位关联试卷
    if exam_year is not None or paper_type:
        sub = (
            db.query(PaperQuestionPosition.question_id)
            .join(ExamPaperUnified, PaperQuestionPosition.paper_id == ExamPaperUnified.id)
        )
        if exam_year is not None:
            sub = sub.filter(ExamPaperUnified.exam_year == exam_year)
        if paper_type:
            sub = sub.filter(ExamPaperUnified.paper_type == paper_type)
        query = query.filter(QuestionItem.id.in_(sub))

    # quality_flag 筛选：通过题位的 quality_flags_json
    if quality_flag:
        flagged_qids = (
            db.query(PaperQuestionPosition.question_id)
            .filter(PaperQuestionPosition.quality_flags_json.isnot(None))
            .all()
        )
        matched_ids = set()
        for (qid,) in flagged_qids:
            pos = db.query(PaperQuestionPosition).filter(
                PaperQuestionPosition.question_id == qid
            ).first()
            flags = pos.quality_flags_json if pos else []
            for f in flags or []:
                flag_name = f if isinstance(f, str) else f.get("flag", "")
                if flag_name == quality_flag:
                    matched_ids.add(qid)
                    break
        query = query.filter(QuestionItem.id.in_(list(matched_ids) if matched_ids else ["__none__"]))

    total = query.count()

    # has_answer 筛选：需要关联版本
    items = query.order_by(QuestionItem.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result_items = []
    for item in items:
        version = _current_version(db, item.id)
        # has_answer 过滤
        if has_answer is not None:
            item_has_answer = bool(version and version.correct_answer_json)
            if item_has_answer != has_answer:
                continue
        paper_count = (
            db.query(func.count(func.distinct(PaperQuestionPosition.paper_id)))
            .filter(PaperQuestionPosition.question_id == item.id)
            .scalar()
            or 0
        )
        result_items.append(_question_summary(item, version, paper_count))

    return ApiResponse.ok({
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/questions/{question_id}")
def admin_qb_question_detail(
    question_id: str,
    _admin=Depends(require_permission("exam:read")),
    db: Session = Depends(get_db),
):
    """题目详情：当前版本完整内容 + 版本列表 + 关联题位 + 材料 + quality flags + provenance。"""
    item = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not item:
        return ApiResponse.fail("题目不存在", code=404)

    version = _current_version(db, question_id)

    # 版本列表
    versions = (
        db.query(QuestionVersion)
        .filter(QuestionVersion.question_id == question_id)
        .order_by(QuestionVersion.version_no.desc())
        .all()
    )
    version_list = [
        {
            "id": v.id,
            "version_no": v.version_no,
            "stem_summary": v.stem[:40] + ("…" if len(v.stem) > 40 else ""),
            "content_hash": v.content_hash,
            "change_summary": v.change_summary,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]

    # 关联题位（试卷+题号+模块）
    positions = (
        db.query(PaperQuestionPosition)
        .filter(PaperQuestionPosition.question_id == question_id)
        .order_by(PaperQuestionPosition.number)
        .all()
    )
    position_list = []
    all_flags: list[str] = []
    for pos in positions:
        paper = db.query(ExamPaperUnified).filter(ExamPaperUnified.id == pos.paper_id).first()
        section = db.query(PaperSection).filter(PaperSection.id == pos.section_id).first() if pos.section_id else None
        flags = pos.quality_flags_json or []
        for f in flags:
            flag_name = f if isinstance(f, str) else f.get("flag", "")
            if flag_name and flag_name not in all_flags:
                all_flags.append(flag_name)
        position_list.append({
            "position_id": pos.id,
            "paper_id": pos.paper_id,
            "paper_title": paper.title if paper else "",
            "exam_year": paper.exam_year if paper else None,
            "paper_type": paper.paper_type if paper else "",
            "section_name": section.name if section else "",
            "number": pos.number,
            "section_index": pos.section_index,
            "source_key": pos.source_key,
            "provenance": pos.provenance_json,
            "quality_flags": flags,
        })

    # 材料关联
    material_links = (
        db.query(QuestionMaterialLink)
        .filter(QuestionMaterialLink.question_id == question_id)
        .all()
    )
    materials = []
    for ml in material_links:
        mat = db.query(Material).filter(Material.id == ml.material_id).first()
        if mat:
            materials.append({
                "id": mat.id,
                "title": mat.title,
                "material_type": mat.material_type,
                "content_summary": mat.content[:80] + ("…" if len(mat.content) > 80 else ""),
                "role": ml.role,
                "sort_order": ml.sort_order,
            })

    # 高风险检测
    has_high_risk, high_risk_flags = _question_has_high_risk_flag(db, question_id)

    return ApiResponse.ok({
        "id": item.id,
        "origin_type": item.origin_type,
        "subject": item.subject,
        "module": item.module,
        "subtype": item.subtype,
        "response_type": item.response_type,
        "difficulty": item.difficulty,
        "lifecycle_status": item.lifecycle_status,
        "canonical_hash": item.canonical_hash,
        "current_version_id": item.current_version_id,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        # 当前版本完整内容
        "current_version": {
            "id": version.id if version else None,
            "version_no": version.version_no if version else None,
            "stem": version.stem if version else "",
            "items": version.items_json if version else None,
            "options": version.options_json if version else None,
            "correct_answer": version.correct_answer_json if version else None,
            "explanation": version.explanation if version else "",
            "analysis_payload": version.analysis_payload_json if version else None,
            "answer_source": version.answer_source if version else "",
            "media": version.media_json if version else None,
            "formulas": version.formulas_json if version else None,
            "topic": version.topic if version else "",
            "tag": version.tag if version else "",
            "content_hash": version.content_hash if version else "",
            "change_summary": version.change_summary if version else "",
        } if version else None,
        "versions": version_list,
        "positions": position_list,
        "materials": materials,
        "quality_flags": all_flags,
        "has_high_risk_flag": has_high_risk,
        "high_risk_flags": high_risk_flags,
        "paper_count": len(set(p.paper_id for p in positions)),
    })


# ═══════════════════════════════════════════════════════
#  2. 真题试卷
# ═══════════════════════════════════════════════════════

@router.get("/papers")
def admin_qb_papers(
    exam_year: int | None = None,
    paper_type: str | None = None,
    _admin=Depends(require_permission("exam:read")),
    db: Session = Depends(get_db),
):
    """试卷列表（年份/卷种/题量/答案覆盖率/导入状态）。"""
    query = db.query(ExamPaperUnified)
    if exam_year is not None:
        query = query.filter(ExamPaperUnified.exam_year == exam_year)
    if paper_type:
        query = query.filter(ExamPaperUnified.paper_type == paper_type)

    papers = query.order_by(ExamPaperUnified.exam_year.desc(), ExamPaperUnified.paper_type).all()

    result = []
    for paper in papers:
        positions = (
            db.query(PaperQuestionPosition)
            .filter(PaperQuestionPosition.paper_id == paper.id)
            .all()
        )
        total_pos = len(positions)
        with_answer = 0
        for pos in positions:
            v = _current_version(db, pos.question_id)
            if v and v.correct_answer_json:
                with_answer += 1
        answer_coverage = round(with_answer / total_pos * 100, 1) if total_pos > 0 else 0

        batch = None
        if paper.import_batch_id:
            batch = db.query(ImportBatch).filter(ImportBatch.id == paper.import_batch_id).first()

        result.append({
            "id": paper.id,
            "exam_year": paper.exam_year,
            "exam_kind": paper.exam_kind,
            "paper_type": paper.paper_type,
            "title": paper.title,
            "total_questions": paper.total_questions,
            "position_count": total_pos,
            "answer_coverage": answer_coverage,
            "import_batch_id": paper.import_batch_id,
            "import_status": batch.status if batch else "unknown",
            "import_time": batch.parsed_at.isoformat() if batch and batch.parsed_at else None,
            "created_at": paper.created_at.isoformat() if paper.created_at else None,
        })

    return ApiResponse.ok(result)


@router.get("/papers/{paper_id}")
def admin_qb_paper_detail(
    paper_id: str,
    _admin=Depends(require_permission("exam:read")),
    db: Session = Depends(get_db),
):
    """试卷详情（元信息 + 模块列表 + 题位概览）。"""
    paper = db.query(ExamPaperUnified).filter(ExamPaperUnified.id == paper_id).first()
    if not paper:
        return ApiResponse.fail("试卷不存在", code=404)

    sections = (
        db.query(PaperSection)
        .filter(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.sort_order)
        .all()
    )
    section_list = [
        {
            "id": s.id,
            "name": s.name,
            "sort_order": s.sort_order,
            "number_start": s.number_start,
            "number_end": s.number_end,
            "question_count": s.question_count,
        }
        for s in sections
    ]

    total_pos = (
        db.query(func.count(PaperQuestionPosition.id))
        .filter(PaperQuestionPosition.paper_id == paper_id)
        .scalar()
        or 0
    )

    batch = None
    if paper.import_batch_id:
        batch = db.query(ImportBatch).filter(ImportBatch.id == paper.import_batch_id).first()

    return ApiResponse.ok({
        "id": paper.id,
        "exam_year": paper.exam_year,
        "exam_kind": paper.exam_kind,
        "paper_type": paper.paper_type,
        "title": paper.title,
        "source_document": paper.source_document,
        "schema_version": paper.schema_version,
        "total_questions": paper.total_questions,
        "position_count": total_pos,
        "import_batch_id": paper.import_batch_id,
        "import_status": batch.status if batch else "unknown",
        "sections": section_list,
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
        "updated_at": paper.updated_at.isoformat() if paper.updated_at else None,
    })


@router.get("/papers/{paper_id}/positions")
def admin_qb_paper_positions(
    paper_id: str,
    _admin=Depends(require_permission("exam:read")),
    db: Session = Depends(get_db),
):
    """题位列表（按模块分组，每题位：number, question_id, stem摘要, answer, flags, provenance）。"""
    paper = db.query(ExamPaperUnified).filter(ExamPaperUnified.id == paper_id).first()
    if not paper:
        return ApiResponse.fail("试卷不存在", code=404)

    sections = (
        db.query(PaperSection)
        .filter(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.sort_order)
        .all()
    )

    result = []
    for section in sections:
        positions = (
            db.query(PaperQuestionPosition)
            .filter(
                PaperQuestionPosition.paper_id == paper_id,
                PaperQuestionPosition.section_id == section.id,
            )
            .order_by(PaperQuestionPosition.number)
            .all()
        )
        pos_list = []
        for pos in positions:
            version = _current_version(db, pos.question_id)
            stem = version.stem if version else ""
            answer = version.correct_answer_json if version else None
            if isinstance(answer, list):
                answer_display = "".join(str(a) for a in answer)
            elif answer is not None:
                answer_display = str(answer)
            else:
                answer_display = ""
            pos_list.append({
                "position_id": pos.id,
                "number": pos.number,
                "section_index": pos.section_index,
                "question_id": pos.question_id,
                "stem_summary": stem[:40] + ("…" if len(stem) > 40 else ""),
                "answer": answer_display,
                "has_answer": bool(answer),
                "quality_flags": pos.quality_flags_json or [],
                "provenance": pos.provenance_json,
                "source_key": pos.source_key,
                "lifecycle_status": (
                    db.query(QuestionItem.lifecycle_status)
                    .filter(QuestionItem.id == pos.question_id)
                    .scalar()
                ),
            })
        result.append({
            "section_id": section.id,
            "section_name": section.name,
            "number_start": section.number_start,
            "number_end": section.number_end,
            "question_count": section.question_count,
            "positions": pos_list,
        })

    return ApiResponse.ok(result)


@router.get("/papers/{paper_id}/reconcile")
def admin_qb_paper_reconcile(
    paper_id: str,
    _admin=Depends(require_permission("exam:read")),
    db: Session = Depends(get_db),
):
    """对账报告（题位数/答案覆盖率/断号/共享题数/flags统计）。"""
    paper = db.query(ExamPaperUnified).filter(ExamPaperUnified.id == paper_id).first()
    if not paper:
        return ApiResponse.fail("试卷不存在", code=404)

    positions = (
        db.query(PaperQuestionPosition)
        .filter(PaperQuestionPosition.paper_id == paper_id)
        .order_by(PaperQuestionPosition.number)
        .all()
    )

    total_positions = len(positions)
    numbers = [p.number for p in positions]

    # 断号检测
    missing_numbers = []
    if numbers:
        expected = set(range(min(numbers), max(numbers) + 1))
        missing_numbers = sorted(expected - set(numbers))

    # 答案覆盖率
    with_answer = 0
    without_explanation = 0
    for pos in positions:
        v = _current_version(db, pos.question_id)
        if v and v.correct_answer_json:
            with_answer += 1
        if v and not v.explanation:
            without_explanation += 1

    answer_coverage = round(with_answer / total_positions * 100, 1) if total_positions > 0 else 0

    # 共享题数（同一 question_id 出现在多份试卷）
    question_ids = [p.question_id for p in positions]
    shared_count = 0
    shared_questions = []
    for qid in set(question_ids):
        paper_count = (
            db.query(func.count(func.distinct(PaperQuestionPosition.paper_id)))
            .filter(PaperQuestionPosition.question_id == qid)
            .scalar()
            or 0
        )
        if paper_count > 1:
            shared_count += 1
            shared_questions.append({"question_id": qid, "paper_count": paper_count})

    # flags 统计
    flag_stats: dict[str, int] = defaultdict(int)
    high_risk_count = 0
    for pos in positions:
        flags = pos.quality_flags_json or []
        for f in flags:
            flag_name = f if isinstance(f, str) else f.get("flag", "")
            if flag_name:
                flag_stats[flag_name] += 1
                if flag_name in HIGH_RISK_FLAGS:
                    high_risk_count += 1

    # 模块对账
    sections = (
        db.query(PaperSection)
        .filter(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.sort_order)
        .all()
    )
    section_reconcile = []
    for sec in sections:
        sec_positions = [p for p in positions if p.section_id == sec.id]
        sec_with_answer = sum(
            1 for p in sec_positions
            if _current_version(db, p.question_id) and _current_version(db, p.question_id).correct_answer_json
        )
        section_reconcile.append({
            "section_name": sec.name,
            "expected_count": sec.question_count,
            "actual_count": len(sec_positions),
            "answer_count": sec_with_answer,
            "number_range": f"{sec.number_start}-{sec.number_end}",
        })

    return ApiResponse.ok({
        "paper_id": paper.id,
        "paper_title": paper.title,
        "exam_year": paper.exam_year,
        "paper_type": paper.paper_type,
        "total_positions": total_positions,
        "expected_total": paper.total_questions,
        "answer_coverage": answer_coverage,
        "with_answer": with_answer,
        "without_answer": total_positions - with_answer,
        "without_explanation": without_explanation,
        "missing_numbers": missing_numbers,
        "missing_count": len(missing_numbers),
        "shared_question_count": shared_count,
        "shared_questions": shared_questions[:20],  # 最多展示20个
        "flag_stats": dict(flag_stats),
        "high_risk_flag_count": high_risk_count,
        "sections": section_reconcile,
    })


# ═══════════════════════════════════════════════════════
#  3. 发布门禁
# ═══════════════════════════════════════════════════════

@router.post("/questions/{question_id}/publish")
def admin_qb_publish_question(
    question_id: str,
    _admin=Depends(require_permission("exam:write")),
    db: Session = Depends(get_db),
):
    """发布题目（带门禁检查）。

    门禁：
    - 缺答案 → 400 拒绝
    - 高风险 flag → 400 拒绝
    - 未审核（lifecycle_status=disputed）→ 400 拒绝
    - 缺解析 → 警告但可发布
    通过后 lifecycle_status → active
    """
    item = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not item:
        return ApiResponse.fail("题目不存在", code=404)

    version = _current_version(db, question_id)
    warnings: list[str] = []

    # 门禁1：缺答案
    if not version or not version.correct_answer_json:
        return ApiResponse.fail("发布失败：题目缺少答案，无法发布", code=400)

    # 门禁2：高风险 flag
    has_high_risk, high_risk_flags = _question_has_high_risk_flag(db, question_id)
    if has_high_risk:
        return ApiResponse.fail(
            f"发布失败：题目存在高风险质量标记 [{', '.join(high_risk_flags)}]，无法发布",
            code=400,
        )

    # 门禁3：未审核（pending_review / disputed 状态）
    if item.lifecycle_status in ("pending_review", "disputed"):
        return ApiResponse.fail(
            f"发布失败：题目处于 {item.lifecycle_status} 状态，未审核通过，无法发布", code=400
        )

    # 警告：缺解析
    if not version or not version.explanation:
        warnings.append("题目缺少解析，已发布但建议补充解析")

    # 通过门禁 → 发布
    item.lifecycle_status = "active"
    db.commit()
    db.refresh(item)

    return ApiResponse.ok({
        "id": item.id,
        "lifecycle_status": item.lifecycle_status,
        "published": True,
        "warnings": warnings,
    })


@router.post("/questions/{question_id}/unpublish")
def admin_qb_unpublish_question(
    question_id: str,
    _admin=Depends(require_permission("exam:write")),
    db: Session = Depends(get_db),
):
    """下线题目（lifecycle_status → retired）。"""
    item = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not item:
        return ApiResponse.fail("题目不存在", code=404)

    item.lifecycle_status = "retired"
    db.commit()
    db.refresh(item)

    return ApiResponse.ok({
        "id": item.id,
        "lifecycle_status": item.lifecycle_status,
        "unpublished": True,
    })
