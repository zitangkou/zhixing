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
        "openingPattern": _text(value.get("openingPattern")),
        "transition": _text(value.get("transition")),
        "fields": value.get("fields") if isinstance(value.get("fields"), list) else [],
        "points": points,
    }


def _exam_anchor_out(value: object) -> dict:
    if not isinstance(value, dict):
        return {"theme": "", "titleDevice": "", "stancePath": ""}
    return {
        "theme": _text(value.get("theme")),
        "titleDevice": _text(value.get("titleDevice")),
        "stancePath": _text(value.get("stancePath")),
    }


def _transfer_out(value: object) -> dict:
    if not isinstance(value, dict):
        return {"examFit": "", "caution": "", "imitateDemo": ""}
    return {
        "examFit": _text(value.get("examFit")),
        "caution": _text(value.get("caution")),
        "imitateDemo": _text(value.get("imitateDemo")),
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
    raw_arg = _loads(row.argument_json, {})
    argument = _argument_out(raw_arg)
    terms = _dict_list(_loads(row.terms_json, []), ("term", "category"), ("plainWord",))
    quotes = _dict_list(_loads(row.quotes_json, []), ("text", "source"), ("meaning",))
    verbs = _dict_list(_loads(row.verbs_json, []), ("verb", "usage"), ("category",))
    templates = _dict_list(
        _loads(row.templates_json, []),
        ("type", "original", "template", "imitate"),
        ("typeName",),
    )
    exam_anchor = _exam_anchor_out(raw_arg.get("examAnchor") if isinstance(raw_arg, dict) else None)
    transfer = _transfer_out(raw_arg.get("transferGuide") if isinstance(raw_arg, dict) else None)
    practice = _loads(row.practice_json, {})
    if not isinstance(practice, dict):
        practice = {}
    if not practice.get("prompt") and transfer.get("imitateDemo"):
        practice = {
            "prompt": "按迁移指南完成一段仿写。",
            "minLength": 150,
            "maxLength": 250,
            "checks": [transfer["caution"]] if transfer.get("caution") else ["对照示范结构"],
            "referenceAnswer": transfer["imitateDemo"],
        }
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
        "examAnchor": exam_anchor,
        "transferGuide": transfer,
        "practice": practice,
        "displayHtml": (getattr(row, "display_html", None) or "").strip(),
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


def published_example_for_article(db: Session, article_id: str) -> dict | None:
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
        if example:
            return example
    return None


def upsert_teaching_from_parsed(db: Session, parsed, *, source_url: str = "", display_html: str = "") -> tuple:
    from app.models.base import gen_id
    from app.services.html_sanitize import sanitize_display_html
    from app.services.shenlun_import_service import theme_tags_from_anchor, v218_incomplete_reasons

    gaps = v218_incomplete_reasons(parsed)
    if gaps:
        raise ValueError("v2.18 结构不完整：" + "、".join(gaps))

    title = parsed.articleTitle.strip()
    article = db.query(RmrbArticle).filter(RmrbArticle.title == title).first()
    theme_tags = theme_tags_from_anchor(parsed.examAnchor.theme)
    tags_json = json.dumps(theme_tags, ensure_ascii=False)
    if not article:
        article = RmrbArticle(
            id=parsed.articleId if parsed.articleId and str(parsed.articleId).startswith("rmrb") else gen_id("rmrb"),
            title=title,
            source="人民时评",
            source_url=source_url,
            publish_date=parsed.mineDate or "",
            summary=(parsed.sourceExcerpt or "")[:500],
            content=parsed.sourceExcerpt or title,
            tags=tags_json,
            is_published=True,
        )
        db.add(article)
        db.flush()
    else:
        article.tags = tags_json
        if source_url and not article.source_url:
            article.source_url = source_url

    arg = parsed.argument.model_dump() if parsed.argument else {}
    arg["examAnchor"] = parsed.examAnchor.model_dump()
    arg["transferGuide"] = parsed.transferGuide.model_dump()
    practice = {
        "prompt": "按迁移指南完成一段仿写。",
        "minLength": 150,
        "maxLength": 250,
        "checks": [parsed.transferGuide.caution] if parsed.transferGuide.caution else ["对照示范结构"],
        "referenceAnswer": parsed.transferGuide.imitateDemo,
    }
    version = "v2.18"
    payload = {
        "sourceExcerpt": parsed.sourceExcerpt,
        "argument": arg,
        "terms": [t.model_dump() if hasattr(t, "model_dump") else t for t in parsed.terms],
        "quotes": [q.model_dump() for q in parsed.quotes],
        "verbs": [v.model_dump() for v in parsed.verbs],
        "templates": [t.model_dump() for t in parsed.templates],
        "practice": practice,
    }
    content_hash = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    row = (
        db.query(ShenlunTeachingExample)
        .filter(
            ShenlunTeachingExample.article_id == article.id,
            ShenlunTeachingExample.version == version,
        )
        .first()
    )
    if not row:
        row = ShenlunTeachingExample(
            id=gen_id("ste"),
            article_id=article.id,
            version=version,
        )
        db.add(row)
    row.source_excerpt = parsed.sourceExcerpt
    row.argument_json = json.dumps(arg, ensure_ascii=False)
    row.terms_json = json.dumps(payload["terms"], ensure_ascii=False)
    row.quotes_json = json.dumps(payload["quotes"], ensure_ascii=False)
    row.verbs_json = json.dumps(payload["verbs"], ensure_ascii=False)
    row.templates_json = json.dumps(payload["templates"], ensure_ascii=False)
    row.practice_json = json.dumps(practice, ensure_ascii=False)
    row.content_hash = content_hash
    cleaned = sanitize_display_html(display_html)
    if cleaned:
        row.display_html = cleaned
    row.status = "published"
    db.commit()
    db.refresh(row)
    example = teaching_example_out(row)
    if not example:
        raise ValueError("示范写入后仍未通过完整性校验")
    return article, example
