import json
import random
import re
from typing import Any

from app.constants import IMPORTANCE_LABELS
from app.models import Article, Question
from app.schemas import ArticleOut, ArticleSection, MindMapNode, QuestionOut
from app.services.section_parser import build_sections_from_content, sections_to_content

POLITICAL_KEYWORDS = [
    "两个确立", "两个维护", "新质生产力", "中国式现代化",
    "根本保证", "核心", "本质", "根本立场", "最大优势", "必由之路",
    "根本方向", "根本任务", "鲜明特色", "本质要求", "战略支撑", "根本遵循",
]

DISTRACTORS: dict[str, list[str]] = {
    "根本保证": ["基本前提", "重要保障", "有力支撑", "必然要求"],
    "核心": ["关键", "重点", "中心", "枢纽"],
    "本质": ["实质", "本性", "实质内涵", "根本属性"],
}


def parse_json(value: str, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except json.JSONDecodeError:
        return default


def encode_correct_answer(value: str | list[str]) -> str:
    """JSON 编码答案，避免纯数字字符串入库后被 json.loads 解析为 int/float。"""
    return json.dumps(value, ensure_ascii=False)


def parse_correct_answer(value: str) -> str | list[str]:
    """解析题目正确答案，统一为 str 或 list[str]。"""
    if not value:
        return ""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    if isinstance(parsed, (int, float)):
        return str(parsed)
    if isinstance(parsed, str):
        return parsed
    return str(parsed)


def article_to_out(article: Article) -> ArticleOut:
    mind_raw = parse_json(article.mind_map, None)
    if not isinstance(mind_raw, dict) or not mind_raw.get("id") or not mind_raw.get("title"):
        mind_raw = {"id": "root", "title": article.title, "children": []}
    sections_raw = parse_json(getattr(article, "sections", "[]") or "[]", [])
    if not sections_raw and article.content:
        from app.services.section_parser import build_sections_from_content

        sections_raw = build_sections_from_content(article.title, article.content)

    sections = [ArticleSection.model_validate(s) for s in sections_raw]
    content = article.content or sections_to_content(sections_raw)
    cat_path = parse_json(getattr(article, "category_path", "[]") or "[]", [])
    importance = int(getattr(article, "importance", 3) or 3)

    return ArticleOut(
        id=article.id,
        title=article.title,
        source=article.source,
        publishDate=article.publish_date,
        summary=article.summary,
        sections=sections,
        content=content,
        tags=parse_json(article.tags, []),
        mindMap=MindMapNode.model_validate(mind_raw),
        readCount=article.read_count,
        isFeatured=bool(getattr(article, "is_featured", False)),
        categoryId=getattr(article, "category_id", None),
        categoryName=cat_path[-1] if cat_path else None,
        categoryPath=cat_path,
        importance=importance,
        importanceLabel=IMPORTANCE_LABELS.get(importance, "掌握"),
        status=getattr(article, "status", "published") or "published",
        allowQuiz=bool(getattr(article, "allow_quiz", True)),
        isDaily=bool(getattr(article, "is_daily", False)),
    )


def question_to_out(q: Question) -> QuestionOut:
    options = parse_json(q.options, [])
    if isinstance(options, list):
        options = [str(o) for o in options]
    correct = parse_correct_answer(q.correct_answer or "")
    return QuestionOut(
        id=q.id,
        articleId=q.article_id,
        type=q.type,
        stem=q.stem,
        options=options if options else None,
        correctAnswer=correct,
        analysis=q.analysis,
        sourceSentence=q.source_sentence,
        status=getattr(q, "status", "approved") or "approved",
        origin=getattr(q, "origin", "manual") or "manual",
        isActive=bool(q.is_active),
    )


def build_mind_map(title: str, content: str) -> dict[str, Any]:
    sentences = [s.strip() + "。" for s in re.split(r"[。！？\n]+", content) if len(s.strip()) > 12]
    children = []
    for i, s in enumerate(sentences[:4]):
        children.append({"id": f"m{i+1}", "title": f"要点{i+1}", "content": s[:120]})
    return {"id": "root", "title": title, "children": children}


def generate_questions_for_article(article: Article) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    sentences = [s.strip() + "。" for s in re.split(r"[。！？\n]+", article.content) if len(s.strip()) > 10]
    is_featured = bool(getattr(article, "is_featured", False))
    single_limit = 6 if is_featured else 3
    judge_limit = 4 if is_featured else 2
    max_total = 10 if is_featured else 5

    for sentence in sentences:
        if len(questions) >= single_limit:
            break
        for kw in POLITICAL_KEYWORDS:
            if kw in sentence:
                stem = sentence.replace(kw, "______")
                distractors = DISTRACTORS.get(kw, ["重要基础", "关键环节", "主要矛盾", "中心环节"])
                options = [kw] + distractors[:3]
                random.shuffle(options)
                questions.append({
                    "type": "single",
                    "stem": f"（单选）{stem}",
                    "options": options,
                    "correct_answer": kw,
                    "analysis": f'正确答案为"{kw}"，需准确记忆政治术语。',
                    "source_sentence": sentence,
                })
                break

    for i, sentence in enumerate(sentences[: judge_limit * 3]):
        if len(questions) >= max_total:
            break
        if len([q for q in questions if q["type"] == "judge"]) >= judge_limit:
            break
        is_correct = i % 2 == 0
        if is_correct:
            questions.append({
                "type": "judge",
                "stem": f"（判断）{sentence}",
                "options": ["正确", "错误"],
                "correct_answer": "正确",
                "analysis": "该表述与原文一致。",
                "source_sentence": sentence,
            })
        else:
            wrong = sentence.replace("根本", "基本").replace("核心", "关键")
            questions.append({
                "type": "judge",
                "stem": f"（判断）{wrong}",
                "options": ["正确", "错误"],
                "correct_answer": "错误",
                "analysis": f"该表述与原文不符。正确表述：{sentence}",
                "source_sentence": sentence,
            })

    return questions[:max_total]
