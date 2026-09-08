from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import Category, gen_id


def get_category_path(db: Session, category_id: str | None) -> list[str]:
    if not category_id:
        return []
    path: list[str] = []
    current = db.get(Category, category_id)
    while current:
        path.insert(0, current.name)
        current = db.get(Category, current.parent_id) if current.parent_id else None
    return path


def sync_article_category(db: Session, article, category_id: str | None) -> None:
    article.category_id = category_id
    article.category_path = json.dumps(get_category_path(db, category_id), ensure_ascii=False)


def build_category_tree(db: Session, active_only: bool = True) -> list[dict]:
    q = db.query(Category).order_by(Category.sort_order, Category.name)
    if active_only:
        q = q.filter(Category.is_active.is_(True))
    rows = q.all()
    by_parent: dict[str | None, list[Category]] = {}
    for row in rows:
        by_parent.setdefault(row.parent_id, []).append(row)

    def walk(parent_id: str | None) -> list[dict]:
        items = []
        for cat in by_parent.get(parent_id, []):
            items.append({
                "id": cat.id,
                "name": cat.name,
                "parentId": cat.parent_id,
                "sortOrder": cat.sort_order,
                "children": walk(cat.id),
            })
        return items

    return walk(None)


def seed_default_categories(db: Session) -> dict[str, str]:
    """返回 slug-like 名称 -> id 映射"""
    if db.query(Category).count() > 0:
        return {c.name: c.id for c in db.query(Category).all()}

    ids: dict[str, str] = {}

    def add(name: str, parent_id: str | None = None, sort_order: int = 0) -> str:
        cat = Category(id=gen_id("cat"), name=name, parent_id=parent_id, sort_order=sort_order)
        db.add(cat)
        db.flush()
        ids[name] = cat.id
        return cat.id

    theory = add("政治理论", sort_order=1)
    add("时政要闻", theory, 1)
    add("思想理论", theory, 2)
    add("政策法规", theory, 3)
    history = add("党史学习", sort_order=2)
    add("党史事件", history, 1)
    add("人物事迹", history, 2)
    culture = add("文化思想", sort_order=3)
    add("中华文明", culture, 1)
    add("传统文化", culture, 2)
    db.flush()
    return ids
