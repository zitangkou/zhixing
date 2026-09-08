"""AI 生成题目的格式与质量校验"""

from __future__ import annotations

import re
from typing import Any

_LOW_QUALITY_PATTERNS = (
    re.compile(r"_{3,}"),  # ______ 挖空
    re.compile(r"（单选）[^（]*_{3,}"),
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _in_corpus(sentence: str, corpus: str) -> bool:
    if not sentence or not corpus:
        return False
    if sentence in corpus:
        return True
    ns, nc = _normalize(sentence), _normalize(corpus)
    if len(ns) < 8:
        return ns in nc
    head = ns[: min(20, len(ns))]
    return head in nc if len(head) >= 8 else ns in nc


def _is_low_quality_stem(stem: str, qtype: str) -> str | None:
    if qtype in ("single", "multiple"):
        for pat in _LOW_QUALITY_PATTERNS:
            if pat.search(stem):
                return "禁止使用 ______ 简单挖空，请用（ ）填空或完整问句"
    if qtype == "single" and len(stem) < 12:
        return "单选题干过短，请使用完整公考表述"
    return None


def validate_question(q: dict[str, Any], corpus: str) -> list[str]:
    errors: list[str] = []
    qtype = q.get("type")
    stem = (q.get("stem") or "").strip()
    options = q.get("options") or []
    correct = q.get("correct_answer")
    analysis = (q.get("analysis") or "").strip()
    source = (q.get("source_sentence") or "").strip()

    if qtype not in ("single", "multiple", "judge"):
        errors.append(f"无效题型: {qtype}")
        return errors

    low = _is_low_quality_stem(stem, qtype)
    if low:
        errors.append(low)

    if len(stem) < 6:
        errors.append("题干过短")
    if not analysis:
        errors.append("缺少解析")
    if not source:
        errors.append("缺少 source_sentence")
    elif not _in_corpus(source, corpus):
        errors.append("source_sentence 不在原文范围内")

    if qtype == "judge":
        if options != ["正确", "错误"]:
            errors.append("判断题选项必须为 [正确, 错误]")
        if correct not in ("正确", "错误"):
            errors.append("判断题答案必须为 正确 或 错误")
        return errors

    if not isinstance(options, list) or len(options) != 4:
        errors.append("选择题必须 4 个选项")
        return errors
    if len(set(options)) != 4:
        errors.append("选项不能重复")

    if qtype == "single":
        if not isinstance(correct, str) or correct not in options:
            errors.append("单选答案必须是选项之一")
    elif qtype == "multiple":
        if not isinstance(correct, list):
            errors.append("多选答案必须是数组")
        else:
            if not (2 <= len(correct) <= 4):
                errors.append("多选应有 2-4 个正确答案")
            for c in correct:
                if c not in options:
                    errors.append(f"多选答案「{c}」不在选项中")
            if len(set(correct)) != len(correct):
                errors.append("多选答案不能重复")

    return errors


def validate_batch(
    questions: list[dict[str, Any]],
    corpus: str,
    *,
    single: int,
    multiple: int,
    judge: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    valid: list[dict[str, Any]] = []
    all_errors: list[str] = []
    counts = {"single": 0, "multiple": 0, "judge": 0}
    seen_stems: set[str] = set()

    for i, q in enumerate(questions):
        errs = validate_question(q, corpus)
        stem = (q.get("stem") or "").strip()
        if stem in seen_stems:
            errs.append("题干重复")
        if errs:
            all_errors.append(f"第{i + 1}题: {'; '.join(errs)}")
            continue
        seen_stems.add(stem)
        counts[q["type"]] += 1
        valid.append(q)

    for t, expected in [("single", single), ("multiple", multiple), ("judge", judge)]:
        if counts[t] != expected:
            all_errors.append(f"{t} 数量应为 {expected}，实际 {counts[t]}")

    return valid, all_errors
