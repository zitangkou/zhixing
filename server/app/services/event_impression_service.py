"""时事新闻 · 事件印象：记录事件 + 挂知识框架，形成考点联系。"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import AppUser, EventImpression, gen_id
from app.schemas import (
    EventFrameworkGroup,
    EventHubOut,
    EventImpressionCreate,
    EventImpressionOut,
    EventImpressionUpdate,
)
from app.services.knowledge_service import resolve_knowledge_ref
from app.timezone import now, today as today_str


def _label(tree_key: str, path: str) -> str:
    tk = (tree_key or "").strip()
    p = (path or "").strip()
    if tk and p:
        return f"{tk} / {p}"
    return p or tk or "未归属框架"


def _to_out(m: EventImpression) -> EventImpressionOut:
    return EventImpressionOut(
        id=m.id,
        title=m.title or "",
        eventDate=m.event_date or "",
        place=m.place or "",
        coreContent=m.core_content or "",
        note=m.note or "",
        knowledgeNodeId=m.knowledge_node_id,
        knowledgeTreeKey=m.knowledge_tree_key or "",
        knowledgePath=m.knowledge_path or "",
        createdAt=m.created_at,
        updatedAt=m.updated_at,
    )


def list_events(
    db: Session,
    user: AppUser,
    *,
    tree_key: str | None = None,
    path: str | None = None,
    unlinked: bool = False,
    limit: int = 100,
) -> list[EventImpressionOut]:
    q = db.query(EventImpression).filter(EventImpression.user_id == user.id)
    if unlinked:
        q = q.filter(
            (EventImpression.knowledge_path == "") | (EventImpression.knowledge_path.is_(None)),
            (EventImpression.knowledge_tree_key == "") | (EventImpression.knowledge_tree_key.is_(None)),
        )
    else:
        if tree_key:
            q = q.filter(EventImpression.knowledge_tree_key == tree_key.strip())
        if path:
            # 前缀匹配：选「航天常识」时，子路径「航天常识/神舟系列」也纳入
            p = path.strip()
            q = q.filter(
                (EventImpression.knowledge_path == p)
                | (EventImpression.knowledge_path.like(f"{p}/%"))
            )
    rows = (
        q.order_by(EventImpression.event_date.desc(), EventImpression.updated_at.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    return [_to_out(r) for r in rows]


def get_event(db: Session, user: AppUser, event_id: str) -> EventImpressionOut | None:
    m = (
        db.query(EventImpression)
        .filter(EventImpression.id == event_id, EventImpression.user_id == user.id)
        .first()
    )
    return _to_out(m) if m else None


def create_event(db: Session, user: AppUser, body: EventImpressionCreate) -> EventImpressionOut:
    title = (body.title or "").strip()
    if not title:
        raise ValueError("请填写事件标题")
    nid, tk, path = resolve_knowledge_ref(
        db,
        node_id=body.knowledgeNodeId,
        tree_key=body.knowledgeTreeKey,
        path=body.knowledgePath,
    )
    m = EventImpression(
        id=gen_id("ei"),
        user_id=user.id,
        title=title,
        event_date=(body.eventDate or today_str()).strip(),
        place=(body.place or "").strip(),
        core_content=(body.coreContent or "").strip(),
        note=(body.note or "").strip(),
        knowledge_node_id=nid,
        knowledge_tree_key=tk,
        knowledge_path=path,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _to_out(m)


def update_event(
    db: Session,
    user: AppUser,
    event_id: str,
    body: EventImpressionUpdate,
) -> EventImpressionOut | None:
    m = (
        db.query(EventImpression)
        .filter(EventImpression.id == event_id, EventImpression.user_id == user.id)
        .first()
    )
    if not m:
        return None
    data = body.model_dump(exclude_unset=True)
    mapping = {
        "eventDate": "event_date",
        "coreContent": "core_content",
        "knowledgeNodeId": "knowledge_node_id",
        "knowledgeTreeKey": "knowledge_tree_key",
        "knowledgePath": "knowledge_path",
    }
    kb_keys = {"knowledgeNodeId", "knowledgeTreeKey", "knowledgePath"}
    if kb_keys & set(data.keys()):
        nid, tk, path = resolve_knowledge_ref(
            db,
            node_id=data.get("knowledgeNodeId", m.knowledge_node_id),
            tree_key=data.get("knowledgeTreeKey", m.knowledge_tree_key),
            path=data.get("knowledgePath", m.knowledge_path),
        )
        m.knowledge_node_id = nid
        m.knowledge_tree_key = tk
        m.knowledge_path = path
        for k in kb_keys:
            data.pop(k, None)
    for k, v in data.items():
        col = mapping.get(k, k)
        if isinstance(v, str):
            v = v.strip()
        setattr(m, col, v)
    if not (m.title or "").strip():
        raise ValueError("标题不能为空")
    db.commit()
    db.refresh(m)
    return _to_out(m)


def delete_event(db: Session, user: AppUser, event_id: str) -> bool:
    m = (
        db.query(EventImpression)
        .filter(EventImpression.id == event_id, EventImpression.user_id == user.id)
        .first()
    )
    if not m:
        return False
    db.delete(m)
    db.commit()
    return True


def get_hub(db: Session, user: AppUser) -> EventHubOut:
    rows = (
        db.query(EventImpression)
        .filter(EventImpression.user_id == user.id)
        .order_by(EventImpression.event_date.desc(), EventImpression.updated_at.desc())
        .all()
    )
    outs = [_to_out(r) for r in rows]
    week_ago = (now().date() - timedelta(days=7)).isoformat()
    linked = [o for o in outs if o.knowledgePath or o.knowledgeTreeKey]
    unlinked = [o for o in outs if not o.knowledgePath and not o.knowledgeTreeKey]
    recent = [o for o in outs if (o.eventDate or "") >= week_ago]

    groups_map: dict[tuple[str, str], list[EventImpressionOut]] = defaultdict(list)
    for o in linked:
        groups_map[(o.knowledgeTreeKey, o.knowledgePath)].append(o)

    groups = [
        EventFrameworkGroup(
            treeKey=tk,
            path=path,
            label=_label(tk, path),
            count=len(items),
            items=items[:8],
        )
        for (tk, path), items in sorted(
            groups_map.items(),
            key=lambda x: (-len(x[1]), x[0][0], x[0][1]),
        )
    ]
    return EventHubOut(
        total=len(outs),
        linkedCount=len(linked),
        unlinkedCount=len(unlinked),
        recentCount=len(recent),
        frameworkGroups=groups,
    )
