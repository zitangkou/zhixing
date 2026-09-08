"""人民日报模块 · 时评文章 CRUD（开采本/规范词见 shenlun_service）"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import RmrbArticle, gen_id
from app.schemas import RmrbArticleCreate, RmrbArticleOut, RmrbArticleUpdate
from app.timezone import today as today_str


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


def _to_out(a: RmrbArticle) -> RmrbArticleOut:
    return RmrbArticleOut(
        id=a.id,
        title=a.title,
        source=a.source or "人民时评",
        sourceUrl=getattr(a, "source_url", "") or "",
        publishDate=a.publish_date or "",
        summary=a.summary or "",
        content=a.content or "",
        tags=_parse_tags(getattr(a, "tags", None)),
        isPublished=bool(a.is_published),
        sortOrder=a.sort_order or 0,
        readCount=a.read_count or 0,
        createdAt=a.created_at,
        updatedAt=a.updated_at,
    )


def list_articles(
    db: Session,
    *,
    published_only: bool = False,
    tag: str | None = None,
) -> list[RmrbArticleOut]:
    q = db.query(RmrbArticle)
    if published_only:
        q = q.filter(RmrbArticle.is_published.is_(True))
    rows = q.order_by(RmrbArticle.sort_order.desc(), RmrbArticle.publish_date.desc(), RmrbArticle.id.desc()).all()
    outs = [_to_out(r) for r in rows]
    if tag:
        t = tag.strip()
        outs = [o for o in outs if t in (o.tags or [])]
    return outs


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
    a = db.get(RmrbArticle, article_id)
    if not a:
        return None
    if bump_read:
        a.read_count = (a.read_count or 0) + 1
        db.commit()
        db.refresh(a)
    return _to_out(a)


def create_article(db: Session, body: RmrbArticleCreate) -> RmrbArticleOut:
    a = RmrbArticle(
        id=gen_id("rmrb"),
        title=body.title.strip(),
        source=(body.source or "人民时评").strip(),
        source_url=(body.sourceUrl or "").strip(),
        publish_date=(body.publishDate or today_str()).strip(),
        summary=(body.summary or "").strip(),
        content=body.content or "",
        tags=_dump_tags(body.tags),
        is_published=body.isPublished,
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
        "sortOrder": "sort_order",
    }
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
    db.delete(a)
    db.commit()
    return True
