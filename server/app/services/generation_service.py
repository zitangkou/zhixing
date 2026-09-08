"""生成题数据读取服务：从只读 JSON 产出文件中聚合批次/题目/校验信息。

不修改原始 JSON 文件，仅读取。生成题源文件位于 xingce-structured-data/generated/。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 生成题产出目录（相对于项目根）
_GENERATED_DIR = Path(__file__).resolve().parents[3] / "xingce-structured-data" / "generated"

# 已知批次文件 → 引擎类型映射
_BATCH_FILES: list[dict[str, str]] = [
    {
        "batch_id": "batch-qa-data-analysis-v2",
        "engine_type": "qa_data_analysis",
        "file": "qa_data_analysis_v2.json",
        "label": "资料分析 v2（6 能力 32 题）",
    },
    {
        "batch_id": "batch-qa-quantity-v1",
        "engine_type": "qa_quantity",
        "file": "qa_quantity_v1.json",
        "label": "数量关系 v1（工程/行程 10 题）",
    },
    {
        "batch_id": "batch-qa-verbal-v2",
        "engine_type": "qa_verbal",
        "file": "qa_verbal_v2.json",
        "label": "言语理解 v2（选词/排序/标题 40 题）",
    },
    {
        "batch_id": "batch-qa-judgment-v1",
        "engine_type": "qa_judgment",
        "file": "qa_judgment_v1.json",
        "label": "判断推理 v1（定义/翻译/图形/论证/类比 35 题）",
    },
    {
        "batch_id": "batch-qa-theory-v1",
        "engine_type": "qa_theory",
        "file": "qa_theory_v1.json",
        "label": "常识/政治理论 v1（常识10+政治理论10 题）",
    },
]

# 模板元数据（从引擎脚本中提取的模板信息）
_TEMPLATES: list[dict[str, Any]] = [
    {
        "template_id": "tpl-qa-data-analysis-v2",
        "engine_type": "qa_data_analysis",
        "skill": "资料分析",
        "version": "full_capability_v2",
        "description": "资料分析全能力模板：基期量、增长率、增长量、比重、平均数、倍数 6 种能力，双求解器校验",
        "param_schema": {
            "count": {"type": "integer", "default": 32, "description": "生成题数"},
            "seed": {"type": "integer", "default": 42, "description": "随机种子"},
            "capabilities": {"type": "array", "items": {"type": "string"}, "description": "能力子集"},
        },
        "created_at": "2026-09-03T08:38:54",
    },
    {
        "template_id": "tpl-qa-quantity-v1",
        "engine_type": "qa_quantity",
        "skill": "数量关系",
        "version": "quantity_work_travel_v1",
        "description": "数量关系工程/行程模板：合作完成、轮流工作、相遇追及等，sympy 符号求解 + 直接公式双校验",
        "param_schema": {
            "count": {"type": "integer", "default": 10, "description": "生成题数"},
            "seed": {"type": "integer", "default": 42, "description": "随机种子"},
            "subtypes": {"type": "array", "items": {"type": "string"}, "description": "子题型子集"},
        },
        "created_at": "2026-09-03T08:37:40",
    },
]

# 模板版本历史
_TEMPLATE_HISTORY: dict[str, list[dict[str, Any]]] = {
    "tpl-qa-data-analysis-v2": [
        {"version": "full_capability_v2", "date": "2026-09-03", "changes": "扩展至 6 种能力，增加双求解器精确比对", "file": "qa_data_analysis_v2.json"},
        {"version": "base_growth_v1", "date": "2026-08-28", "changes": "初始版本：基期量与增长率两类", "file": "qa_data_analysis_v1.json"},
    ],
    "tpl-qa-quantity-v1": [
        {"version": "quantity_work_travel_v1", "date": "2026-09-03", "changes": "初始版本：工程问题与行程问题", "file": "qa_quantity_v1.json"},
    ],
}


def _load_json(file_name: str) -> dict[str, Any] | None:
    """加载生成题 JSON 文件，失败返回 None。"""
    path = _GENERATED_DIR / file_name
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_batches() -> list[dict[str, Any]]:
    """聚合所有已知批次的元信息与校验摘要。"""
    result = []
    for meta in _BATCH_FILES:
        data = _load_json(meta["file"])
        if data is None:
            continue
        questions = data.get("questions", [])
        passed = sum(1 for q in questions if _question_passed(q))
        failed = len(questions) - passed
        result.append({
            "batch_id": meta["batch_id"],
            "engine_type": meta["engine_type"],
            "label": meta["label"],
            "template_version": data.get("template_version", ""),
            "seed": data.get("seed"),
            "total_questions": len(questions),
            "passed_count": passed,
            "failed_count": failed,
            "pass_rate": round(passed / len(questions), 4) if questions else 0,
            "created_at": data.get("generated_at", ""),
            "status": "completed",
            "source_file": meta["file"],
        })
    return result


def get_batch(batch_id: str) -> dict[str, Any] | None:
    """获取批次详情：元信息 + 题目列表。"""
    meta = _find_batch_meta(batch_id)
    if meta is None:
        return None
    data = _load_json(meta["file"])
    if data is None:
        return None
    questions = data.get("questions", [])
    passed = sum(1 for q in questions if _question_passed(q))
    failed = len(questions) - passed
    return {
        "batch_id": meta["batch_id"],
        "engine_type": meta["engine_type"],
        "label": meta["label"],
        "template_version": data.get("template_version", ""),
        "seed": data.get("seed"),
        "dual_solve_method": data.get("dual_solve_method", ""),
        "total_questions": len(questions),
        "passed_count": passed,
        "failed_count": failed,
        "pass_rate": round(passed / len(questions), 4) if questions else 0,
        "created_at": data.get("generated_at", ""),
        "status": "completed",
        "source_file": meta["file"],
        "questions": [_question_summary(q) for q in questions],
    }


def get_batch_questions(batch_id: str) -> list[dict[str, Any]]:
    """获取批次的题目列表（摘要）。"""
    batch = get_batch(batch_id)
    return batch["questions"] if batch else []


def get_question(batch_id: str, question_id: str) -> dict[str, Any] | None:
    """获取单道生成题的完整详情（含生成元信息）。"""
    meta = _find_batch_meta(batch_id)
    if meta is None:
        return None
    data = _load_json(meta["file"])
    if data is None:
        return None
    for q in data.get("questions", []):
        if q.get("question_id") == question_id:
            return _question_detail(q, meta, data)
    return None


def get_validation_report(batch_id: str) -> dict[str, Any] | None:
    """获取批次自动校验报告。"""
    meta = _find_batch_meta(batch_id)
    if meta is None:
        return None
    data = _load_json(meta["file"])
    if data is None:
        return None
    questions = data.get("questions", [])
    per_question = []
    failure_dist: dict[str, int] = {}
    for q in questions:
        vr = _validate_question(q)
        per_question.append(vr)
        for reason in vr["failed_checks"]:
            failure_dist[reason] = failure_dist.get(reason, 0) + 1
    passed = sum(1 for v in per_question if v["all_passed"])
    return {
        "batch_id": batch_id,
        "total": len(questions),
        "passed": passed,
        "failed": len(questions) - passed,
        "pass_rate": round(passed / len(questions), 4) if questions else 0,
        "failure_distribution": failure_dist,
        "failed_questions": [v["question_id"] for v in per_question if not v["all_passed"]],
        "per_question": per_question,
    }


def list_templates() -> list[dict[str, Any]]:
    """模板列表。"""
    return list(_TEMPLATES)


def get_template_history(template_id: str) -> list[dict[str, Any]]:
    """模板版本历史。"""
    return _TEMPLATE_HISTORY.get(template_id, [])


# ═══════════════════════════════════════════════════════
#  内部工具
# ═══════════════════════════════════════════════════════

def _find_batch_meta(batch_id: str) -> dict[str, str] | None:
    for m in _BATCH_FILES:
        if m["batch_id"] == batch_id:
            return m
    return None


def _question_passed(q: dict[str, Any]) -> bool:
    """题是否通过全部自动校验。"""
    return _validate_question(q)["all_passed"]


def _validate_question(q: dict[str, Any]) -> dict[str, Any]:
    """对单题执行自动校验，返回各项校验结果。

    引擎专属校验（双求解/计算树/干扰项）仅在对应字段存在时检查，
    避免对言语/判断/常识等无此字段的引擎误判。
    """
    checks: dict[str, bool] = {}
    # 1. 双求解一致（仅当有 dual_solve 字段时检查；兼容 match/passed 两种字段）
    dual = q.get("dual_solve")
    if dual is not None:
        checks["dual_solve_match"] = bool(dual.get("match", False)) or bool(dual.get("passed", False))
    # 2. 选项互不相同
    options = q.get("options", {})
    values = [str(v).strip() for v in options.values()]
    checks["options_distinct"] = len(values) == len(set(values)) and len(values) >= 2
    # 3. 答案唯一且在选项中
    answer = q.get("answer", "")
    checks["answer_unique"] = bool(answer) and answer in options
    # 4. 数据一致性（仅当有 dual_solve 或 calc_tree 时检查）
    if dual is not None or q.get("calc_tree"):
        checks["data_consistent"] = _check_data_consistent(q)
    # 5. 干扰项可追溯（仅当有 distractors 字段时检查）
    distractors = q.get("distractors")
    if distractors is not None:
        non_correct = [k for k in options if k != answer]
        checks["distractors_traced"] = all(k in distractors for k in non_correct)
    # 6. 引擎自带校验（judgment/theory 的 validation 字段）
    engine_validation = q.get("validation")
    if isinstance(engine_validation, dict):
        issues = engine_validation.get("issues", [])
        checks["engine_validation_passed"] = len(issues) == 0
    # 7. 缺解析警告（不阻断，仅记录）
    has_explanation = bool(q.get("explanation", ""))
    checks["has_explanation"] = has_explanation

    failed = [name for name, ok in checks.items() if not ok]
    return {
        "question_id": q.get("question_id", ""),
        "subtype": q.get("subtype", ""),
        "difficulty": q.get("difficulty", 0),
        "checks": checks,
        "all_passed": len(failed) == 0,
        "failed_checks": failed,
    }


def _check_data_consistent(q: dict[str, Any]) -> bool:
    """检查答案与计算树/双求解结果的一致性（宽松校验）。"""
    answer = q.get("answer", "")
    options = q.get("options", {})
    if answer not in options:
        return False
    # 双求解有结果且 match/passed 为 true 即视为一致
    dual = q.get("dual_solve", {})
    if dual.get("match") is True or dual.get("passed") is True:
        return True
    # 有计算树且最后一步有 result
    calc = q.get("calc_tree", [])
    if calc and calc[-1].get("result") is not None:
        return True
    return False


def _question_summary(q: dict[str, Any]) -> dict[str, Any]:
    """构造题目列表摘要。"""
    dual = q.get("dual_solve", {})
    distractors = q.get("distractors", {})
    return {
        "question_id": q.get("question_id", ""),
        "origin_type": q.get("origin_type", "generated"),
        "module": q.get("module", ""),
        "subtype": q.get("subtype", ""),
        "difficulty": q.get("difficulty", 0),
        "answer": q.get("answer", ""),
        "dual_solve_match": bool(dual.get("match", False)),
        "distractor_count": len(distractors),
        "stem_summary": (q.get("stem", "") or "")[:50],
        "review_status": "pending",  # 由 API 层叠加实际审核状态
    }


def _question_detail(q: dict[str, Any], meta: dict[str, str], batch_data: dict[str, Any]) -> dict[str, Any]:
    """构造题目完整详情（含引擎专属字段）。"""
    detail = {
        "question_id": q.get("question_id", ""),
        "batch_id": meta["batch_id"],
        "engine_type": meta["engine_type"],
        "origin_type": q.get("origin_type", "generated"),
        "module": q.get("module", ""),
        "subtype": q.get("subtype", ""),
        "difficulty": q.get("difficulty", 0),
        "stem": q.get("stem", ""),
        "material": q.get("material"),
        "options": q.get("options", {}),
        "answer": q.get("answer", ""),
        "explanation": q.get("explanation", ""),
        "calc_tree": q.get("calc_tree", []),
        "distractors": q.get("distractors", {}),
        "dual_solve": q.get("dual_solve", {}),
        "generation_meta": {
            **q.get("generation_meta", {}),
            "batch_template_version": batch_data.get("template_version", ""),
            "batch_seed": batch_data.get("seed"),
            "engine_type": meta["engine_type"],
        },
        "validation": _validate_question(q),
    }
    # 引擎专属字段（言语/判断/常识）
    for key in ("passage", "target_word", "pos", "logic_signal", "context_constraints",
                "definition", "key_elements", "options_detail", "knowledge_point_id",
                "items", "media", "formulas", "topic", "tag", "review_status"):
        if key in q and q[key] is not None:
            detail[key] = q[key]
    return detail
