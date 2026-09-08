"""P3 学习反馈 — 管理后台分析 API（/admin/analytics/）

正确率统计、选项分布、错因归集、质量看板。
数据源：practice_answers 表 + Q2/Q3 生成题 JSON（question_id 关联 distractors）。
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.admin._deps import ApiResponse, get_db, require_permission
from app.models import PracticeAnswer

router = APIRouter(prefix="/analytics", tags=["学习反馈"])

# ── 题库 JSON 路径（与 practice_service 一致）──
_REPO_ROOT = Path(__file__).resolve().parents[4]
_QUESTION_BANK_PATH = _REPO_ROOT / "xingce-structured-data" / "generated" / "qa_data_analysis_v2.json"

_question_lookup: dict[str, dict[str, Any]] | None = None


def _load_question_lookup() -> dict[str, dict[str, Any]]:
    """懒加载题库，构建 question_id → 题目元数据 映射。"""
    global _question_lookup
    if _question_lookup is None:
        with open(_QUESTION_BANK_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _question_lookup = {q["question_id"]: q for q in data["questions"]}
    return _question_lookup


def _question_meta(qid: str) -> dict[str, Any] | None:
    """获取题目元数据（module/subtype/difficulty/options/answer/distractors）。"""
    return _load_question_lookup().get(qid)


def _filter_query(
    db: Session,
    module: str | None = None,
    subtype: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    origin_type: str | None = None,
    source: str | None = None,
):
    """构建 practice_answers 基础查询，按参数过滤。

    module/subtype/origin_type 需要关联题库 JSON 过滤（question_id 维度）。
    """
    q = db.query(PracticeAnswer)

    if source:
        q = q.filter(PracticeAnswer.source == source)
    if date_from:
        q = q.filter(PracticeAnswer.created_at >= date_from)
    if date_to:
        q = q.filter(PracticeAnswer.created_at <= date_to + " 23:59:59")

    # module/subtype/origin_type 过滤：先从题库找出匹配的 question_id 集合
    if module or subtype or origin_type:
        lookup = _load_question_lookup()
        matched_ids: set[str] = set()
        for qid, qdata in lookup.items():
            if module and qdata.get("module", "") != module:
                continue
            if subtype and qdata.get("subtype", "") != subtype:
                continue
            if origin_type and qdata.get("origin_type", "") != origin_type:
                continue
            matched_ids.add(qid)
        q = q.filter(PracticeAnswer.question_id.in_(matched_ids))

    return q


def _accuracy_from_rows(rows: list[PracticeAnswer]) -> dict[str, Any]:
    """从作答记录行计算正确率汇总。"""
    total = len(rows)
    correct = sum(1 for r in rows if r.is_correct)
    rate = round(correct / total * 100, 2) if total else 0.0
    avg_time = round(sum(r.time_spent_ms for r in rows) / total, 0) if total else 0
    return {
        "total_attempts": total,
        "correct_count": correct,
        "accuracy_rate": rate,
        "avg_time_ms": int(avg_time),
    }


# ═══════════════════════════════════════════════════════
#  1. 正确率统计
# ═══════════════════════════════════════════════════════

@router.get("/accuracy")
def get_accuracy(
    db: Session = Depends(get_db),
    module: str | None = Query(None, description="模块筛选，如 资料分析"),
    subtype: str | None = Query(None, description="子题型筛选"),
    date_from: str | None = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    origin_type: str | None = Query(None, description="real/generated"),
    source: str | None = Query(None, description="real/demo，默认全部"),
    _=Depends(require_permission("exam:read")),
):
    """正确率汇总：总体 + 按模块 + 按子题型。"""
    rows = _filter_query(db, module, subtype, date_from, date_to, origin_type, source).all()
    overall = _accuracy_from_rows(rows)

    # 按模块分组
    lookup = _load_question_lookup()
    by_module_map: dict[str, list[PracticeAnswer]] = defaultdict(list)
    by_subtype_map: dict[str, list[PracticeAnswer]] = defaultdict(list)
    for r in rows:
        meta = lookup.get(r.question_id, {})
        m = meta.get("module", "未知")
        s = meta.get("subtype", "未知")
        by_module_map[m].append(r)
        by_subtype_map[s].append(r)

    by_module = [
        {"module": m, "attempts": len(v), "correct_count": sum(1 for x in v if x.is_correct),
         "accuracy": round(sum(1 for x in v if x.is_correct) / len(v) * 100, 2) if v else 0}
        for m, v in sorted(by_module_map.items(), key=lambda x: -len(x[1]))
    ]
    by_subtype = [
        {"subtype": s, "attempts": len(v), "correct_count": sum(1 for x in v if x.is_correct),
         "accuracy": round(sum(1 for x in v if x.is_correct) / len(v) * 100, 2) if v else 0}
        for s, v in sorted(by_subtype_map.items(), key=lambda x: -len(x[1]))
    ]

    return ApiResponse.ok({
        **overall,
        "by_module": by_module,
        "by_subtype": by_subtype,
    })


@router.get("/accuracy/questions/{question_id}")
def get_question_accuracy(
    question_id: str,
    db: Session = Depends(get_db),
    source: str | None = Query(None, description="real/demo"),
    _=Depends(require_permission("exam:read")),
):
    """单题正确率：作答次数、正确数、正确率、平均用时。"""
    q = db.query(PracticeAnswer).filter(PracticeAnswer.question_id == question_id)
    if source:
        q = q.filter(PracticeAnswer.source == source)
    rows = q.all()
    stats = _accuracy_from_rows(rows)
    return ApiResponse.ok({
        "question_id": question_id,
        **stats,
    })


# ═══════════════════════════════════════════════════════
#  2. 选项分布
# ═══════════════════════════════════════════════════════

def _option_distribution_for(question_id: str, rows: list[PracticeAnswer]) -> dict[str, Any]:
    """计算单题选项分布。"""
    meta = _question_meta(question_id) or {}
    correct_answer = (meta.get("answer") or "").strip().upper()
    options = meta.get("options", {}) or {}

    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        ua = (r.user_answer or "").strip().upper()
        if ua:
            counts[ua] += 1

    total = sum(counts.values())
    distribution = []
    for label in sorted(options.keys()):
        c = counts.get(label, 0)
        distribution.append({
            "label": label,
            "text": options.get(label, ""),
            "count": c,
            "percentage": round(c / total * 100, 2) if total else 0,
            "is_correct": label == correct_answer,
        })

    # 异常检测
    anomalies: list[str] = []
    correct_item = next((d for d in distribution if d["is_correct"]), None)
    if correct_item and correct_item["percentage"] < 10 and total >= 5:
        anomalies.append("正确项选择率极低（<10%），题目可能有问题")
    percentages = [d["percentage"] for d in distribution if d["count"] > 0]
    for i in range(len(percentages)):
        for j in range(i + 1, len(percentages)):
            if abs(percentages[i] - percentages[j]) < 5 and percentages[i] >= 20:
                anomalies.append("两个选项选择率接近（差<5%），可能有歧义")
                break
        if anomalies and anomalies[-1].startswith("两个"):
            break

    return {
        "question_id": question_id,
        "total_attempts": total,
        "correct_answer": correct_answer,
        "option_distribution": distribution,
        "anomalies": anomalies,
    }


@router.get("/options/{question_id}")
def get_option_distribution(
    question_id: str,
    db: Session = Depends(get_db),
    source: str | None = Query(None),
    _=Depends(require_permission("exam:read")),
):
    """单题选项分布：A/B/C/D 各选项选择次数、占比、正确项标记、异常检测。"""
    q = db.query(PracticeAnswer).filter(PracticeAnswer.question_id == question_id)
    if source:
        q = q.filter(PracticeAnswer.source == source)
    rows = q.all()
    return ApiResponse.ok(_option_distribution_for(question_id, rows))


@router.post("/options/batch")
def get_option_distribution_batch(
    body: dict,
    db: Session = Depends(get_db),
    source: str | None = Query(None),
    _=Depends(require_permission("exam:read")),
):
    """批次选项分布：按题目列表批量查询。

    Body: {"question_ids": ["q1", "q2", ...]}
    """
    question_ids = body.get("question_ids", [])
    if not question_ids:
        return ApiResponse.ok({"results": []})

    q = db.query(PracticeAnswer).filter(PracticeAnswer.question_id.in_(question_ids))
    if source:
        q = q.filter(PracticeAnswer.source == source)
    rows = q.all()

    by_qid: dict[str, list[PracticeAnswer]] = defaultdict(list)
    for r in rows:
        by_qid[r.question_id].append(r)

    results = []
    for qid in question_ids:
        results.append(_option_distribution_for(qid, by_qid.get(qid, [])))

    return ApiResponse.ok({"results": results})


# ═══════════════════════════════════════════════════════
#  3. 错因归集
# ═══════════════════════════════════════════════════════

def _error_path_for(question_id: str, user_answer: str) -> str | None:
    """从选错选项 → 查找 distractors 中对应选项的 distractor_type。"""
    meta = _question_meta(question_id)
    if not meta:
        return None
    distractors = meta.get("distractors", {}) or {}
    ua = (user_answer or "").strip().upper()
    dist = distractors.get(ua)
    if dist:
        return dist.get("type", "未知错误")
    return "其他错误"


@router.get("/error-paths")
def get_error_paths(
    db: Session = Depends(get_db),
    module: str | None = Query(None),
    subtype: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    origin_type: str | None = Query(None),
    source: str | None = Query(None),
    _=Depends(require_permission("exam:read")),
):
    """错误路径汇总：各 distractor_type 出现频次、占比、示例题。"""
    rows = _filter_query(db, module, subtype, date_from, date_to, origin_type, source).all()
    wrong_rows = [r for r in rows if not r.is_correct]
    total_errors = len(wrong_rows)

    path_counts: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "question_ids": set()})
    for r in wrong_rows:
        ep = _error_path_for(r.question_id, r.user_answer)
        if ep:
            path_counts[ep]["count"] += 1
            path_counts[ep]["question_ids"].add(r.question_id)

    by_error_path = []
    for ep_type, info in sorted(path_counts.items(), key=lambda x: -x[1]["count"]):
        qids = list(info["question_ids"])[:5]
        by_error_path.append({
            "type": ep_type,
            "count": info["count"],
            "percentage": round(info["count"] / total_errors * 100, 2) if total_errors else 0,
            "involved_question_count": len(info["question_ids"]),
            "example_question_ids": qids,
        })

    return ApiResponse.ok({
        "total_errors": total_errors,
        "by_error_path": by_error_path,
    })


@router.get("/error-paths/questions/{question_id}")
def get_question_error_paths(
    question_id: str,
    db: Session = Depends(get_db),
    source: str | None = Query(None),
    _=Depends(require_permission("exam:read")),
):
    """单题错因分布：用户选错选项对应的错误路径类型分布。"""
    q = db.query(PracticeAnswer).filter(
        PracticeAnswer.question_id == question_id,
        PracticeAnswer.is_correct == False,  # noqa: E712
    )
    if source:
        q = q.filter(PracticeAnswer.source == source)
    rows = q.all()
    total_wrong = len(rows)

    path_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        ep = _error_path_for(question_id, r.user_answer)
        if ep:
            path_counts[ep] += 1

    distribution = [
        {"type": t, "count": c, "percentage": round(c / total_wrong * 100, 2) if total_wrong else 0}
        for t, c in sorted(path_counts.items(), key=lambda x: -x[1])
    ]

    # 干扰项溯源
    meta = _question_meta(question_id) or {}
    distractors = meta.get("distractors", {}) or {}
    distractor_trace = []
    for opt_label, dist in sorted(distractors.items()):
        distractor_trace.append({
            "option": opt_label,
            "type": dist.get("type", ""),
            "error_formula": dist.get("error_formula", ""),
            "computed_value": dist.get("computed_value", ""),
        })

    return ApiResponse.ok({
        "question_id": question_id,
        "total_wrong": total_wrong,
        "error_path_distribution": distribution,
        "distractor_trace": distractor_trace,
    })


# ═══════════════════════════════════════════════════════
#  4. 质量看板
# ═══════════════════════════════════════════════════════

@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    source: str | None = Query(None, description="real/demo，默认全部"),
    _=Depends(require_permission("exam:read")),
):
    """汇总看板：总练习人次、总正确率、高频错误路径TOP5、低正确率题TOP10、疑似歧义题。"""
    q = db.query(PracticeAnswer)
    if source:
        q = q.filter(PracticeAnswer.source == source)
    all_rows = q.all()

    total_attempts = len(all_rows)
    correct_count = sum(1 for r in all_rows if r.is_correct)
    overall_accuracy = round(correct_count / total_attempts * 100, 2) if total_attempts else 0
    avg_time = round(sum(r.time_spent_ms for r in all_rows) / total_attempts, 0) if total_attempts else 0
    active_questions = len(set(r.question_id for r in all_rows))

    # 按题统计正确率
    by_qid: dict[str, list[PracticeAnswer]] = defaultdict(list)
    for r in all_rows:
        by_qid[r.question_id].append(r)

    question_stats = []
    for qid, rows in by_qid.items():
        total = len(rows)
        correct = sum(1 for r in rows if r.is_correct)
        meta = _question_meta(qid) or {}
        question_stats.append({
            "question_id": qid,
            "module": meta.get("module", ""),
            "subtype": meta.get("subtype", ""),
            "difficulty": meta.get("difficulty", 0),
            "attempts": total,
            "correct_count": correct,
            "accuracy": round(correct / total * 100, 2) if total else 0,
            "rows": rows,
        })

    # 低正确率 TOP10（至少 3 次作答）
    low_accuracy = [s for s in question_stats if s["attempts"] >= 3]
    low_accuracy.sort(key=lambda x: (x["accuracy"], -x["attempts"]))
    low_accuracy_top10 = [
        {k: v for k, v in s.items() if k != "rows"}
        for s in low_accuracy[:10]
    ]

    # 高频错误路径 TOP5
    wrong_rows = [r for r in all_rows if not r.is_correct]
    path_counts: dict[str, int] = defaultdict(int)
    for r in wrong_rows:
        ep = _error_path_for(r.question_id, r.user_answer)
        if ep:
            path_counts[ep] += 1
    total_errors = len(wrong_rows)
    top_error_paths = [
        {"type": t, "count": c, "percentage": round(c / total_errors * 100, 2) if total_errors else 0}
        for t, c in sorted(path_counts.items(), key=lambda x: -x[1])[:5]
    ]

    # 疑似歧义题：选项分布异常
    ambiguous_questions = []
    disputed_questions = []
    for s in question_stats:
        if s["attempts"] < 5:
            continue
        dist = _option_distribution_for(s["question_id"], s["rows"])
        if dist["anomalies"]:
            entry = {
                "question_id": s["question_id"],
                "module": s["module"],
                "subtype": s["subtype"],
                "attempts": s["attempts"],
                "accuracy": s["accuracy"],
                "anomalies": dist["anomalies"],
            }
            if any("歧义" in a for a in dist["anomalies"]):
                ambiguous_questions.append(entry)
            if any("正确项选择率极低" in a for a in dist["anomalies"]):
                disputed_questions.append(entry)

    return ApiResponse.ok({
        "total_attempts": total_attempts,
        "correct_count": correct_count,
        "overall_accuracy": overall_accuracy,
        "avg_time_ms": int(avg_time),
        "active_question_count": active_questions,
        "top_error_paths": top_error_paths,
        "low_accuracy_top10": low_accuracy_top10,
        "ambiguous_questions": ambiguous_questions,
        "disputed_questions": disputed_questions,
    })
