"""真题批量导入：支持 Markdown / JSON / CSV 三种格式

所有格式最终统一解析成 list[dict]，每条形如：
{
  "section": "言语理解",
  "section_index": 1,
  "type": "single",
  "material": "可选共享材料",
  "stem": "题干",
  "options": ["A选项", "B选项", "C选项", "D选项"],
  "correct_answer": "A选项"  或  ["A选项", "C选项"]
  "analysis": "解析",
  "difficulty": 3,
  "knowledge_tags": ["言语-概括归纳"]
}

格式说明：
- Markdown：友好手写格式，## 模块，### 题号，A. 选项，> 答案：B，> 解析：...
- JSON：[{...}, ...]，字段同上
- CSV：每行一题，列：section,stem,type,A,B,C,D,answer,analysis,difficulty,knowledge_tags
"""
from __future__ import annotations

import csv
import io
import json
import re
from typing import Any

_OPTION_RE = re.compile(r"^([A-D])[．.、]\s*(.+)$")
_MD_ANSWER_RE = re.compile(r"^>\s*\*\*答案[：:]\s*(.+?)\*\*\s*$")
_MD_ANSWER_ALT_RE = re.compile(r"^>\s*\*\*答案[：:]\*\*\s*(.+?)(?:\*\*)?\s*$")
_MD_ANALYSIS_RE = re.compile(r"^>\s*\*\*解析[：:]\s*(.+?)\*\*\s*$")
_MD_ANALYSIS_ALT_RE = re.compile(r"^>\s*\*\*解析[：:]?\*\*[：:]?\s*(.+?)(?:\*\*)?\s*$")
_MD_KNOWLEDGE_RE = re.compile(r"^>\s*\*\*知识点[：:]\s*(.+?)\*\*\s*$")
_MD_KNOWLEDGE_ALT_RE = re.compile(r"^>\s*\*\*知识点[：:]?\*\*[：:]?\s*(.+?)(?:\*\*)?\s*$")
_MD_DIFF_RE = re.compile(r"^>\s*\*\*难度[：:]\s*(\d)\*\*\s*$")
_MD_SECTION_RE = re.compile(r"^##\s+(.+)$")
_MD_QNUM_RE = re.compile(r"^###\s*(\d+)\s*$")
_MD_MATERIAL_RE = re.compile(r"^>\s*\*\*材料[：:]?\*\*[：:]?\s*(.+?)(?:\*\*)?\s*$", re.S)
_MD_MATERIAL_BLOCK_RE = re.compile(r"^>\s*\*\*材料[：:]?\*\*\s*$")


def _resolve_answer_letter(raw: str, options: list[str], qtype: str) -> str | list[str] | None:
    """'B' / 'AB' / 'A、C' -> 对应选项文本"""
    raw = raw.strip()
    if not raw:
        return None
    letters = re.sub(r"[^A-D]", "", raw.upper())
    if letters and len(letters) == len(raw.replace(" ", "").replace(",", "").replace("、", "")):
        idx_map = {chr(65 + i): options[i] for i in range(min(len(options), 4))}
        picked = [idx_map[c] for c in letters if c in idx_map]
        if qtype == "multiple":
            return picked if len(picked) >= 2 else None
        return picked[0] if len(picked) == 1 else None
    # 直接是选项文本
    if qtype == "multiple":
        parts = [p.strip() for p in re.split(r"[,，、]", raw) if p.strip()]
        if len(parts) >= 2 and all(p in options for p in parts):
            return parts
        return None
    if raw in options:
        return raw
    return None


# ===== Markdown =====


