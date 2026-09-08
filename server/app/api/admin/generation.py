"""生成工作台管理 API：批次/模板版本/自动校验/教研审核。

设计依据：docs/architecture/question-bank-persistence-admin-design.md §7.5, §4.11
生成题源数据为只读 JSON，审核结论持久化到 review_records / question_items。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.admin._deps import ApiResponse, get_db, require_permission
from app.models.generation import GenerationBatch, ReviewRecord
from app.models.question_bank import QuestionItem
from app.services import generation_service as gs

router = APIRouter(prefix="/generation", tags=["生成工作台"])


# ═══════════════════════════════════════════════════════
#  请求体
# ═══════════════════════════════════════════════════════

class RunBatchBody(BaseModel):
    engine_type: str = Field(..., description="qa_data_analysis / qa_quantity")
    skill: str = Field("", description="技能/子题型")
    count: int = Field(10, ge=1, le=100)
    seed: int = Field(42)


class ReviewBody(BaseModel):
    action: str = Field(..., description="approve / reject")
    comment: str = Field("")
    reviewer: str = Field("")
    batch_id: str | None = Field(None, description="关联批次 ID（可选）")


class BatchReviewBody(BaseModel):
    action: str = Field(..., description="approve / reject")
    comment: str = Field("")
    reviewer: str = Field("")
    question_ids: list[str] = Field(..., description="题目 ID 列表")


# ═══════════════════════════════════════════════════════
#  内部工具
# ═══════════════════════════════════════════════════════

def _latest_review(db: Session, question_id: str) -> ReviewRecord | None:
    """获取某题最新审核记录。"""
    return (
        db.query(ReviewRecord)
        .filter(ReviewRecord.question_id == question_id)
        .order_by(ReviewRecord.created_at.desc())
        .first()
    )


def _enrich_review_status(db: Session, question: dict[str, Any]) -> dict[str, Any]:
    """为题目摘要叠加最新审核状态。"""
    rr = _latest_review(db, question["question_id"])
    if rr:
        question["review_status"] = rr.action
        question["review_comment"] = rr.comment
        question["reviewer"] = rr.reviewer
        question["reviewed_at"] = rr.created_at.isoformat() if rr.created_at else None
    else:
        question["review_status"] = "pending"
        question["review_comment"] = ""
        question["reviewer"] = ""
        question["reviewed_at"] = None
    return question


def _find_question_item(db: Session, question_id: str) -> QuestionItem | None:
    """尝试在 question_items 中匹配生成题（origin_type=generated + id 或 canonical_hash）。"""
    # 优先精确匹配 id
    item = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if item:
        return item
    # 按 origin_type=generated 模糊匹配（生成题导入后 id 可能不同，但可通过其他方式关联）
    return None


def _sync_batch_record(db: Session, batch_id: str, engine_type: str, template_version: str,
                        total: int, passed: int, failed: int, source_file: str) -> GenerationBatch:
    """确保 generation_batches 表中有对应记录（upsert）。"""
    record = db.query(GenerationBatch).filter(GenerationBatch.id == batch_id).first()
    if record:
        record.engine_type = engine_type
        record.template_version = template_version
        record.total_count = total
        record.passed_count = passed
        record.failed_count = failed
        record.source_file = source_file
        record.status = "completed"
    else:
        record = GenerationBatch(
            id=batch_id,
            engine_type=engine_type,
            template_version=template_version,
            source_file=source_file,
            total_count=total,
            passed_count=passed,
            failed_count=failed,
            status="completed",
        )
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ═══════════════════════════════════════════════════════
#  1. 生成批次
# ═══════════════════════════════════════════════════════

@router.get("/batches")
def admin_generation_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    engine_type: str | None = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("exam:read")),
):
    """生成批次列表（从只读 JSON 聚合）。"""
    batches = gs.list_batches()
    if engine_type:
        batches = [b for b in batches if b["engine_type"] == engine_type]
    total = len(batches)
    start = (page - 1) * page_size
    items = batches[start:start + page_size]
    # 同步批次记录到 DB
    for b in items:
        _sync_batch_record(db, b["batch_id"], b["engine_type"], b["template_version"],
                            b["total_questions"], b["passed_count"], b["failed_count"], b["source_file"])
    return ApiResponse(data={"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/batches/{batch_id}")
def admin_generation_batch_detail(
    batch_id: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("exam:read")),
):
    """批次详情：元信息 + 题目列表。"""
    batch = gs.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"批次 {batch_id} 不存在")
    # 叠加审核状态
    batch["questions"] = [_enrich_review_status(db, q) for q in batch["questions"]]
    # 同步 DB 记录
    _sync_batch_record(db, batch["batch_id"], batch["engine_type"], batch["template_version"],
                        batch["total_questions"], batch["passed_count"], batch["failed_count"], batch["source_file"])
    return ApiResponse(data=batch)


@router.post("/batches/run")
def admin_generation_batch_run(
    body: RunBatchBody,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("exam:read")),
):
    """触发生成（调用引擎脚本）。

    当前为受控触发：记录批次元信息，实际引擎调用需在服务器环境执行。
    返回创建的批次 ID（pending 状态）。
    """
    import uuid
    batch_id = f"batch-{body.engine_type}-{uuid.uuid4().hex[:8]}"
    record = GenerationBatch(
        id=batch_id,
        engine_type=body.engine_type,
        skill=body.skill,
        param_json={"count": body.count, "seed": body.seed, "skill": body.skill},
        total_count=0,
        passed_count=0,
        failed_count=0,
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return ApiResponse(data={
        "batch_id": batch_id,
        "status": "pending",
        "message": f"已创建生成任务（engine={body.engine_type}, count={body.count}, seed={body.seed}），引擎执行需在服务器侧触发",
    })


# ═══════════════════════════════════════════════════════
#  2. 模板版本
# ═══════════════════════════════════════════════════════

@router.get("/templates")
def admin_generation_templates(
    _admin=Depends(require_permission("exam:read")),
):
    """模板列表。"""
    return ApiResponse(data=gs.list_templates())


@router.get("/templates/{template_id}/history")
def admin_generation_template_history(
    template_id: str,
    _admin=Depends(require_permission("exam:read")),
):
    """模板版本历史。"""
    history = gs.get_template_history(template_id)
    if not history:
        raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
    return ApiResponse(data=history)


# ═══════════════════════════════════════════════════════
#  3. 自动校验结果
# ═══════════════════════════════════════════════════════

@router.get("/batches/{batch_id}/validation")
def admin_generation_validation(
    batch_id: str,
    _admin=Depends(require_permission("exam:read")),
):
    """批次自动校验报告。"""
    report = gs.get_validation_report(batch_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"批次 {batch_id} 不存在")
    return ApiResponse(data=report)


# ═══════════════════════════════════════════════════════
#  4. 教研审核
# ═══════════════════════════════════════════════════════

@router.get("/review-tasks")
def admin_generation_review_tasks(
    status: str | None = Query(None, description="pending/approve/reject"),
    engine_type: str | None = None,
    module: str | None = None,
    subtype: str | None = None,
    difficulty: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("exam:read")),
):
    """审核任务列表：聚合所有批次的生成题，叠加审核状态。"""
    all_questions: list[dict[str, Any]] = []
    for batch in gs.list_batches():
        if engine_type and batch["engine_type"] != engine_type:
            continue
        for q in gs.get_batch_questions(batch["batch_id"]):
            q["batch_id"] = batch["batch_id"]
            q["engine_type"] = batch["engine_type"]
            all_questions.append(q)

    # 叠加审核状态
    for q in all_questions:
        _enrich_review_status(db, q)

    # 筛选
    filtered = all_questions
    if status:
        filtered = [q for q in filtered if q["review_status"] == status]
    if module:
        filtered = [q for q in filtered if q.get("module") == module]
    if subtype:
        filtered = [q for q in filtered if subtype in (q.get("subtype") or "")]
    if difficulty is not None:
        filtered = [q for q in filtered if q.get("difficulty") == difficulty]

    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start:start + page_size]

    # 统计
    stats = {
        "total": len(all_questions),
        "pending": sum(1 for q in all_questions if q["review_status"] == "pending"),
        "approved": sum(1 for q in all_questions if q["review_status"] == "approve"),
        "rejected": sum(1 for q in all_questions if q["review_status"] == "reject"),
    }

    return ApiResponse(data={"items": items, "total": total, "page": page, "page_size": page_size, "stats": stats})


@router.get("/questions/{question_id}")
def admin_generation_question_detail(
    question_id: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("exam:read")),
):
    """生成题详情（含生成元信息、计算树、干扰项错误路径、双求解结果）。"""
    # 跨批次搜索
    for batch in gs.list_batches():
        q = gs.get_question(batch["batch_id"], question_id)
        if q:
            # 叠加审核记录
            rr = _latest_review(db, question_id)
            q["review"] = {
                "status": rr.action if rr else "pending",
                "comment": rr.comment if rr else "",
                "reviewer": rr.reviewer if rr else "",
                "reviewed_at": rr.created_at.isoformat() if rr and rr.created_at else None,
            }
            # 关联 question_items
            item = _find_question_item(db, question_id)
            q["question_item_id"] = item.id if item else None
            q["lifecycle_status"] = item.lifecycle_status if item else None
            return ApiResponse(data=q)
    raise HTTPException(status_code=404, detail=f"生成题 {question_id} 不存在")


@router.post("/questions/{question_id}/review")
def admin_generation_question_review(
    question_id: str,
    body: ReviewBody,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("exam:read")),
):
    """提交审核结果：通过/驳回。

    - 通过：question_items.lifecycle_status → active（若已导入）
    - 驳回：lifecycle_status → disputed（若已导入）
    - 审核结论持久化到 review_records
    """
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action 必须为 approve 或 reject")

    # 确认题目存在
    found = False
    for batch in gs.list_batches():
        if gs.get_question(batch["batch_id"], question_id):
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail=f"生成题 {question_id} 不存在")

    # 创建审核记录
    import uuid
    rr = ReviewRecord(
        id=f"rr{uuid.uuid4().hex}",
        batch_id=body.batch_id,
        question_id=question_id,
        action=body.action,
        comment=body.comment,
        reviewer=body.reviewer or "admin",
    )
    db.add(rr)

    # 同步 question_items.lifecycle_status（若题已导入）
    item = _find_question_item(db, question_id)
    if item:
        rr.question_item_id = item.id
        if body.action == "approve":
            item.lifecycle_status = "approved"
        elif body.action == "reject":
            item.lifecycle_status = "disputed"

    db.commit()
    db.refresh(rr)

    return ApiResponse(data={
        "question_id": question_id,
        "action": body.action,
        "review_record_id": rr.id,
        "question_item_id": rr.question_item_id,
        "lifecycle_status": item.lifecycle_status if item else None,
        "message": f"已{'通过' if body.action == 'approve' else '驳回'}题目 {question_id}",
    })


@router.post("/questions/batch-review")
def admin_generation_batch_review(
    body: BatchReviewBody,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("exam:read")),
):
    """批量审核：选中多题批量通过/驳回。"""
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action 必须为 approve 或 reject")

    import uuid
    results = []
    for qid in body.question_ids:
        rr = ReviewRecord(
            id=f"rr{uuid.uuid4().hex}",
            question_id=qid,
            action=body.action,
            comment=body.comment,
            reviewer=body.reviewer or "admin",
        )
        db.add(rr)
        item = _find_question_item(db, qid)
        if item:
            rr.question_item_id = item.id
            item.lifecycle_status = "approved" if body.action == "approve" else "disputed"
        results.append({"question_id": qid, "action": body.action})

    db.commit()
    return ApiResponse(data={
        "processed": len(results),
        "action": body.action,
        "results": results,
    })


# ═══════════════════════════════════════════════════════
#  5. 工作台统计
# ═══════════════════════════════════════════════════════

@router.get("/stats")
def admin_generation_stats(
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("exam:read")),
):
    """生成工作台首页统计卡片数据。"""
    batches = gs.list_batches()
    total_questions = sum(b["total_questions"] for b in batches)
    total_passed = sum(b["passed_count"] for b in batches)
    pass_rate = round(total_passed / total_questions, 4) if total_questions else 0

    # 审核统计
    all_qids: list[str] = []
    for b in batches:
        for q in gs.get_batch_questions(b["batch_id"]):
            all_qids.append(q["question_id"])

    approved = 0
    rejected = 0
    pending = 0
    for qid in all_qids:
        rr = _latest_review(db, qid)
        if rr is None:
            pending += 1
        elif rr.action == "approve":
            approved += 1
        elif rr.action == "reject":
            rejected += 1

    # 已发布 = 审核通过且已导入 question_items 并 active
    published = (
        db.query(QuestionItem)
        .filter(QuestionItem.origin_type == "generated", QuestionItem.lifecycle_status == "active")
        .count()
    )

    return ApiResponse(data={
        "total_generated": total_questions,
        "auto_pass_rate": pass_rate,
        "auto_passed": total_passed,
        "auto_failed": total_questions - total_passed,
        "pending_review": pending,
        "approved": approved,
        "rejected": rejected,
        "published": published,
        "batch_count": len(batches),
        "by_engine": {
            b["engine_type"]: {
                "total": b["total_questions"],
                "passed": b["passed_count"],
                "failed": b["failed_count"],
            }
            for b in batches
        },
    })
