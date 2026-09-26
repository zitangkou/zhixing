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


THEORY_ROOT = "政治理论"
# 政治理论下的二级分类（顺序即默认排序）；后五个与运营 HTML「分类：」取值一致
THEORY_CHILDREN = (
    "时政要闻",
    "思想理论",
    "政策法规",
    "大国外交",
    "经济发展",
    "生态文明",
    "民生保障",
    "科技自立自强",
)


def ensure_theory_categories(db: Session) -> list[str]:
    """幂等补齐政治理论二级分类：按名称判断，已存在（含已停用）的不动，缺的追加到末尾。返回新增名称。"""
    root = (
        db.query(Category)
        .filter(Category.name == THEORY_ROOT, Category.parent_id.is_(None))
        .order_by(Category.sort_order)
        .first()
    )
    added: list[str] = []
    if not root:
        max_root = max((c.sort_order or 0 for c in db.query(Category).filter(Category.parent_id.is_(None))), default=0)
        root = Category(id=gen_id("cat"), name=THEORY_ROOT, parent_id=None, sort_order=max_root + 1)
        db.add(root)
        db.flush()
        added.append(THEORY_ROOT)
    existing = {c.name for c in db.query(Category).all()}
    next_order = max(
        (c.sort_order or 0 for c in db.query(Category).filter(Category.parent_id == root.id)),
        default=0,
    )
    for name in THEORY_CHILDREN:
        if name in existing:
            continue
        next_order += 1
        db.add(Category(id=gen_id("cat"), name=name, parent_id=root.id, sort_order=next_order))
        existing.add(name)
        added.append(name)
    if added:
        db.flush()
    return added


def seed_default_categories(db: Session) -> dict[str, str]:
    """空表时写入默认分类；非空时只幂等补齐政治理论二级分类。返回 名称 -> id 映射"""
    if db.query(Category).count() > 0:
        ensure_theory_categories(db)
        return {c.name: c.id for c in db.query(Category).all()}

    ids: dict[str, str] = {}

    def add(name: str, parent_id: str | None = None, sort_order: int = 0) -> str:
        cat = Category(id=gen_id("cat"), name=name, parent_id=parent_id, sort_order=sort_order)
        db.add(cat)
        db.flush()
        ids[name] = cat.id
        return cat.id

    theory = add(THEORY_ROOT, sort_order=1)
    for idx, name in enumerate(THEORY_CHILDREN, start=1):
        add(name, theory, idx)
    history = add("党史学习", sort_order=2)
    add("党史事件", history, 1)
    add("人物事迹", history, 2)
    culture = add("文化思想", sort_order=3)
    add("中华文明", culture, 1)
    add("传统文化", culture, 2)
    db.flush()
    return ids
