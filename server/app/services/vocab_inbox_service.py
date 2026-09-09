"""词表待收录：开采/导入扫到未知类型名，人工晋升进目录。"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import (
    Category,
    ShenlunArgumentMethod,
    ShenlunSentenceType,
    ShenlunSkeletonTemplate,
    ShenlunTermCategory,
    VocabInbox,
    gen_id,
    utcnow,
)
from app.schemas import (
    ShenlunArgumentMethodCreate,
    ShenlunSentenceTypeCreate,
    ShenlunSkeletonTemplateCreate,
    ShenlunTermCategoryCreate,
)
from app.services.rmrb_meta_service import (
    _slug_code,
    create_argument_method,
    create_sentence_type,
    create_skeleton_template,
    create_term_category,
)

KINDS = (
    "term_category",
    "verb_category",
    "sentence_type",
    "argument_method",
    "skeleton",
    "theory_category",
)

SKIP_NAMES = frozenset({"其他", "动词其他", "不选", "", "dialectic", "direction", "solution", "quote"})

UNCLASSIFIED_PARENT = "未归类"


def _trim(name: str | None) -> str:
    return (name or "").strip()


def _in_catalog(db: Session, kind: str, name: str) -> bool:
    if kind == "term_category":
        q = db.query(ShenlunTermCategory).filter(ShenlunTermCategory.name == name)
        rows = q.all()
        return any((getattr(r, "kind", None) or "term") == "term" for r in rows) or (
            bool(rows) and all(not getattr(r, "kind", None) for r in rows)
        )
    if kind == "verb_category":
        return (
            db.query(ShenlunTermCategory)
            .filter(ShenlunTermCategory.name == name, ShenlunTermCategory.kind == "verb")
            .first()
            is not None
        )
    if kind == "sentence_type":
        return (
            db.query(ShenlunSentenceType)
            .filter((ShenlunSentenceType.name == name) | (ShenlunSentenceType.code == name))
            .first()
            is not None
        )
    if kind == "argument_method":
        return db.query(ShenlunArgumentMethod).filter(ShenlunArgumentMethod.name == name).first() is not None
    if kind == "skeleton":
        return db.query(ShenlunSkeletonTemplate).filter(ShenlunSkeletonTemplate.name == name).first() is not None
    if kind == "theory_category":
        return db.query(Category).filter(Category.name == name).first() is not None
    return False


def observe(
    db: Session,
    kind: str,
    name: str,
    *,
    source_article_id: str = "",
    source_title: str = "",
) -> None:
    if kind not in KINDS:
        return
    name = _trim(name)
    if not name or name in SKIP_NAMES or len(name) > 128:
        return
    if _in_catalog(db, kind, name):
        return
    for obj in db.new:
        if isinstance(obj, VocabInbox) and obj.kind == kind and obj.name == name:
            obj.hit_count = int(obj.hit_count or 1) + 1
            obj.last_seen = utcnow()
            return
    row = db.query(VocabInbox).filter(VocabInbox.kind == kind, VocabInbox.name == name).first()
    now = utcnow()
    if row:
        if row.status == "ignored" or row.status == "promoted":
            return
        row.hit_count = int(row.hit_count or 1) + 1
        row.last_seen = now
        if source_article_id:
            row.source_article_id = source_article_id
            row.source_title = (source_title or "")[:256]
        row.updated_at = now
        return
    db.add(
        VocabInbox(
            id=gen_id("vin"),
            kind=kind,
            name=name,
            status="pending",
            hit_count=1,
            source_article_id=source_article_id or "",
            source_title=(source_title or "")[:256],
        )
    )
    db.flush()


def observe_from_mine(
    db: Session,
    *,
    terms,
    verbs,
    templates,
    argument,
    article_id: str = "",
    article_title: str = "",
) -> None:
    src = {"source_article_id": article_id or "", "source_title": article_title or ""}
    for item in terms or []:
        cat = item.get("category") if isinstance(item, dict) else getattr(item, "category", "")
        observe(db, "term_category", str(cat or ""), **src)
    for item in verbs or []:
        cat = item.get("category") if isinstance(item, dict) else getattr(item, "category", "")
        observe(db, "verb_category", str(cat or ""), **src)
    for item in templates or []:
        if isinstance(item, dict):
            tname = item.get("typeName") or ""
            tcode = item.get("type") or ""
        else:
            tname = getattr(item, "typeName", "") or ""
            tcode = getattr(item, "type", "") or ""
        observe(db, "sentence_type", str(tname or tcode), **src)
    if argument is None:
        return
    if isinstance(argument, dict):
        observe(db, "skeleton", str(argument.get("templateName") or ""), **src)
        observe(db, "argument_method", str(argument.get("overviewMethod") or ""), **src)
        for p in argument.get("points") or []:
            if isinstance(p, dict):
                observe(db, "argument_method", str(p.get("method") or ""), **src)
    else:
        observe(db, "skeleton", str(getattr(argument, "templateName", "") or ""), **src)
        observe(db, "argument_method", str(getattr(argument, "overviewMethod", "") or ""), **src)
        for p in getattr(argument, "points", None) or []:
            observe(db, "argument_method", str(getattr(p, "method", "") or ""), **src)


def observe_uncategorized_theory(db: Session, article) -> None:
    if getattr(article, "category_id", None):
        return
    tags = []
    try:
        raw = json.loads(getattr(article, "tags", None) or "[]")
        if isinstance(raw, list):
            tags = [str(x).strip() for x in raw if str(x).strip()]
    except json.JSONDecodeError:
        pass
    aid = getattr(article, "id", "") or ""
    title = getattr(article, "title", "") or ""
    for tag in tags:
        observe(db, "theory_category", tag, source_article_id=aid, source_title=title)


def list_inbox(
    db: Session,
    *,
    kind: str | None = None,
    kinds: list[str] | None = None,
    status: str = "pending",
) -> list[dict]:
    q = db.query(VocabInbox)
    if kinds:
        q = q.filter(VocabInbox.kind.in_(kinds))
    elif kind:
        q = q.filter(VocabInbox.kind == kind)
    if status:
        q = q.filter(VocabInbox.status == status)
    rows = q.order_by(VocabInbox.hit_count.desc(), VocabInbox.updated_at.desc()).all()
    return [_row_out(r) for r in rows]


def _row_out(r: VocabInbox) -> dict:
    return {
        "id": r.id,
        "kind": r.kind,
        "name": r.name,
        "status": r.status,
        "hitCount": r.hit_count,
        "sourceArticleId": r.source_article_id,
        "sourceTitle": r.source_title,
        "createdAt": r.created_at.isoformat() if r.created_at else "",
        "updatedAt": r.updated_at.isoformat() if r.updated_at else "",
    }


def ignore_inbox(db: Session, inbox_id: str) -> dict | None:
    row = db.get(VocabInbox, inbox_id)
    if not row:
        return None
    row.status = "ignored"
    row.updated_at = utcnow()
    db.commit()
    db.refresh(row)
    return _row_out(row)


def _ensure_unclassified_parent(db: Session) -> Category:
    parent = (
        db.query(Category)
        .filter(Category.name == UNCLASSIFIED_PARENT, Category.parent_id.is_(None))
        .first()
    )
    if parent:
        return parent
    parent = Category(id=gen_id("cat"), name=UNCLASSIFIED_PARENT, parent_id=None, sort_order=99)
    db.add(parent)
    db.flush()
    return parent


def promote_inbox(db: Session, inbox_id: str) -> dict:
    row = db.get(VocabInbox, inbox_id)
    if not row:
        raise ValueError("待收录项不存在")
    if row.status != "pending":
        raise ValueError("该项已处理")
    name = row.name
    kind = row.kind
    if _in_catalog(db, kind, name):
        row.status = "promoted"
        db.commit()
        return _row_out(row)

    if kind == "term_category":
        create_term_category(db, ShenlunTermCategoryCreate(name=name, kind="term"))
    elif kind == "verb_category":
        create_term_category(db, ShenlunTermCategoryCreate(name=name, kind="verb"))
    elif kind == "sentence_type":
        create_sentence_type(
            db,
            ShenlunSentenceTypeCreate(code=_slug_code(name), name=name, tip="", sortOrder=50),
        )
    elif kind == "argument_method":
        create_argument_method(
            db,
            ShenlunArgumentMethodCreate(name=name, scope="point", note="", template="", sortOrder=50),
        )
    elif kind == "skeleton":
        create_skeleton_template(
            db,
            ShenlunSkeletonTemplateCreate(name=name, description="", mode="points", sortOrder=50),
        )
    elif kind == "theory_category":
        parent = _ensure_unclassified_parent(db)
        db.add(Category(id=gen_id("cat"), name=name, parent_id=parent.id, sort_order=0))
        db.commit()
    else:
        raise ValueError("未知词表类型")

    # create_* already committed; refresh inbox
    row = db.get(VocabInbox, inbox_id)
    if row:
        row.status = "promoted"
        db.commit()
        db.refresh(row)
        return _row_out(row)
    return {"id": inbox_id, "kind": kind, "name": name, "status": "promoted"}