def parse_markdown(text: str) -> tuple[list[dict], list[str]]:
    """解析真题 Markdown

    结构：
    # 2024 国考行测地市级  （文档标题，忽略，试卷元信息由表单填）

    ## 常识判断

    ### 1
    某题干，可多行
    A. 选项A
    B. 选项B
    C. 选项C
    D. 选项D
    > **答案：B**
    > **解析：因为...**

    ### 2
    ...

    ## 言语理解
    ...

    材料题（资料分析/逻辑）：
    ### 21
    > **材料**
    > 某段共享材料，可多行
    根据材料回答...
    A. ...
    > **答案：C**
    """
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return [], ["内容为空"]

    questions: list[dict] = []
    errors: list[str] = []
    current_section = ""
    current_q_section = ""  # 当前题所属模块（题进入时锁定）
    current_material = ""
    current_block: list[str] = []
    current_qnum = 0
    in_material = False
    material_lines: list[str] = []

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # 模块标题
        sec_m = _MD_SECTION_RE.match(line)
        if sec_m:
            current_section = sec_m.group(1).strip()
            i += 1
            continue

        # 题号
        qnum_m = _MD_QNUM_RE.match(line)
        if qnum_m:
            # 保存前一个题（用题自己的 section）
            if current_block:
                q, err = _parse_md_block(current_block, current_q_section, current_qnum, current_material)
                if err:
                    errors.append(err)
                elif q:
                    questions.append(q)
            current_qnum = int(qnum_m.group(1))
            current_q_section = current_section  # 锁定当前题的 section
            current_block = []
            current_material = ""
            i += 1
            continue

        # 材料块开始（多行）
        if _MD_MATERIAL_BLOCK_RE.match(line):
            in_material = True
            material_lines = []
            i += 1
            continue
        if in_material:
            if line.startswith(">"):
                material_lines.append(line.lstrip("> ").rstrip())
                i += 1
                continue
            else:
                current_material = "\n".join(s for s in material_lines if s.strip())
                in_material = False
                # 不 continue，让本行走 normal 流程

        # 单行材料
        mat_m = _MD_MATERIAL_RE.match(line)
        if mat_m:
            current_material = mat_m.group(1).strip()
            i += 1
            continue

        # 收集当前题的所有行
        if current_qnum > 0:
            current_block.append(line)
        i += 1

    # 最后一个题
    if current_block:
        q, err = _parse_md_block(current_block, current_q_section, current_qnum, current_material)
        if err:
            errors.append(err)
        elif q:
            questions.append(q)

    if not questions and not errors:
        errors.append("未识别到任何题目，请检查 Markdown 格式")
    return questions, errors


def _parse_md_block(block: list[str], section: str, qnum: int, material: str) -> tuple[dict | None, str | None]:
    lines = [ln for ln in block if ln.strip()]
    if not lines:
        return None, None

    options: list[str] = []
    stem_lines: list[str] = []
    answer_raw = ""
    analysis = ""
    knowledge = ""
    difficulty = 3
    qtype = "single"

    for line in lines:
        opt_m = _OPTION_RE.match(line)
        if opt_m:
            options.append(opt_m.group(2).strip())
            continue
        ans_m = _MD_ANSWER_RE.match(line) or _MD_ANSWER_ALT_RE.match(line)
        if ans_m:
            answer_raw = ans_m.group(1).strip()
            continue
        ana_m = _MD_ANALYSIS_RE.match(line) or _MD_ANALYSIS_ALT_RE.match(line)
        if ana_m:
            analysis = ana_m.group(1).strip()
            continue
        know_m = _MD_KNOWLEDGE_RE.match(line) or _MD_KNOWLEDGE_ALT_RE.match(line)
        if know_m:
            knowledge = know_m.group(1).strip()
            continue
        diff_m = _MD_DIFF_RE.match(line)
        if diff_m:
            try:
                difficulty = int(diff_m.group(1))
            except ValueError:
                pass
            continue
        # 其他行算作题干
        if not line.startswith(">"):
            stem_lines.append(line)

    stem = "\n".join(s for s in stem_lines if s.strip()).strip()
    if not stem:
        return None, f"第{qnum}题：题干为空"

    if len(options) == 2 and options == ["正确", "错误"]:
        qtype = "judge"
    elif len(options) < 2:
        return None, f"第{qnum}题：选项不足（{len(options)}个）"

    correct = _resolve_answer_letter(answer_raw, options, qtype)
    if correct is None:
        return None, f"第{qnum}题：无法解析答案「{answer_raw}」"

    return {
        "section": section,
        "section_index": qnum,
        "type": qtype,
        "material": material,
        "stem": stem,
        "options": options if qtype != "judge" else ["正确", "错误"],
        "correct_answer": correct,
        "analysis": analysis,
        "difficulty": difficulty,
        "knowledge_tags": [t.strip() for t in re.split(r"[,，、]", knowledge) if t.strip()] if knowledge else [],
    }, None


# ===== JSON =====


