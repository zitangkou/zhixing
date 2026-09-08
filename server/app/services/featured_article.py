"""导入人民日报重点文章（十五五规划建议）"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Article, Category, Question, gen_id
from app.services.category_service import sync_article_category
from app.services.question_factory import add_generated_questions
from app.services.serializers import generate_questions_for_article
from app.timezone import now

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "shiwuwu-plan.json"
FEATURED_SOURCE_URL = "https://paper.people.com.cn/rmrb/pc/content/202510/29/content_30111880.html"


def seed_featured_article(db: Session) -> Article | None:
    if not DATA_PATH.exists():
        return None

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    existing = (
        db.query(Article)
        .filter(
            (Article.source_url == FEATURED_SOURCE_URL)
            | (Article.title == payload["title"])
        )
        .first()
    )

    sections = payload["sections"]
    mind_map = payload["mindMap"]
    content = payload.get("content") or ""

    cat = db.query(Category).filter(Category.name == "思想理论").first()

    if existing:
        existing.title = payload["title"]
        existing.source = payload["source"]
        existing.source_url = FEATURED_SOURCE_URL
        existing.publish_date = payload["publishDate"]
        existing.summary = payload["summary"]
        existing.content = content
        existing.sections = json.dumps(sections, ensure_ascii=False)
        existing.tags = json.dumps(payload.get("tags") or [], ensure_ascii=False)
        existing.mind_map = json.dumps(mind_map, ensure_ascii=False)
        existing.is_published = True
        existing.is_daily = True
        existing.is_featured = True
        existing.importance = 5
        existing.status = "published"
        existing.allow_quiz = True
        if cat:
            sync_article_category(db, existing, cat.id)
        db.flush()
        return existing

    article = Article(
        id=payload.get("id") or gen_id("art"),
        title=payload["title"],
        source=payload["source"],
        source_url=FEATURED_SOURCE_URL,
        publish_date=payload["publishDate"],
        summary=payload["summary"],
        content=content,
        sections=json.dumps(sections, ensure_ascii=False),
        tags=json.dumps(payload.get("tags") or [], ensure_ascii=False),
        mind_map=json.dumps(mind_map, ensure_ascii=False),
        is_published=True,
        is_daily=True,
        is_featured=True,
        importance=5,
        status="published",
        allow_quiz=True,
        crawled_at=now(),
    )
    db.add(article)
    db.flush()
    if cat:
        sync_article_category(db, article, cat.id)

    for qdata in generate_questions_for_article(article):
        db.add(
            Question(
                id=gen_id("q"),
                article_id=article.id,
                type=qdata["type"],
                stem=qdata["stem"],
                options=json.dumps(qdata.get("options", []), ensure_ascii=False),
                correct_answer=json.dumps(qdata["correct_answer"], ensure_ascii=False)
                if isinstance(qdata["correct_answer"], list)
                else str(qdata["correct_answer"]),
                analysis=qdata["analysis"],
                source_sentence=qdata.get("source_sentence", ""),
                status="approved",
                origin="seed",
                is_active=True,
            )
        )

    return article
