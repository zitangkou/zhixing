"""基于 LLM 的 AI 出题流水线（两阶段：提取要点 → 命制题目）"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models import Article
from app.services.ai.llm_client import LlmError, chat_json
from app.services.ai.section_extract import extract_sections_text, flatten_source_corpus, list_chapter_section_ids
from app.services.ai.validators import validate_batch
from app.services.question_factory import add_ai_questions
from app.services.serializers import parse_json

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"
RUBRIC_PATH = PROMPTS_DIR / "shiwuwu-question-rubric.md"
EXAMPLES_PATH = PROMPTS_DIR / "shiwuwu-question-examples.md"

DEFAULT_SECTION_IDS = ["ch1", "ch2", "ch3", "ch4", "ch5"]

KEY_POINTS_SYSTEM = """你是公务员考试政治理论教研专家。
任务：从《建议》原文中提取可出题要点，输出合法 JSON，不要 markdown 代码块。"""

GENERATE_SYSTEM = """你是公务员考试政治理论命题专家。
任务：模仿高质量公考样题风格命制试题，严格依据给定要点与原文，不得编造。
输出合法 JSON，不要 markdown 代码块。"""


def _load_prompt_file(path: Path, fallback: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def _load_rubric() -> str:
    return _load_prompt_file(RUBRIC_PATH, "按公考政治题标准出题。")


def _load_examples() -> str:
    return _load_prompt_file(EXAMPLES_PATH, "")


def _extract_key_points(article_title: str, source_text: str, min_count: int) -> list[dict[str, Any]]:
    prompt = f"""# 文章
{article_title}

# 原文
{source_text}

# 任务
提取至少 {min_count} 个可出题要点，覆盖不同章节与类型。

# 要点类型 category（必填其一）
定位表述、指导术语、原文原话、并列要点、具体举措、不包括素材、困难挑战、判断素材、常识结合

# 输出 JSON
{{
  "key_points": [
    {{
      "category": "定位表述",
      "topic": "现代化产业体系定位",
      "quote": "原文精确摘录30-150字",
      "section_hint": "章节标题关键词"
    }}
  ]
}}

要求：
- quote 必须来自上方原文，可逐字摘录
- 并列要点、不包括素材类需标注多个并列项
- 不要输出题目，只输出要点
"""
    result = chat_json(KEY_POINTS_SYSTEM, prompt)
    points = result.get("key_points") or []
    if not isinstance(points, list) or len(points) < min(min_count, 3):
        raise LlmError("要点提取不足，请缩小章节范围或重试")
    return points


def _build_generate_prompt(
    article_title: str,
    key_points: list[dict[str, Any]],
    corpus_excerpt: str,
    *,
    single: int,
    multiple: int,
    judge: int,
) -> str:
    rubric = _load_rubric()
    examples = _load_examples()
    points_json = json.dumps(key_points, ensure_ascii=False, indent=2)
    return f"""# 文章
{article_title}

# 高质量样题（请模仿风格、难度、干扰项设计，勿照抄）
{examples}

# 出题规范
{rubric}

# 已提取要点（每题必须对应其中一个要点的 quote）
{points_json}

# 原文摘录（校验 source_sentence 用，约前8000字）
{corpus_excerpt[:8000]}

# 任务
生成共 {single + multiple + judge} 道题：
- 单选题 {single} 道（type=single）
- 多选题 {multiple} 道（type=multiple，2-4个正确答案）
- 判断题 {judge} 道（type=judge）

# 硬性要求
1. 题干以《建议》开头或明确考查本文，填空用（ ），禁止 ______ 挖空
2. 单选/多选 options 共4项，不含 A/B/C/D 前缀
3. 判断题 options 固定 ["正确","错误"]
4. source_sentence 必须能在原文摘录中找到
5. 考点不重复，干扰项与正确项语义接近
6. 多选题需含至少1道「陷阱型」（2-3个正确+1个易错项）和1道「并列全选型」

# 输出 JSON
{{
  "questions": [
    {{
      "type": "single|multiple|judge",
      "stem": "题干",
      "options": ["选项1","选项2","选项3","选项4"],
      "correct_answer": "字符串或字符串数组",
      "analysis": "解析，多选需说明陷阱项",
      "source_sentence": "原文依据"
    }}
  ]
}}
"""


def generate_questions_payload(
    article: Article,
    *,
    section_ids: list[str] | None = None,
    single: int = 8,
    multiple: int = 4,
    judge: int = 2,
) -> tuple[list[dict[str, Any]], list[str]]:
    section_ids = section_ids or DEFAULT_SECTION_IDS
    sections = parse_json(article.sections or "[]", [])
    if not sections:
        raise LlmError("文章无 sections 结构，无法 AI 出题")

    source_text = extract_sections_text(sections, section_ids)
    if len(source_text) < 100:
        raise LlmError(f"指定章节 {section_ids} 文本过短，请检查 section id")

    corpus = flatten_source_corpus(sections, section_ids)
    total = single + multiple + judge
    min_points = max(total, 8)

    key_points = _extract_key_points(article.title, source_text, min_points)
    user_prompt = _build_generate_prompt(
        article.title,
        key_points,
        corpus,
        single=single,
        multiple=multiple,
        judge=judge,
    )

    result = chat_json(GENERATE_SYSTEM, user_prompt)
    raw_questions = result.get("questions") or []
    if not isinstance(raw_questions, list):
        raise LlmError("LLM 返回缺少 questions 数组")

    valid, errors = validate_batch(
        raw_questions,
        corpus,
        single=single,
        multiple=multiple,
        judge=judge,
    )

    # 数量不足时带校验反馈重试一次
    if len(valid) < total and errors:
        retry_prompt = user_prompt + f"\n\n# 上次校验失败，请修正后重新输出全部 {total} 题\n" + "\n".join(errors[:12])
        retry = chat_json(GENERATE_SYSTEM, retry_prompt)
        retry_questions = retry.get("questions") or []
        if isinstance(retry_questions, list):
            valid, errors = validate_batch(
                retry_questions,
                corpus,
                single=single,
                multiple=multiple,
                judge=judge,
            )

    return valid, errors


def run_ai_question_generation(
    db: Session,
    article: Article,
    *,
    section_ids: list[str] | None = None,
    single: int = 8,
    multiple: int = 4,
    judge: int = 2,
) -> dict[str, Any]:
    if section_ids is None and article.is_featured:
        all_ids = list_chapter_section_ids(parse_json(article.sections or "[]", []))
        section_ids = all_ids if all_ids else DEFAULT_SECTION_IDS

    questions, validation_errors = generate_questions_payload(
        article,
        section_ids=section_ids,
        single=single,
        multiple=multiple,
        judge=judge,
    )
    if not questions:
        msg = "无有效题目"
        if validation_errors:
            msg += "：" + "；".join(validation_errors[:5])
        raise LlmError(msg)

    count = add_ai_questions(db, article, questions)
    db.commit()
    return {
        "count": count,
        "validation_warnings": validation_errors,
        "section_ids": section_ids or DEFAULT_SECTION_IDS,
        "breakdown": {
            "single": single,
            "multiple": multiple,
            "judge": judge,
        },
    }
