"""从 Markdown 批量导入题目（公考 MD 格式）"""

from __future__ import annotations

import re
from typing import Any

_OPTION_RE = re.compile(r"^([A-D])[．.]\s*(.+)$")
# 标签 **原文依据：** / **解析：** 后内容在加粗外；**答案：B** 答案可在加粗内
# 原文依据支持 **原文依据：** 与 **原文依据**： 两种冒号位置
_ANSWER_RE = re.compile(r"^>\s*\*\*答案[：:]\s*(.+?)\*\*\s*$")
_ANSWER_ALT_RE = re.compile(r"^>\s*\*\*答案[：:]\*\*\s*(.+?)(?:\*\*)?\s*$")
_SOURCE_RE = re.compile(
    r"^>\s*\*\*原文依据[：:]?\*\*[：:]?\s*(.+?)(?:\*\*)?\s*$"
)
_ANALYSIS_RE = re.compile(
    r"^>\s*\*\*解析[：:]?\*\*[：:]?\s*(.+?)(?:\*\*)?\s*$"
)
_TIP_RE = re.compile(
    r"^>\s*\*\*技巧点拨[：:]?\*\*[：:]?\s*(.+?)(?:\*\*)?\s*$"
)
_STEM_RE = re.compile(r"^\*\*(\d+)\.\s*(.+?)\*\*\s*$", re.S)
_QUESTION_SPLIT_RE = re.compile(r"(?=\n\*\*\d+\.)")


def _detect_section_type(text: str) -> str:
    if re.search(r"多选题", text):
        return "multiple"
    if re.search(r"判断题", text):
        return "judge"
    return "single"


def _strip_wrapping_quotes(text: str) -> str:
    text = text.strip()
    for left, right in (
        ("\u201c", "\u201d"),
        ('"', '"'),
        ("「", "」"),
        ("『", "』"),
    ):
        if text.startswith(left) and text.endswith(right) and len(text) > len(left) + len(right):
            return text[len(left) : -len(right)].strip()
    return text


def _resolve_answer(
    raw: str,
    options: list[str],
    qtype: str,
) -> str | list[str] | None:
    raw = raw.strip()
    if not raw:
        return None

    letters = re.sub(r"[^A-D]", "", raw.upper())
    if letters and len(letters) == len(raw.replace(" ", "").replace(",", "").replace("、", "")):
        idx_map = {chr(65 + i): options[i] for i in range(min(4, len(options)))}
        picked = [idx_map[c] for c in letters if c in idx_map]
        if qtype == "multiple":
            return picked if len(picked) >= 2 else None
        return picked[0] if len(picked) == 1 else None

    if qtype == "multiple":
        parts = [p.strip() for p in re.split(r"[,，、]", raw) if p.strip()]
        if len(parts) >= 2 and all(p in options for p in parts):
            return parts
        return None

    if raw in options:
        return raw
    for opt in options:
        if opt.startswith(raw) or raw.startswith(opt):
            return opt
    return None


def _parse_block(block: str, default_type: str) -> tuple[dict[str, Any] | None, str | None]:
    lines = [ln.rstrip() for ln in block.strip().splitlines() if ln.strip()]
    if not lines:
        return None, None

    stem_match = _STEM_RE.match(lines[0])
    if not stem_match:
        return None, None

    qnum = stem_match.group(1)
    stem = stem_match.group(2).strip()

    options: list[str] = []
    answer_raw = ""
    source_sentence = ""
    analysis = ""
    tip = ""

    for line in lines[1:]:
        opt_m = _OPTION_RE.match(line)
        if opt_m:
            options.append(opt_m.group(2).strip())
            continue
        ans_m = _ANSWER_RE.match(line) or _ANSWER_ALT_RE.match(line)
        if ans_m:
            answer_raw = ans_m.group(1).strip()
            continue
        src_m = _SOURCE_RE.match(line)
        if src_m:
            source_sentence = _strip_wrapping_quotes(src_m.group(1).strip())
            continue
        ana_m = _ANALYSIS_RE.match(line)
        if ana_m:
            analysis = ana_m.group(1).strip()
            continue
        tip_m = _TIP_RE.match(line)
        if tip_m:
            tip = tip_m.group(1).strip()
            continue

    qtype = default_type
    if len(options) == 2 and options == ["正确", "错误"]:
        qtype = "judge"

    if qtype != "judge" and len(options) != 4:
        return None, f"第{qnum}题：选项应为4个（当前{len(options)}个）"

    correct = _resolve_answer(answer_raw, options, qtype)
    if correct is None:
        return None, f"第{qnum}题：无法解析答案「{answer_raw}」"

    if not analysis and tip:
        analysis = tip
    elif not analysis and source_sentence:
        analysis = source_sentence
    elif not analysis:
        analysis = "见原文依据。"
    if not source_sentence and qtype != "judge":
        source_sentence = analysis if analysis != "见原文依据。" else ""

    return {
        "type": qtype,
        "stem": stem,
        "options": options if qtype != "judge" else ["正确", "错误"],
        "correct_answer": correct,
        "analysis": analysis,
        "source_sentence": source_sentence,
    }, None


def parse_questions_markdown(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """解析 MD 文档，返回 (题目列表, 错误/警告信息)"""
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return [], ["内容为空"]

    errors: list[str] = []
    questions: list[dict[str, Any]] = []

    sections = re.split(r"(?=^##\s)", text, flags=re.M)
    if len(sections) == 1:
        sections = [text]

    for section in sections:
        section = section.strip()
        if not section:
            continue
        default_type = _detect_section_type(section.split("\n", 1)[0])
        blocks = _QUESTION_SPLIT_RE.split(section)
        for block in blocks:
            block = block.strip()
            if not block.startswith("**"):
                continue
            parsed, err = _parse_block(block, default_type)
            if err:
                errors.append(err)
            elif parsed:
                questions.append(parsed)

    if not questions and not errors:
        errors.append("未识别到任何题目，请检查 Markdown 格式")
    return questions, errors
