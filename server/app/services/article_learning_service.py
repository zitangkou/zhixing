"""Public, read-only article practice. No account, points or wrong-answer writes."""

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Article, Question
from app.services.serializers import article_to_out, question_to_out
from app.services.user_service import check_answer
from app.services.theory_learning_entry_service import get_public_entry


def load_learning_bundle(db: Session, article_id: str):
    entry, parts = get_public_entry(db, article_id)
    article = db.get(Article, article_id)
    if not article or not article.is_published or article.status != "published":
        raise HTTPException(404, "文章已下线或不存在")
    if not article.allow_quiz:
        raise HTTPException(404, "文章暂未开放练习")
    active_rows = db.query(Question).filter(
        Question.article_id == article_id,
        Question.is_active.is_(True),
    ).order_by(Question.created_at, Question.id).all()
    rows = [row for row in active_rows if row.status == "approved"]
    # Fail closed: unsupported/incomplete teaching data must not enter a public unit.
    ready = []
    for row in rows:
        out = question_to_out(row).model_dump()
        options = out.get("options") or []
        answer = out["correctAnswer"]
        answers = answer if isinstance(answer, list) else [answer]
        if (row.type in ("single", "multiple", "judge") and row.stem.strip()
                and row.analysis.strip() and row.source_sentence.strip()
                and len(options) >= 2 and len(set(options)) == len(options)
                and answers and all(a in options for a in answers)
                and len(set(answers)) == len(answers)
                and (len(answers) >= 2 if row.type == "multiple" else len(answers) == 1)):
            ready.append((row, out))
    ready_by_id = {row.id: (row, out) for row, out in ready}
    configured_ids = [question_id for part in parts for question_id in part["questionIds"]]
    ready = [ready_by_id[question_id] for question_id in configured_ids if question_id in ready_by_id]
    article_data = article_to_out(article).model_dump()
    fingerprint = json.dumps(
        [{key: article_data[key] for key in ("id", "title", "source", "publishDate", "summary", "content", "sections")},
         [out for _, out in ready], parts, entry.collection_enabled], ensure_ascii=False, sort_keys=True,
    ).encode()
    revision = hashlib.sha256(fingerprint).hexdigest()
    return article_data, ready, revision, entry.collection_enabled, parts


def get_learning_bundle(db: Session, article_id: str):
    article, ready, revision, complete, parts = load_learning_bundle(db, article_id)
    questions = [
        {key: out[key] for key in ("id", "articleId", "type", "stem", "options")}
        for _, out in ready
    ]
    return {
        "article": article, "revision": revision, "questions": questions,
        "collectionComplete": complete,
        "parts": parts,
    }


def check_learning_answer(db: Session, article_id: str, revision: str, question_id: str, answer):
    _, ready, current_revision, _, _ = load_learning_bundle(db, article_id)
    if revision != current_revision:
        raise HTTPException(409, "内容已更新，请重新打开学习内容；旧记录仍保留在本机")
    pair = next((pair for pair in ready if pair[0].id == question_id), None)
    if not pair:
        raise HTTPException(404, "题目不属于当前学习内容")
    row, out = pair
    values = answer if isinstance(answer, list) else [answer]
    if (not values or len(set(values)) != len(values)
            or any(value not in out["options"] for value in values)
            or (row.type != "multiple" and len(values) != 1)
            or (row.type == "multiple" and len(values) < 2)):
        raise HTTPException(422, "请选择有效的答案选项")
    normalized = values if row.type == "multiple" else values[0]
    return {
        "correct": check_answer(row, normalized), "correctAnswer": out["correctAnswer"],
        "analysis": out["analysis"], "sourceSentence": out["sourceSentence"],
        "pointsEarned": 0,
    }
