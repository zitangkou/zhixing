"""Q7 资料分析最小学习闭环 — 练习服务

从 qa_data_analysis_v2.json 读取题目，按 skill + date 生成确定性练习包。
不修改 P0 模型，不修改 Q2/Q3 生成引擎和题目数据（只读）。
提交结果暂存内存（原型阶段），daily_id 由 skill+date 确定性生成。
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# ── 题库路径 ──────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[3]
_QUESTION_BANK_PATH = _REPO_ROOT / "xingce-structured-data" / "generated" / "qa_data_analysis_v2.json"

# ── 6 种技能定义 ──────────────────────────────────────
SKILL_DEFS: dict[str, dict[str, Any]] = {
    "base_period": {
        "name": "基期量",
        "formula": "基期量 = 现期量 / (1 + 增长率)",
        "subtypes": ["基期量计算"],
        "tip": "注意区分基期与现期，增长率需先转为小数再代入。",
    },
    "growth_rate": {
        "name": "增长率",
        "formula": "增长率 = (现期量 - 基期量) / 基期量 × 100%",
        "subtypes": ["增长率计算"],
        "tip": "分母是基期量不是现期量；百分点与百分数不要混淆。",
    },
    "proportion": {
        "name": "比重",
        "formula": "比重 = 部分 / 整体 × 100%；两期比重差 = 现期比重 - 基期比重",
        "subtypes": ["现期比重计算", "已知整体和比重求部分", "已知部分和比重求整体", "两期比重差"],
        "tip": "判断比重升降看部分增长率与整体增长率的大小关系。",
    },
    "average": {
        "name": "平均数",
        "formula": "平均数 = 总量 / 份数；两期平均数增长率 = (a - b) / (1 + b)",
        "subtypes": ["现期平均数计算", "已知平均和份数求总量", "两期平均数差", "两期平均数增长率", "已知总量和平均求份数"],
        "tip": "平均数增长率公式中 a 是分子增长率，b 是分母增长率。",
    },
    "multiple": {
        "name": "倍数",
        "formula": "是几倍 = A / B；多几倍 = A / B - 1",
        "subtypes": ["是几倍", "多几倍", "基期倍数", "倍数与比重联合", "基期多几倍"],
        "tip": '"是几倍"与"多几倍"相差 1，审题时务必看清问法。',
    },
    "mixed_growth": {
        "name": "混合增长率",
        "formula": "整体增长率介于各部分增长率之间，且偏向基数较大的一方",
        "subtypes": ["混合增长率_整体率", "混合增长率_推断部分率", "混合增长率_十字交叉"],
        "tip": "十字交叉法得到的是基期量之比，不是现期量之比。",
    },
}

DIFFICULTY_LABELS = {1: "简单", 2: "中等", 3: "较难"}

# ── 内存缓存 ──────────────────────────────────────────
_question_bank: list[dict[str, Any]] | None = None
_package_cache: dict[str, dict[str, Any]] = {}
_submission_cache: dict[str, dict[str, Any]] = {}


def _load_question_bank() -> list[dict[str, Any]]:
    """懒加载题库 JSON。"""
    global _question_bank
    if _question_bank is None:
        with open(_QUESTION_BANK_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _question_bank = data["questions"]
    return _question_bank


def _questions_by_skill(skill: str) -> list[dict[str, Any]]:
    """按技能筛选题目。"""
    defn = SKILL_DEFS.get(skill)
    if not defn:
        return []
    subtypes = set(defn["subtypes"])
    bank = _load_question_bank()
    return [q for q in bank if q.get("subtype") in subtypes]


def _seed_for(skill: str, date: str) -> int:
    """由 skill + date 生成确定性种子。"""
    return hash(f"{skill}|{date}") & 0xFFFFFFFF


def _pick_deterministic(items: list[dict[str, Any]], count: int, seed: int) -> list[dict[str, Any]]:
    """确定性随机选取，不修改原列表。"""
    if len(items) <= count:
        return list(items)
    rng = random.Random(seed)
    idxs = list(range(len(items)))
    rng.shuffle(idxs)
    return [items[i] for i in idxs[:count]]


def _simplify_question(q: dict[str, Any]) -> dict[str, Any]:
    """精简题目字段，去掉 raw_data 等大字段，保留答题所需。"""
    material = q.get("material", {})
    return {
        "question_id": q["question_id"],
        "subtype": q.get("subtype", ""),
        "difficulty": q.get("difficulty", 1),
        "difficulty_label": DIFFICULTY_LABELS.get(q.get("difficulty", 1), "中等"),
        "stem": q.get("stem", ""),
        "options": q.get("options", {}),
        "answer": q.get("answer", ""),
        "explanation": q.get("explanation", ""),
        "calc_tree": q.get("calc_tree", []),
        "distractors": q.get("distractors", {}),
        "material": {
            "material_id": material.get("material_id", ""),
            "content": material.get("content", ""),
        },
    }


def generate_daily_package(skill: str, date: str) -> dict[str, Any]:
    """生成今日练习包（确定性，同一天同一技能结果一致）。

    返回: daily_id, skill, skill_name, formula, method_example, progressive, material_set, total_questions
    """
    if skill not in SKILL_DEFS:
        raise ValueError(f"未知技能: {skill}")

    daily_id = f"practice-{skill}-{date}"
    if daily_id in _package_cache:
        return _package_cache[daily_id]

    defn = SKILL_DEFS[skill]
    seed = _seed_for(skill, date)
    skill_questions = _questions_by_skill(skill)

    # ── 方法示例：取最简单的 1 题 ──
    sorted_by_diff = sorted(skill_questions, key=lambda q: (q.get("difficulty", 9), q["question_id"]))
    method_example = _simplify_question(sorted_by_diff[0]) if sorted_by_diff else None

    # ── 渐进训练：3 题（简单→中等→较难）──
    # 优先按难度分层选取；题量不足时按确定性随机补足
    progressive: list[dict[str, Any]] = []
    used_ids = {method_example["question_id"]} if method_example else set()
    remaining = [q for q in sorted_by_diff if q["question_id"] not in used_ids]

    if len(remaining) >= 3:
        # 尝试按难度 1/2/3 各取一题
        by_diff: dict[int, list[dict[str, Any]]] = {}
        for q in remaining:
            d = q.get("difficulty", 2)
            by_diff.setdefault(d, []).append(q)
        for target_diff in (1, 2, 3):
            candidates = by_diff.get(target_diff, [])
            if candidates:
                picked = _pick_deterministic(candidates, 1, seed + target_diff)[0]
            else:
                # 该难度无题，从剩余中确定性补选
                pool = [q for q in remaining if q["question_id"] not in {p["question_id"] for p in progressive}]
                picked = _pick_deterministic(pool, 1, seed + target_diff + 100)[0] if pool else None
            if picked:
                progressive.append(_simplify_question(picked))
                used_ids.add(picked["question_id"])
    else:
        # 题量不足 3，全部用上
        progressive = [_simplify_question(q) for q in remaining[:3]]

    # ── 材料题组：5 题共享同一材料 ──
    # 选题库中题目数 ≥ 5 的材料，按种子确定性选一个，取 5 题
    bank = _load_question_bank()
    material_groups: dict[str, list[dict[str, Any]]] = {}
    for q in bank:
        mid = q.get("material", {}).get("material_id", "")
        if mid:
            material_groups.setdefault(mid, []).append(q)
    eligible_materials = {mid: qs for mid, qs in material_groups.items() if len(qs) >= 5}

    material_set: list[dict[str, Any]] = []
    material_content = ""
    if eligible_materials:
        mat_ids = sorted(eligible_materials.keys())
        rng = random.Random(seed + 500)
        chosen_mid = rng.choice(mat_ids)
        group = eligible_materials[chosen_mid]
        picked = _pick_deterministic(group, 5, seed + 600)
        material_set = [_simplify_question(q) for q in picked]
        material_content = picked[0].get("material", {}).get("content", "")

    total = (1 if method_example else 0) + len(progressive) + len(material_set)

    package = {
        "daily_id": daily_id,
        "skill": skill,
        "skill_name": defn["name"],
        "formula": defn["formula"],
        "tip": defn["tip"],
        "date": date,
        "method_example": method_example,
        "progressive": progressive,
        "material_set": material_set,
        "material_content": material_content,
        "total_questions": total,
    }
    _package_cache[daily_id] = package
    return package


def _find_question_in_package(package: dict[str, Any], question_id: str) -> dict[str, Any] | None:
    """在练习包中查找题目。"""
    for section in ("method_example", "progressive", "material_set"):
        item = package.get(section)
        if isinstance(item, dict) and item.get("question_id") == question_id:
            return item
        if isinstance(item, list):
            for q in item:
                if q.get("question_id") == question_id:
                    return q
    return None


def submit_answers(
    daily_id: str,
    answers: list[dict[str, str]],
    db: Session | None = None,
    user_id: str = "anonymous",
    source: str = "real",
) -> dict[str, Any]:
    """提交答案，返回逐题判定与错因映射。

    请求: [{question_id, user_answer}]
    返回: {daily_id, total, correct_count, wrong_count, results: [...]}
    若传入 db，则将每题作答持久化到 practice_answers 表。
    """
    package = _package_cache.get(daily_id)
    if not package:
        # 尝试从 daily_id 反解 skill+date 重新生成
        parts = daily_id.split("-", 2)
        if len(parts) == 3 and parts[0] == "practice":
            skill, date = parts[1], parts[2]
            package = generate_daily_package(skill, date)
        else:
            raise ValueError(f"练习包不存在: {daily_id}")

    results = []
    correct_count = 0
    wrong_count = 0

    for ans in answers:
        qid = ans.get("question_id", "")
        user_answer = ans.get("user_answer", "").strip().upper()
        q = _find_question_in_package(package, qid)
        if not q:
            results.append({
                "question_id": qid,
                "correct_answer": "",
                "user_answer": user_answer,
                "is_correct": False,
                "error_path": None,
                "explanation": "题目不在本次练习包中",
            })
            wrong_count += 1
            continue

        correct_answer = q.get("answer", "").strip().upper()
        is_correct = user_answer == correct_answer

        error_path = None
        if not is_correct and user_answer:
            distractors = q.get("distractors", {})
            dist = distractors.get(user_answer)
            if dist:
                error_path = {
                    "type": dist.get("type", "未知错误"),
                    "error_formula": dist.get("error_formula", ""),
                    "correct_formula": package.get("formula", ""),
                }
            else:
                error_path = {
                    "type": "其他错误",
                    "error_formula": "",
                    "correct_formula": package.get("formula", ""),
                }

        if is_correct:
            correct_count += 1
        else:
            wrong_count += 1

        results.append({
            "question_id": qid,
            "correct_answer": correct_answer,
            "user_answer": user_answer,
            "is_correct": is_correct,
            "error_path": error_path,
            "explanation": q.get("explanation", ""),
        })

    submission = {
        "daily_id": daily_id,
        "total": len(answers),
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "results": results,
    }
    _submission_cache[daily_id] = submission

    # ── 持久化作答记录（P3 学习反馈数据源）──
    if db is not None:
        _persist_answers(db, daily_id, user_id, source, results)

    return submission


def _persist_answers(
    db: Session,
    daily_id: str,
    user_id: str,
    source: str,
    results: list[dict[str, Any]],
) -> None:
    """将提交结果逐题写入 practice_answers 表。"""
    from app.models import PracticeAnswer

    for r in results:
        record = PracticeAnswer(
            user_id=user_id,
            question_id=r["question_id"],
            daily_id=daily_id,
            user_answer=r.get("user_answer", ""),
            correct_answer=r.get("correct_answer", ""),
            is_correct=bool(r.get("is_correct", False)),
            time_spent_ms=0,
            source=source,
        )
        db.add(record)
    db.commit()


def get_review_card(daily_id: str) -> dict[str, Any]:
    """获取错因复习卡：汇总错误路径类型 + 错题列表。"""
    submission = _submission_cache.get(daily_id)
    if not submission:
        raise ValueError(f"未找到提交记录: {daily_id}")

    package = _package_cache.get(daily_id)

    # 汇总错误路径
    error_path_counts: dict[str, dict[str, Any]] = {}
    wrong_questions = []

    for r in submission["results"]:
        if r["is_correct"]:
            continue
        ep = r.get("error_path")
        if ep:
            etype = ep["type"]
            if etype not in error_path_counts:
                error_path_counts[etype] = {
                    "type": etype,
                    "count": 0,
                    "correct_formula": ep.get("correct_formula", ""),
                    "error_formula": ep.get("error_formula", ""),
                }
            error_path_counts[etype]["count"] += 1

        # 查找错题详情
        q_detail = None
        if package:
            q_detail = _find_question_in_package(package, r["question_id"])
        wrong_questions.append({
            "question_id": r["question_id"],
            "user_answer": r["user_answer"],
            "correct_answer": r["correct_answer"],
            "error_path": r.get("error_path"),
            "stem": q_detail.get("stem", "") if q_detail else "",
            "options": q_detail.get("options", {}) if q_detail else {},
            "explanation": r.get("explanation", ""),
        })

    # 按次数降序
    error_paths = sorted(error_path_counts.values(), key=lambda x: -x["count"])

    return {
        "daily_id": daily_id,
        "total": submission["total"],
        "correct_count": submission["correct_count"],
        "wrong_count": submission["wrong_count"],
        "error_paths": error_paths,
        "review_questions": wrong_questions,
    }


def list_skills() -> list[dict[str, str]]:
    """列出 6 种技能。"""
    return [
        {"skill": k, "name": v["name"], "formula": v["formula"]}
        for k, v in SKILL_DEFS.items()
    ]
