"""知识框架 service：读取派生节点树（学员/管理端）、知识关联解析。

写入统一走 knowledge_doc_service（md 草稿 → 版本 → 激活时派生节点）。
旧的 sync_knowledge（整表删除重建）与节点 CRUD（含物理删除）已移除，避免断开关联。
以下为历史说明：

md 结构支持：
- `#` 文档标题（跳过，不进树；可用文件名作 tree_key）
- `##` / `###` / `####` … 作为层级标题（## = 第 1 层）
- 标题下的 `- ` / `1.` 列表作为子节点（缩进继续加深）
- 标题/节点下的普通段落写入上一节点 content（便于以后放公式说明）

知识库目录优先级：
1. 配置 KNOWLEDGE_KB_DIR（settings.knowledge_kb_dir，部署时指向挂载目录 / 开发时指向 Obsidian）
2. 后端 data/knowledge/ fallback（上传 md 落地处）

学员个人状态（备注/星标/掌握度/复习进度）只读写 user_knowledge_state。
knowledge_nodes 上的旧字段 my_note / is_starred / mastery_level / next_review_at /
review_count / last_reviewed_at 已废弃：按产品决定旧笔记与进度直接丢弃，不迁移、不回读，
也没有任何启动时/自动迁移（列仅为兼容老库而保留）。
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import KnowledgeNode, UserKnowledgeState
from app.schemas import KnowledgeNodeOut, KnowledgeTreeOut

# 后端本地 fallback 目录（上传 md 落地处、部署时也可挂载这里）
LOCAL_KB = Path(__file__).resolve().parents[2] / "data" / "knowledge"

# tree_key -> 中文标题（可由 md 文件名 stem 推导，也允许动态新增）
TREE_TITLES = {
    "申论": "申论",
    "申论题型": "申论",
    "判断推理": "判断推理",
    "常识判断": "常识判断",
    "数量关系": "数量关系",
    "言语理解": "言语理解",
    "言语理解与表达": "言语理解与表达",
    "资料分析": "资料分析",
}


def _resolve_kb_dir() -> Path | None:
    """按优先级解析知识库目录"""
    cfg_dir = get_settings().knowledge_kb_dir.strip()
    if cfg_dir and Path(cfg_dir).is_dir():
        return Path(cfg_dir)
    # 本地 fallback：要有 md 文件才算
    if LOCAL_KB.is_dir() and any(LOCAL_KB.glob("*.md")):
        return LOCAL_KB
    return None


def _parse_md_to_tree(content: str, tree_key: str = "", source_file: str = "") -> list[dict]:
    """解析 md 为扁平节点列表；实现见 knowledge_md.parse_md。"""
    from app.services.knowledge_md import parse_md_to_legacy_flat

    return parse_md_to_legacy_flat(content, tree_key=tree_key, source_file=source_file)


def _build_path(parent_path: str | None, title: str) -> str:
    if not parent_path:
        return title
    return f"{parent_path}/{title}"


def _user_state_map(db: Session, user_id: str | None, tree_key: str | None = None) -> dict[str, UserKnowledgeState]:
    if not user_id:
        return {}
    q = db.query(UserKnowledgeState).filter(UserKnowledgeState.user_id == user_id)
    if tree_key:
        q = q.filter(UserKnowledgeState.tree_key == tree_key)
    return {s.node_id: s for s in q.all()}


def _node_to_out(
    n: KnowledgeNode,
    children_map: dict[str | None, list[KnowledgeNode]],
    states: dict[str, UserKnowledgeState] | None = None,
) -> KnowledgeNodeOut:
    children = children_map.get(n.id, [])
    st = (states or {}).get(n.id)
    return KnowledgeNodeOut(
        id=n.id,
        treeKey=n.tree_key,
        parentId=n.parent_id,
        title=n.title,
        content=n.content or "",
        myNote=(st.my_note if st else "") or "",
        isStarred=bool(st.is_starred) if st else False,
        masteryLevel=(st.mastery_level if st else None) or "new",
        nextReviewAt=st.next_review_at if st else None,
        reviewCount=int(st.review_count or 0) if st else 0,
        lastReviewedAt=st.last_reviewed_at if st else None,
        depth=n.depth,
        sortOrder=n.sort_order,
        path=n.path or "",
        sourceFile=n.source_file or "",
        children=[_node_to_out(c, children_map, states) for c in children] if children else None,
    )


def _tree_titles(db: Session) -> dict[str, str]:
    from app.models import KnowledgeTree

    return {k: t for k, t in db.query(KnowledgeTree.tree_key, KnowledgeTree.title).all()}


def list_trees(
    db: Session, *, user_id: str | None = None, visible_only: bool = False
) -> list[KnowledgeTreeOut]:
    """列出知识树（按 tree_key 分组，组成树形结构）；用户状态按本人合并。

    visible_only=True（学员端）时只返回 is_visible 且已上线的树，避免泄露隐藏树/遗留 tree_key。
    """
    q = db.query(KnowledgeNode).filter(KnowledgeNode.archived_at.is_(None))
    allowed: list[str] | None = None
    if visible_only:
        from app.services.knowledge_doc_service import public_tree_keys

        allowed = public_tree_keys(db)
        if not allowed:
            return []
        q = q.filter(KnowledgeNode.tree_key.in_(allowed))
    all_nodes = q.order_by(KnowledgeNode.tree_key, KnowledgeNode.sort_order).all()
    by_tree: dict[str, list[KnowledgeNode]] = {}
    tree_keys_in_order: list[str] = []
    for n in all_nodes:
        if n.tree_key not in by_tree:
            tree_keys_in_order.append(n.tree_key)
        by_tree.setdefault(n.tree_key, []).append(n)
    if allowed is not None:
        tree_keys_in_order = [k for k in allowed if k in by_tree]

    titles = _tree_titles(db)
    states = _user_state_map(db, user_id)
    out: list[KnowledgeTreeOut] = []
    for tree_key in tree_keys_in_order:
        nodes = by_tree.get(tree_key, [])
        if not nodes:
            continue
        children_map: dict[str | None, list[KnowledgeNode]] = {}
        for n in nodes:
            children_map.setdefault(n.parent_id, []).append(n)
        roots = children_map.get(None, [])
        out.append(
            KnowledgeTreeOut(
                treeKey=tree_key,
                title=titles.get(tree_key) or TREE_TITLES.get(tree_key, tree_key),
                nodes=[_node_to_out(r, children_map, states) for r in roots],
            )
        )
    return out


def get_tree(
    db: Session, tree_key: str, *, user_id: str | None = None, visible_only: bool = False
) -> KnowledgeTreeOut | None:
    if visible_only:
        from app.services.knowledge_doc_service import public_tree_keys

        if tree_key not in public_tree_keys(db):
            return None
    nodes = (
        db.query(KnowledgeNode)
        .filter(KnowledgeNode.tree_key == tree_key, KnowledgeNode.archived_at.is_(None))
        .order_by(KnowledgeNode.sort_order)
        .all()
    )
    if not nodes:
        return None
    children_map: dict[str | None, list[KnowledgeNode]] = {}
    for n in nodes:
        children_map.setdefault(n.parent_id, []).append(n)
    roots = children_map.get(None, [])
    states = _user_state_map(db, user_id, tree_key)
    return KnowledgeTreeOut(
        treeKey=tree_key,
        title=_tree_titles(db).get(tree_key) or TREE_TITLES.get(tree_key, tree_key),
        nodes=[_node_to_out(r, children_map, states) for r in roots],
    )


def save_uploaded_md(filename: str, content: bytes) -> tuple[str | None, str | None]:
    """把上传的 md 保存到 LOCAL_KB，返回 (路径, 错误)"""
    if not filename.endswith(".md"):
        return None, "仅支持 .md 文件"
    # 安全：只取文件名，不要路径
    safe_name = Path(filename).name
    if not safe_name or safe_name.startswith("."):
        return None, "文件名不合法"
    LOCAL_KB.mkdir(parents=True, exist_ok=True)
    dest = LOCAL_KB / safe_name
    dest.write_bytes(content)
    return str(dest), None


def sync_status(db: Session) -> dict:
    """返回当前同步状态"""
    counts: dict[str, int] = {}
    for n in db.query(KnowledgeNode).all():
        counts[n.tree_key] = counts.get(n.tree_key, 0) + 1
    kb_dir = _resolve_kb_dir()
    return {
        "kb_dir": str(kb_dir) if kb_dir else "",
        "kb_exists": kb_dir is not None,
        "local_kb_dir": str(LOCAL_KB),
        "tree_counts": counts,
        "tree_titles": dict(TREE_TITLES),
    }


# 行测科目短名 → 知识树 tree_key（优先匹配）
SUBJECT_TREE_KEYS: dict[str, list[str]] = {
    "常识": ["常识判断"],
    "言语": ["言语理解与表达", "言语理解"],
    "数量": ["数量关系"],
    "判断": ["判断推理"],
    "资料": ["资料分析"],
    "申论": ["申论", "申论题型"],
}


def resolve_knowledge_ref(
    db: Session,
    *,
    node_id: str | None = None,
    tree_key: str | None = None,
    path: str | None = None,
) -> tuple[str | None, str, str]:
    """解析并规范化知识关联，返回 (node_id, tree_key, path)。

    优先用 node_id；若 id 因重同步失效，则按 (tree_key, path) 重绑。
    """
    nid = (node_id or "").strip() or None
    tk = (tree_key or "").strip()
    p = (path or "").strip()

    if nid:
        n = db.get(KnowledgeNode, nid)
        if n:
            return n.id, n.tree_key or tk, n.path or p

    if p:
        q = db.query(KnowledgeNode).filter(KnowledgeNode.path == p)
        if tk:
            q = q.filter(KnowledgeNode.tree_key == tk)
        n = q.first()
        if n:
            return n.id, n.tree_key or tk, n.path or p
        # path 可能带了 tree 前缀
        if "/" in p and not tk:
            head, rest = p.split("/", 1)
            n = (
                db.query(KnowledgeNode)
                .filter(KnowledgeNode.tree_key == head, KnowledgeNode.path == rest)
                .first()
            )
            if n:
                return n.id, n.tree_key, n.path or rest

    return nid, tk, p
