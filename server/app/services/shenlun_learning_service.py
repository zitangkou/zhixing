"""申论公共教研示范读取；不得回退到任何用户个人开采记录。"""

from __future__ import annotations

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import RmrbArticle, ShenlunTeachingExample


def _loads(raw: str, fallback):
    try:
        value = json.loads(raw or "")
    except (TypeError, json.JSONDecodeError):
        return fallback
    return value


def _article_out(article: RmrbArticle) -> dict:
    tags = _loads(article.tags, [])
    return {
        "id": article.id,
        "title": article.title,
        "source": article.source,
        "sourceUrl": article.source_url,
        "publishDate": article.publish_date,
        "summary": article.summary,
        "content": article.content,
        "tags": tags if isinstance(tags, list) else [],
    }


def _text(value) -> str:
    return str(value or "").strip()


def _argument_out(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    overview = _text(value.get("overview"))
    conclusion = _text(value.get("conclusion"))
    raw_points = value.get("points")
    if not overview or not conclusion or not isinstance(raw_points, list) or not raw_points:
        return None
    points = []
    for item in raw_points:
        if not isinstance(item, dict):
            return None
        point = {
            "title": _text(item.get("title") or item.get("claim")),
            "claim": _text(item.get("claim")),
            "evidence": _text(item.get("evidence")),
            "summary": _text(item.get("summary")),
            "method": _text(item.get("method")),
            "methodNote": _text(item.get("methodNote")),
            "template": _text(item.get("template")),
        }
        if not all(point[key] for key in ("title", "evidence", "summary", "method", "methodNote", "template")):
            return None
        points.append(point)
    return {
        "templateId": _text(value.get("templateId")),
        "templateName": _text(value.get("templateName")),
        "mode": _text(value.get("mode")) or "points",
        "overview": overview,
        "conclusion": conclusion,
        "overviewMethod": _text(value.get("overviewMethod")),
        "overviewTemplate": _text(value.get("overviewTemplate")),
        "fields": value.get("fields") if isinstance(value.get("fields"), list) else [],
        "points": points,
    }


def _dict_list(value: object, required: tuple[str, ...], optional: tuple[str, ...] = ()) -> list[dict] | None:
    if not isinstance(value, list):
        return None
    output = []
    for item in value:
        if not isinstance(item, dict):
            return None
        normalized = {key: _text(item.get(key)) for key in (*required, *optional)}
        if not all(normalized[key] for key in required):
            return None
        output.append(normalized)
    return output


def teaching_example_out(row: ShenlunTeachingExample) -> dict | None:
    argument = _argument_out(_loads(row.argument_json, {}))
    terms = _dict_list(_loads(row.terms_json, []), ("term", "category"), ("plainWord",))
    quotes = _dict_list(_loads(row.quotes_json, []), ("text", "source"), ("meaning",))
    verbs = _dict_list(_loads(row.verbs_json, []), ("verb", "usage"), ("category",))
    templates = _dict_list(
        _loads(row.templates_json, []),
        ("type", "original", "template", "imitate"),
        ("typeName",),
    )
    practice = _loads(row.practice_json, {})
    if not all((
        row.source_excerpt.strip(), argument,
        terms, quotes is not None, verbs is not None,
        templates,
        isinstance(practice, dict), practice.get("prompt"), practice.get("referenceAnswer"),
        isinstance(practice.get("checks"), list) and practice["checks"],
    )):
        return None
    try:
        minimum = int(practice.get("minLength", 20))
        maximum = int(practice.get("maxLength", 150))
    except (TypeError, ValueError):
        return None
    if minimum < 1 or maximum < minimum or maximum > 1000:
        return None
    practice = {
        "prompt": _text(practice["prompt"]),
        "minLength": minimum,
        "maxLength": maximum,
        "checks": [str(item).strip() for item in practice["checks"] if str(item).strip()][:8],
        "referenceAnswer": _text(practice["referenceAnswer"]),
    }
    if not practice["checks"]:
        return None
    return {
        "id": row.id,
        "version": row.version,
        "sourceExcerpt": row.source_excerpt.strip(),
        "argument": argument,
        "terms": terms,
        "quotes": quotes,
        "verbs": verbs,
        "templates": templates,
        "practice": practice,
    }


def _published_rows(db: Session):
    return (
        db.query(ShenlunTeachingExample, RmrbArticle)
        .join(RmrbArticle, RmrbArticle.id == ShenlunTeachingExample.article_id)
        .filter(
            ShenlunTeachingExample.status == "published",
            RmrbArticle.is_published.is_(True),
        )
        .order_by(
            RmrbArticle.sort_order.desc(),
            RmrbArticle.publish_date.desc(),
            ShenlunTeachingExample.updated_at.desc(),
        )
        .all()
    )


def list_learning_articles(db: Session) -> list[dict]:
    items = []
    seen: set[str] = set()
    for example, article in _published_rows(db):
        if article.id in seen or not teaching_example_out(example):
            continue
        seen.add(article.id)
        data = _article_out(article)
        data["teachingVersion"] = example.version
        items.append(data)
    return items


def get_learning_article(db: Session, article_id: str) -> dict:
    article = db.get(RmrbArticle, article_id)
    if not article or not article.is_published:
        raise HTTPException(404, "学习内容已下线或不存在")
    rows = (
        db.query(ShenlunTeachingExample)
        .filter(
            ShenlunTeachingExample.article_id == article_id,
            ShenlunTeachingExample.status == "published",
        )
        .order_by(ShenlunTeachingExample.updated_at.desc())
        .all()
    )
    for row in rows:
        example = teaching_example_out(row)
        if not example:
            continue
        article_data = _article_out(article)
        revision_source = json.dumps(
            {"article": article_data, "example": example},
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
        return {
            "article": article_data,
            "example": example,
            "revision": hashlib.sha256(revision_source).hexdigest(),
        }
    raise HTTPException(404, "教研示范尚未发布")
