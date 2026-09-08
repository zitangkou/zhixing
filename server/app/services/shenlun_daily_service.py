"""申论产品的每日内容编排。"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import DailyLearningTask, RmrbArticle, gen_id


SHENLUN_DAILY_STEPS = [
    {"key": "read", "title": "精读定位", "description": "读懂主题、对象与核心问题"},
    {"key": "analyze", "title": "三刀拆解", "description": "拆骨架、抓规范表达、学句式"},
    {"key": "answer", "title": "小题作答", "description": "围绕材料完成一次短作答"},
    {"key": "deposit", "title": "表达沉淀", "description": "留下一个可迁移表达"},
]


def _article_tags(raw: str) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return [item.strip() for item in (raw or "").split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def ensure_shenlun_daily_task(db: Session, task_date: str) -> DailyLearningTask | None:
    """为当天选择最新已发布时评；已有编排时保持稳定，不随文章列表变化。"""
    existing = (
        db.query(DailyLearningTask)
        .filter(
            DailyLearningTask.product_key == "shenlun",
            DailyLearningTask.task_date == task_date,
            DailyLearningTask.status == "published",
        )
        .order_by(DailyLearningTask.sort_order, DailyLearningTask.created_at)
        .first()
    )
    if existing:
        return existing

    article = (
        db.query(RmrbArticle)
        .filter(
            RmrbArticle.is_published.is_(True),
            RmrbArticle.publish_date <= task_date,
        )
        .order_by(
            RmrbArticle.sort_order.desc(),
            RmrbArticle.publish_date.desc(),
            RmrbArticle.created_at.desc(),
        )
        .first()
    )
    if not article:
        return None

    task = DailyLearningTask(
        id=gen_id("dlt"),
        product_key="shenlun",
        task_date=task_date,
        task_type="shenlun_article_training",
        title=article.title,
        description=article.summary or "精读一篇时评，完成三刀拆解与表达沉淀",
        content_type="rmrb_article",
        content_id=article.id,
        estimated_minutes=15,
        total_steps=len(SHENLUN_DAILY_STEPS),
        sort_order=0,
        status="published",
        metadata_json=json.dumps(
            {
                "source": article.source or "人民时评",
                "publishDate": article.publish_date or "",
                "tags": _article_tags(article.tags),
                "steps": SHENLUN_DAILY_STEPS,
                "question": {
                    "type": "概括练习",
                    "prompt": "请用不超过120字，概括文章关注的核心问题与主要解决思路。",
                    "maxLength": 120,
                    "checks": ["对象和主题明确", "核心问题或成效清楚", "做法、原因有材料依据"],
                },
                "depositPrompt": "写下今天最值得迁移到申论作答中的一个规范表达。",
            },
            ensure_ascii=False,
        ),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