def parse_json(text: str) -> tuple[list[dict], list[str]]:
    """解析 JSON 数组

    字段：section, section_index, type, material, stem, options, correct_answer,
          analysis, difficulty, knowledge_tags
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return [], [f"JSON 解析失败: {e}"]
    if not isinstance(data, list):
        return [], ["JSON 顶层必须是数组"]
    questions: list[dict] = []
    errors: list[str] = []
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            errors.append(f"第{i}条: 不是对象")
            continue
        stem = (item.get("stem") or "").strip()
        if not stem:
            errors.append(f"第{i}条: stem 为空")
            continue
        options = item.get("options", [])
        if not isinstance(options, list) or len(options) < 2:
            errors.append(f"第{i}条: options 不足")
            continue
        correct = item.get("correct_answer") or item.get("correctAnswer")
        if correct is None:
            errors.append(f"第{i}条: correct_answer 缺失")
            continue
        questions.append({
            "section": item.get("section", ""),
            "section_index": int(item.get("section_index", i)),
            "type": item.get("type", "single"),
            "material": item.get("material", ""),
            "stem": stem,
            "options": options,
            "correct_answer": correct,
            "analysis": item.get("analysis", ""),
            "difficulty": int(item.get("difficulty", 3)),
            "knowledge_tags": item.get("knowledge_tags", item.get("knowledgeTags", [])),
        })
    if not questions and not errors:
        errors.append("数组为空")
    return questions, errors


# ===== CSV =====


def parse_csv(text: str) -> tuple[list[dict], list[str]]:
    """解析 CSV

    列：section,stem,type,A,B,C,D,answer,analysis,difficulty,knowledge_tags
    answer 列填字母（B / AC）或选项文本
    knowledge_tags 用 | 或 、 分隔
    """
    questions: list[dict] = []
    errors: list[str] = []
    try:
        reader = csv.DictReader(io.StringIO(text))
    except Exception as e:
        return [], [f"CSV 解析失败: {e}"]
    if not reader.fieldnames:
        return [], ["CSV 缺表头"]
    fields = {f.strip().lower() for f in reader.fieldnames}
    if "stem" not in fields:
        return [], ["CSV 缺 stem 列"]

    for i, row in enumerate(reader, start=2):  # 行号从2开始（1是表头）
        stem = (row.get("stem") or "").strip()
        if not stem:
            continue
        # 选项支持 A/B/C/D 列，也支持 options 列（用 | 分隔）
        options: list[str] = []
        if "options" in row and row.get("options"):
            options = [o.strip() for o in re.split(r"[|｜]", row["options"]) if o.strip()]
        else:
            for letter in ("A", "B", "C", "D", "E"):
                v = (row.get(letter) or "").strip()
                if v:
                    options.append(v)
        if len(options) < 2:
            errors.append(f"第{i}行: 选项不足")
            continue
        qtype = (row.get("type") or "single").strip()
        if qtype == "判断" or (len(options) == 2 and {o for o in options} == {"正确", "错误"}):
            qtype = "judge"
            options = ["正确", "错误"]
        answer_raw = (row.get("answer") or "").strip()
        correct = _resolve_answer_letter(answer_raw, options, qtype)
        if correct is None:
            errors.append(f"第{i}行: 答案「{answer_raw}」无法解析")
            continue
        knowledge_raw = (row.get("knowledge_tags") or row.get("knowledgeTags") or "").strip()
        try:
            difficulty = int(row.get("difficulty") or 3)
        except ValueError:
            difficulty = 3
        questions.append({
            "section": (row.get("section") or "").strip(),
            "section_index": i - 1,
            "type": qtype,
            "material": (row.get("material") or "").strip(),
            "stem": stem,
            "options": options,
            "correct_answer": correct,
            "analysis": (row.get("analysis") or "").strip(),
            "difficulty": difficulty,
            "knowledge_tags": [t.strip() for t in re.split(r"[|｜、]", knowledge_raw) if t.strip()] if knowledge_raw else [],
        })
    if not questions and not errors:
        errors.append("未识别到题目")
    return questions, errors


# ===== 统一入口 =====


def parse_import(file_name: str, text: str) -> tuple[list[dict], list[str]]:
    """根据文件名后缀选择解析器"""
    name = file_name.lower()
    if name.endswith(".json"):
        return parse_json(text)
    if name.endswith(".csv"):
        return parse_csv(text)
    # 默认 markdown（.md / .txt）
    return parse_markdown(text)
