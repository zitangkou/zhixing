"""题目入库辅助"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import Article, Question, gen_id
from app.services.serializers import encode_correct_answer, generate_questions_for_article


def add_generated_questions(
    db: Session,
    article: Article,
    *,
    pending: bool = False,
    origin: str = "crawl_auto",
) -> int:
    status = "pending" if pending else "approved"
    count = 0
    for qdata in generate_questions_for_article(article):
        db.add(
            Question(
                id=gen_id("q"),
                article_id=article.id,
                type=qdata["type"],
                stem=qdata["stem"],
                options=json.dumps(qdata.get("options", []), ensure_ascii=False),
                correct_answer=encode_correct_answer(qdata["correct_answer"]),
                analysis=qdata["analysis"],
                source_sentence=qdata.get("source_sentence", ""),
                status=status,
                origin=origin,
                is_active=not pending,
            )
        )
        count += 1
    return count


def add_ai_questions(
    db: Session,
    article: Article,
    questions: list[dict],
) -> int:
    count = 0
    for qdata in questions:
        db.add(
            Question(
                id=gen_id("q"),
                article_id=article.id,
                type=qdata["type"],
                stem=qdata["stem"],
                options=json.dumps(qdata.get("options", []), ensure_ascii=False),
                correct_answer=encode_correct_answer(qdata["correct_answer"]),
                analysis=qdata["analysis"],
                source_sentence=qdata.get("source_sentence", ""),
                status="pending",
                origin="ai",
                is_active=False,
            )
        )
        count += 1
    return count


def add_imported_questions(
    db: Session,
    article: Article,
    questions: list[dict],
    *,
    pending: bool = True,
) -> int:
    status = "pending" if pending else "approved"
    count = 0
    for qdata in questions:
        db.add(
            Question(
                id=gen_id("q"),
                article_id=article.id,
                type=qdata["type"],
                stem=qdata["stem"],
                options=json.dumps(qdata.get("options", []), ensure_ascii=False),
                correct_answer=encode_correct_answer(qdata["correct_answer"]),
                analysis=qdata["analysis"],
                source_sentence=qdata.get("source_sentence", ""),
                status=status,
                origin="import",
                is_active=not pending,
            )
        )
        count += 1
    return count
