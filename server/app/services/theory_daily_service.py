"""时政学习产品的每日学习包编排。"""

from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Article, DailyLearningTask, Question, gen_id


THEORY_DAILY_STEPS = [
    {"key": "orient", "title": "读前定向", "description": "先看主体、行动与限定条件"},
    {"key": "read", "title": "原文精读", "description": "理解规范表述和知识位置"},
    {"key": "quiz", "title": "证据练习", "description": "每道题都回到原文依据"},
    {"key": "review", "title": "错因回收", "description": "辨清偷换、扩大与程度变化"},
]


def _loads_list(raw: str) -> list:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def ensure_theory_daily_task(db: Session, task_date: str) -> DailyLearningTask | None:
    """只编排至少有3道已审核且具备原文证据的文章。"""
    existing = (
        db.query(DailyLearningTask)
        .filter(
            DailyLearningTask.product_key == "theory",
            DailyLearningTask.task_date == task_date,
            DailyLearningTask.status == "published",
        )
        .order_by(DailyLearningTask.sort_order, DailyLearningTask.created_at)
        .first()
    )
    if existing:
        return existing

    article = (
        db.query(Article)
        .join(Question, Question.article_id == Article.id)
        .filter(
            Article.is_published.is_(True),
            Article.status == "published",
            Article.allow_quiz.is_(True),
            Article.publish_date <= task_date,
            Question.is_active.is_(True),
            Question.status == "approved",
            Question.source_sentence != "",
        )
        .group_by(Article.id)
        .having(func.count(Question.id) >= 3)
        .order_by(
            Article.is_daily.desc(),
            Article.importance.desc(),
            Article.publish_date.desc(),
            Article.created_at.desc(),
        )
        .first()
    )
    if not article:
        return None

    questions = (
        db.query(Question)
        .filter(
            Question.article_id == article.id,
            Question.is_active.is_(True),
            Question.status == "approved",
            Question.source_sentence != "",
        )
        .order_by(Question.created_at, Question.id)
        .all()
    )
    tags = [str(item).strip() for item in _loads_list(article.tags) if str(item).strip()]
    task = DailyLearningTask(
        id=gen_id("dlt"),
        product_key="theory",
        task_date=task_date,
        task_type="theory_daily_pack",
        title=article.title,
        description=article.summary or "理解一个时政主题，用原文依据辨清易混表述",
        content_type="article",
        content_id=article.id,
        estimated_minutes=15,
        total_steps=len(THEORY_DAILY_STEPS),
        sort_order=0,
        status="published",
        metadata_json=json.dumps(
            {
                "source": article.source,
                "publishDate": article.publish_date,
                "focuses": tags[:3],
                "questionCount": len(questions),
                "evidenceCount": sum(bool(question.source_sentence.strip()) for question in questions),
                "steps": THEORY_DAILY_STEPS,
            },
            ensure_ascii=False,
        ),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
