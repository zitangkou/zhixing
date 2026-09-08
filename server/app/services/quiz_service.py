from __future__ import annotations

import random
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Article, Question
from app.timezone import now


def _quiz_base_query(db: Session, category_id: str | None = None, min_importance: int | None = None):
    q = (
        db.query(Question)
        .join(Article, Question.article_id == Article.id)
        .filter(
            Question.is_active.is_(True),
            Question.status == "approved",
            Article.is_published.is_(True),
            Article.status == "published",
            Article.allow_quiz.is_(True),
        )
    )
    if category_id:
        q = q.filter(Article.category_id == category_id)
    if min_importance:
        q = q.filter(Article.importance >= min_importance)
    return q


def pick_questions(db: Session, count: int = 10, category_id: str | None = None, min_importance: int | None = None) -> list[Question]:
    rows = _quiz_base_query(db, category_id, min_importance).all()
    if not rows:
        return []
    if len(rows) <= count:
        random.shuffle(rows)
        return rows
    return random.sample(rows, count)


def pick_timeline_questions(db: Session, count: int = 10, days: int = 14) -> list[Question]:
    cutoff = (now() - timedelta(days=days)).strftime("%Y-%m-%d")
    articles = (
        db.query(Article)
        .filter(
            Article.is_published.is_(True),
            Article.status == "published",
            Article.allow_quiz.is_(True),
            Article.publish_date >= cutoff,
        )
        .order_by(Article.publish_date.desc(), Article.created_at.desc())
        .limit(max(count * 2, 10))
        .all()
    )
    article_ids = [a.id for a in articles]
    if not article_ids:
        return pick_questions(db, count)
    rows = (
        db.query(Question)
        .filter(
            Question.article_id.in_(article_ids),
            Question.is_active.is_(True),
            Question.status == "approved",
        )
        .all()
    )
    if not rows:
        return []
    if len(rows) <= count:
        random.shuffle(rows)
        return rows
    return random.sample(rows, count)
