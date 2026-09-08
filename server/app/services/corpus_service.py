"""语料本 · 跨来源词句：捕获 → 澄清 → 占有 → 运用"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import AppUser, CorpusItem, gen_id
from app.schemas import (
    CORPUS_KINDS,
    CORPUS_SOURCE_TYPES,
    CORPUS_TAG_PRESETS,
    CORPUS_TERM_KINDS,
    CorpusItemCreate,
    CorpusItemOut,
    CorpusItemUpdate,
    CorpusStatsOut,
    ShenlunNormTermAdd,
)
from app.services.knowledge_service import resolve_knowledge_ref
from app.services.shenlun_service import add_term


def _loads_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()][:12]
    except Exception:
        pass
    return []


def _dumps_tags(tags: list[str] | None) -> str:
    clean = [str(x).strip() for x in (tags or []) if str(x).strip()]
    # unique keep order
    seen: set[str] = set()
    out: list[str] = []
    for t in clean:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return json.dumps(out[:12], ensure_ascii=False)


def _compute_status(
    *,
    plain_note: str,
    tags: list[str],
    rewrite: str,
    practice: str,
    used_count: int,
) -> str:
    if used_count > 0 or (practice or "").strip():
        return "used"
    if (rewrite or "").strip():
        return "owned"
    if (plain_note or "").strip() or tags:
        return "clarified"
    return "inbox"


def _item_out(m: CorpusItem) -> CorpusItemOut:
    tags = _loads_tags(m.tags_json)
    return CorpusItemOut(
        id=m.id,
        original=m.original or "",
        kind=m.kind or "句",
        sourceType=m.source_type or "其他",
        sourceTitle=m.source_title or "",
        tags=tags,
        plainNote=m.plain_note or "",
        rewrite=m.rewrite or "",
        practice=m.practice or "",
        status=m.status or "inbox",
        usedCount=int(m.used_count or 0),
        promotedTermId=m.promoted_term_id,
        knowledgeNodeId=getattr(m, "knowledge_node_id", None),
        knowledgeTreeKey=getattr(m, "knowledge_tree_key", None) or "",
        knowledgePath=getattr(m, "knowledge_path", None) or "",
        createdAt=m.created_at,
        updatedAt=m.updated_at,
    )


def _refresh_status(m: CorpusItem) -> None:
    m.status = _compute_status(
        plain_note=m.plain_note or "",
        tags=_loads_tags(m.tags_json),
        rewrite=m.rewrite or "",
        practice=m.practice or "",
        used_count=int(m.used_count or 0),
    )


def _apply_knowledge(
    db: Session,
    m: CorpusItem,
    *,
    node_id: str | None,
    tree_key: str | None,
    path: str | None,
    clear_if_empty: bool = False,
) -> None:
    """写入知识框架挂载；三者皆空且 clear_if_empty 时清空。"""
    nid_in = (node_id or "").strip() or None
    tk_in = (tree_key or "").strip()
    path_in = (path or "").strip()
    if clear_if_empty and not nid_in and not tk_in and not path_in:
        m.knowledge_node_id = None
        m.knowledge_tree_key = ""
        m.knowledge_path = ""
        return
    nid, tk, p = resolve_knowledge_ref(
        db,
        node_id=nid_in,
        tree_key=tk_in,
        path=path_in,
    )
    m.knowledge_node_id = nid
    m.knowledge_tree_key = tk or ""
    m.knowledge_path = p or ""


def get_stats(db: Session, user: AppUser) -> CorpusStatsOut:
    rows = db.query(CorpusItem).filter(CorpusItem.user_id == user.id).all()
    counts = {"inbox": 0, "clarified": 0, "owned": 0, "used": 0}
    for r in rows:
        st = r.status if r.status in counts else "inbox"
        counts[st] = counts.get(st, 0) + 1
    return CorpusStatsOut(
        inboxCount=counts["inbox"],
        clarifiedCount=counts["clarified"],
        ownedCount=counts["owned"],
        usedCount=counts["used"],
        total=len(rows),
        kinds=list(CORPUS_KINDS),
        sourceTypes=list(CORPUS_SOURCE_TYPES),
        tagPresets=list(CORPUS_TAG_PRESETS),
    )


def list_items(
    db: Session,
    user: AppUser,
    status: str | None = None,
    limit: int = 100,
) -> list[CorpusItemOut]:
    q = db.query(CorpusItem).filter(CorpusItem.user_id == user.id)
    if status and status != "all":
        q = q.filter(CorpusItem.status == status)
    rows = q.order_by(CorpusItem.updated_at.desc()).limit(max(1, min(limit, 200))).all()
    return [_item_out(r) for r in rows]


def get_item(db: Session, user: AppUser, item_id: str) -> CorpusItemOut | None:
    m = db.get(CorpusItem, item_id)
    if not m or m.user_id != user.id:
        return None
    return _item_out(m)


def create_item(db: Session, user: AppUser, body: CorpusItemCreate) -> CorpusItemOut:
    original = (body.original or "").strip()
    if not original:
        raise ValueError("请填写原文")
    kind = (body.kind or "句").strip() or "句"
    if kind not in CORPUS_KINDS:
        kind = "句"
    source_type = (body.sourceType or "其他").strip() or "其他"
    if source_type not in CORPUS_SOURCE_TYPES:
        source_type = "其他"
    tags = [t for t in (body.tags or []) if str(t).strip()]
    m = CorpusItem(
        id=gen_id("cps"),
        user_id=user.id,
        original=original,
        kind=kind,
        source_type=source_type,
        source_title=(body.sourceTitle or "").strip()[:256],
        tags_json=_dumps_tags(tags),
        plain_note=(body.plainNote or "").strip(),
        rewrite=(body.rewrite or "").strip(),
        practice=(body.practice or "").strip(),
        used_count=0,
    )
    _apply_knowledge(
        db,
        m,
        node_id=body.knowledgeNodeId,
        tree_key=body.knowledgeTreeKey,
        path=body.knowledgePath,
    )
    _refresh_status(m)
    db.add(m)
    db.commit()
    db.refresh(m)
    return _item_out(m)


def update_item(
    db: Session, user: AppUser, item_id: str, body: CorpusItemUpdate
) -> CorpusItemOut | None:
    m = db.get(CorpusItem, item_id)
    if not m or m.user_id != user.id:
        return None
    data = body.model_dump(exclude_unset=True)
    if "original" in data and data["original"] is not None:
        original = str(data["original"]).strip()
        if not original:
            raise ValueError("原文不能为空")
        m.original = original
    if "kind" in data and data["kind"] is not None:
        kind = str(data["kind"]).strip() or "句"
        m.kind = kind if kind in CORPUS_KINDS else m.kind
    if "sourceType" in data and data["sourceType"] is not None:
        st = str(data["sourceType"]).strip() or "其他"
        m.source_type = st if st in CORPUS_SOURCE_TYPES else m.source_type
    if "sourceTitle" in data and data["sourceTitle"] is not None:
        m.source_title = str(data["sourceTitle"]).strip()[:256]
    if "tags" in data and data["tags"] is not None:
        m.tags_json = _dumps_tags(list(data["tags"] or []))
    if "plainNote" in data and data["plainNote"] is not None:
        m.plain_note = str(data["plainNote"]).strip()
    if "rewrite" in data and data["rewrite"] is not None:
        m.rewrite = str(data["rewrite"]).strip()
    if "practice" in data and data["practice"] is not None:
        m.practice = str(data["practice"]).strip()
    if data.get("markUsed"):
        m.used_count = int(m.used_count or 0) + 1
    kb_touched = any(k in data for k in ("knowledgeNodeId", "knowledgeTreeKey", "knowledgePath"))
    if kb_touched:
        _apply_knowledge(
            db,
            m,
            node_id=data.get("knowledgeNodeId", m.knowledge_node_id),
            tree_key=data.get("knowledgeTreeKey", m.knowledge_tree_key),
            path=data.get("knowledgePath", m.knowledge_path),
            clear_if_empty=True,
        )
    _refresh_status(m)
    db.commit()
    db.refresh(m)
    return _item_out(m)


def delete_item(db: Session, user: AppUser, item_id: str) -> bool:
    m = db.get(CorpusItem, item_id)
    if not m or m.user_id != user.id:
        return False
    db.delete(m)
    db.commit()
    return True


def promote_to_term(db: Session, user: AppUser, item_id: str) -> CorpusItemOut | None:
    """晋升到申论规范词库"""
    m = db.get(CorpusItem, item_id)
    if not m or m.user_id != user.id:
        return None
    original = (m.original or "").strip()
    if not original:
        raise ValueError("原文为空，无法晋升")
    # 词/专名/成语等直接作规范词；句子取前 32 字作词条名，改写作例句
    term = original if m.kind in CORPUS_TERM_KINDS else original[:32]
    tags = _loads_tags(m.tags_json)
    category = tags[0] if tags else "其他"
    out = add_term(
        db,
        user,
        ShenlunNormTermAdd(
            term=term,
            category=category,
            usageNote=(m.plain_note or "").strip(),
            sourceTitle=(m.source_title or m.source_type or "").strip(),
            exampleSentence=(m.rewrite or m.practice or original).strip(),
        ),
    )
    m.promoted_term_id = out.id
    if int(m.used_count or 0) <= 0:
        m.used_count = 1
    _refresh_status(m)
    db.commit()
    db.refresh(m)
    return _item_out(m)
