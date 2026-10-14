"""时政要点：在原文上整理重点，已有套题则沿用，否则起草待审模拟题。"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import Article, Question, gen_id
from app.services.ai.llm_client import chat_json

_SYSTEM = """你是公考时政编辑。只根据给定原文输出 JSON，不要编造原文没有的数字。
格式：
{"summary":"一句话结论","terms":["重点词"],"expressions":["可直接使用的量词或对比句"],
 "questions":[{"type":"single","stem":"题干","options":["A","B","C","D"],"answer":"A","analysis":"解析","sourceSentence":"原文原句"}]}
terms 3到7个。expressions 2到4条。若 user 要求 questions 为空数组，不要出题。
题只能是 single 或 judge。judge 的 options 为 ["正确","错误"]，answer 为「正确」或「错误」。"""


def approved_count(db: Session, article_id: str) -> int:
    return (
        db.query(Question)
        .filter(Question.article_id == article_id, Question.status == "approved", Question.is_active.is_(True))
        .count()
    )


def pending_questions(db: Session, article_id: str) -> list[Question]:
    return (
        db.query(Question)
        .filter(Question.article_id == article_id, Question.status == "pending", Question.origin == "ai")
        .order_by(Question.created_at)
        .all()
    )


def _brief_from(raw: dict) -> dict:
    terms = [str(x).strip() for x in (raw.get("terms") or []) if str(x).strip()]
    expressions = [str(x).strip() for x in (raw.get("expressions") or []) if str(x).strip()]
    summary = str(raw.get("summary") or "").strip()
    if not summary:
        raise ValueError("要点缺少结论")
    return {"summary": summary[:400], "terms": terms[:8], "expressions": expressions[:6]}


def save_brief(db: Session, article: Article, brief: dict) -> dict:
    data = _brief_from(brief)
    article.brief_json = json.dumps(data, ensure_ascii=False)
    if article.brief_status != "published":
        article.brief_status = "draft"
    db.commit()
    return data


def publish_brief(db: Session, article: Article) -> None:
    if not (article.brief_json or "").strip():
        raise ValueError("还没有要点")
    article.brief_status = "published"
    db.commit()


def generate(db: Session, article: Article) -> dict[str, Any]:
    text = (article.content or "").strip()
    if not text:
        raise ValueError("文章没有原文，无法整理")
    has_quiz = approved_count(db, article.id) > 0
    user = f"标题：{article.title}\n日期：{article.publish_date}\n原文：\n{text[:8000]}"
    if has_quiz:
        user += "\n这篇文章已有套题。questions 必须是空数组，只整理要点。"
    else:
        user += "\n这篇文章还没有套题。请另出 5 道模拟题，放进 questions。"
    raw = chat_json(_SYSTEM, user)
    brief = save_brief(db, article, raw)
    created = 0
    if not has_quiz:
        for old in pending_questions(db, article.id):
            db.delete(old)
        for item in (raw.get("questions") or [])[:5]:
            if not isinstance(item, dict):
                continue
            qtype = item.get("type") if item.get("type") in {"single", "judge"} else "single"
            options = item.get("options") or []
            if not isinstance(options, list) or len(options) < 2:
                continue
            stem = str(item.get("stem") or "").strip()
            answer = str(item.get("answer") or "").strip()
            if not stem or not answer:
                continue
            db.add(
                Question(
                    id=gen_id("q"),
                    article_id=article.id,
                    type=qtype,
                    stem=stem,
                    options=json.dumps([str(x) for x in options], ensure_ascii=False),
                    correct_answer=json.dumps(answer, ensure_ascii=False),
                    analysis=str(item.get("analysis") or ""),
                    source_sentence=str(item.get("sourceSentence") or ""),
                    status="pending",
                    origin="ai",
                    is_active=False,
                )
            )
            created += 1
        db.commit()
    return {"brief": brief, "reusedQuiz": has_quiz, "draftedQuestions": created}


def approve_question(db: Session, article_id: str, question_id: str) -> bool:
    row = db.get(Question, question_id)
    if not row or row.article_id != article_id or row.origin != "ai":
        return False
    row.status = "approved"
    row.is_active = True
    db.commit()
    return True
