"""人民日报模块 · 时评文章 CRUD（开采本/规范词见 shenlun_service）"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import RmrbArticle, ShenlunTeachingExample, gen_id
from app.schemas import RmrbArticleCreate, RmrbArticleOut, RmrbArticleUpdate
from app.timezone import today as today_str


def _looks_like_html(text: str) -> bool:
    raw = (text or "").strip()
    return bool(raw) and "<" in raw and "</" in raw


def _parse_source_html(raw: str) -> dict:
    from app.services.article_import import parse_rmrb_source_html

    parsed, _warnings = parse_rmrb_source_html(raw)
    return parsed


def _to_out(a: RmrbArticle, *, include_html: bool = True) -> RmrbArticleOut:
    return RmrbArticleOut(
        id=a.id,
        title=a.title,
        source=a.source or "人民时评",
        sourceUrl=getattr(a, "source_url", "") or "",
        publishDate=a.publish_date or "",
        summary=a.summary or "",
        content=a.content or "",
        contentHtml=(getattr(a, "content_html", "") or "") if include_html else "",
        tags=_parse_tags(getattr(a, "tags", None)),
        isPublished=bool(a.is_published),
        isDaily=bool(getattr(a, "is_daily", False)),
        sortOrder=a.sort_order or 0,
        readCount=a.read_count or 0,
        createdAt=a.created_at,
        updatedAt=a.updated_at,
        hasParse=False,
    )


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
    except json.JSONDecodeError:
        pass
    # 兼容逗号分隔旧写法
    return [p.strip() for p in raw.split(",") if p.strip()]


def _dump_tags(tags: list[str] | None) -> str:
    cleaned: list[str] = []
    seen: set[str] = set()
    for t in tags or []:
        s = str(t).strip()
        if s and s not in seen:
            seen.add(s)
            cleaned.append(s)
    return json.dumps(cleaned, ensure_ascii=False)


def list_articles(
    db: Session,
    *,
    published_only: bool = False,
    tag: str | None = None,
    include_html: bool = False,
) -> list[RmrbArticleOut]:
    q = db.query(RmrbArticle)
    if published_only:
        q = q.filter(RmrbArticle.is_published.is_(True))
    rows = q.order_by(RmrbArticle.sort_order.desc(), RmrbArticle.publish_date.desc(), RmrbArticle.id.desc()).all()
    outs = [_to_out(r, include_html=include_html) for r in rows]
    if outs:
        taught = {
            row[0]
            for row in db.query(ShenlunTeachingExample.article_id)
            .filter(ShenlunTeachingExample.article_id.in_([o.id for o in outs]))
            .distinct()
            .all()
        }
        for item in outs:
            item.hasParse = item.id in taught
    if tag:
        t = tag.strip()
        outs = [o for o in outs if t in (o.tags or [])]
    return outs


def list_today_articles(db: Session, *, fallback: int = 1) -> list[RmrbArticleOut]:
    """优先后台「今日推荐」（可多篇）；没有则按发布日期取最近若干篇。"""
    published = list_articles(db, published_only=True)
    flagged = [a for a in published if a.isDaily]
    if flagged:
        flagged.sort(key=lambda a: (a.publishDate or "", str(a.createdAt or "")), reverse=True)
        return flagged
    return published[:fallback]


def list_theme_tags(db: Session, *, published_only: bool = False) -> list[str]:
    """已使用的主题标签（按出现频次降序）。"""
    from collections import Counter

    from app.schemas import RMRB_THEME_TAG_PRESETS

    counts: Counter[str] = Counter()
    for a in list_articles(db, published_only=published_only):
        for t in a.tags or []:
            counts[t] += 1
    used = [t for t, _ in counts.most_common()]
    # 预设靠前，未使用的预设也返回，方便筛选/录入
    ordered: list[str] = []
    for t in RMRB_THEME_TAG_PRESETS:
        if t not in ordered:
            ordered.append(t)
    for t in used:
        if t not in ordered:
            ordered.append(t)
    return ordered


def get_article(db: Session, article_id: str, *, bump_read: bool = False) -> RmrbArticleOut | None:
    from app.services.shenlun_learning_service import published_example_for_article

    a = db.get(RmrbArticle, article_id)
    if not a:
        return None
    if bump_read:
        a.read_count = (a.read_count or 0) + 1
        db.commit()
        db.refresh(a)
    out = _to_out(a)
    out.teachingExample = published_example_for_article(db, a.id)
    out.hasParse = bool(out.teachingExample)
    return out


def create_article(db: Session, body: RmrbArticleCreate) -> RmrbArticleOut:
    title = (body.title or "").strip()
    source = (body.source or "人民时评").strip()
    source_url = (body.sourceUrl or "").strip()
    publish_date = (body.publishDate or today_str()).strip()
    summary = (body.summary or "").strip()
    tags = list(body.tags or [])
    content = body.content or ""
    content_html = (body.contentHtml or "").strip()
    if not content_html and _looks_like_html(content):
        content_html = content.strip()
    if content_html:
        parsed = _parse_source_html(content_html)
        content_html = parsed["content_html"]
        if not content.strip() or _looks_like_html(content):
            content = parsed["content"]
        title = title or parsed["title"]
        source = source if source != "人民时评" else (parsed.get("source") or source)
        source_url = source_url or parsed.get("source_url") or ""
        publish_date = publish_date or parsed.get("publish_date") or today_str()
        summary = summary or parsed.get("summary") or ""
        tags = tags or list(parsed.get("tags") or [])
    if not title:
        raise ValueError("标题不能为空（可在 HTML 中提供 h1）")
    a = RmrbArticle(
        id=gen_id("rmrb"),
        title=title,
        source=source,
        source_url=source_url,
        publish_date=publish_date,
        summary=summary,
        content=content,
        content_html=content_html,
        tags=_dump_tags(tags),
        is_published=body.isPublished,
        is_daily=body.isDaily,
        sort_order=body.sortOrder,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _to_out(a)


def update_article(db: Session, article_id: str, body: RmrbArticleUpdate) -> RmrbArticleOut | None:
    a = db.get(RmrbArticle, article_id)
    if not a:
        return None
    data = body.model_dump(exclude_unset=True)
    mapping = {
        "publishDate": "publish_date",
        "sourceUrl": "source_url",
        "isPublished": "is_published",
        "isDaily": "is_daily",
        "sortOrder": "sort_order",
        "contentHtml": "content_html",
    }
    html_raw = data.pop("contentHtml", None)
    content_raw = data.get("content")
    if html_raw is None and isinstance(content_raw, str) and _looks_like_html(content_raw):
        html_raw = content_raw
    if html_raw is not None:
        html_raw = (html_raw or "").strip()
        if html_raw:
            parsed = _parse_source_html(html_raw)
            a.content_html = parsed["content_html"]
            if content_raw is None or not str(content_raw).strip() or _looks_like_html(str(content_raw)):
                a.content = parsed["content"]
                data.pop("content", None)
            if not (data.get("title") or a.title):
                data["title"] = parsed["title"]
            if not data.get("sourceUrl") and parsed.get("source_url"):
                data["sourceUrl"] = parsed["source_url"]
            if not data.get("publishDate") and parsed.get("publish_date") and not a.publish_date:
                data["publishDate"] = parsed["publish_date"]
            if not data.get("summary") and parsed.get("summary") and not a.summary:
                data["summary"] = parsed["summary"]
        else:
            a.content_html = ""
    for k, v in data.items():
        if k == "tags":
            a.tags = _dump_tags(v)
            continue
        setattr(a, mapping.get(k, k), v)
    db.commit()
    db.refresh(a)
    return _to_out(a)


def delete_article(db: Session, article_id: str) -> bool:
    a = db.get(RmrbArticle, article_id)
    if not a:
        return False
    db.query(ShenlunTeachingExample).filter(ShenlunTeachingExample.article_id == article_id).delete(
        synchronize_session=False
    )
    db.delete(a)
    db.commit()
    return True
