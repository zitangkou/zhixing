"""知识框架 service：解析 md -> KnowledgeNode 树，支持节点 CRUD 与备注保留

md 结构支持：
- `#` 文档标题（跳过，不进树；可用文件名作 tree_key）
- `##` / `###` / `####` … 作为层级标题（## = 第 1 层）
- 标题下的 `- ` / `1.` 列表作为子节点（缩进继续加深）
- 标题/节点下的普通段落写入上一节点 content（便于以后放公式说明）

知识库目录优先级：
1. 配置 KNOWLEDGE_KB_DIR（settings.knowledge_kb_dir，部署时指向挂载目录 / 开发时指向 Obsidian）
2. 后端 data/knowledge/ fallback（上传 md 落地处）

同步策略：merge 而非 delete+rebuild，按 (tree_key, path) 匹配保留
my_note / is_starred / mastery_level / next_review_at / review_count / last_reviewed_at。
"""
from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import KnowledgeNode, gen_id
from app.schemas import KnowledgeNodeCreate, KnowledgeNodeOut, KnowledgeNodeUpdate, KnowledgeTreeOut

# 同步时按 path 保留的 App 侧字段
_PRESERVE_FIELDS = (
    "my_note",
    "is_starred",
    "mastery_level",
    "next_review_at",
    "review_count",
    "last_reviewed_at",
)

# 后端本地 fallback 目录（上传 md 落地处、部署时也可挂载这里）
LOCAL_KB = Path(__file__).resolve().parents[2] / "data" / "knowledge"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LIST_RE = re.compile(r"^([-*+]|\d+\.)\s+")

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


def _strip_md(text: str) -> str:
    """去掉 md 行的 `- `、`*`、`**`、`[[]]` 等标记，返回纯文本"""
    s = text.strip()
    s = re.sub(r"^[-*+]\s+", "", s)
    s = re.sub(r"^\d+\.\s+", "", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"\[\[(.+?)(?:\|(.+?))?\]\]", lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s.strip()


def _append_content(node: dict, text: str) -> None:
    t = text.strip()
    if not t:
        return
    prev = (node.get("content") or "").rstrip()
    node["content"] = f"{prev}\n{t}".strip() if prev else t


def _parse_md_to_tree(content: str, tree_key: str = "", source_file: str = "") -> list[dict]:
    """解析 md 为扁平节点列表（含 parent_index / depth / sort_order / line / content）

    层级规则：
    - `#` 文档标题跳过
    - `##` depth=0，`###` depth=1，`####` depth=2 …
    - 列表项挂在当前标题下：depth = 标题depth + 1 + 缩进层级
    - 纯列表文档（无标题）仍按缩进解析，兼容旧 md
    """
    nodes: list[dict] = []
    stack: list[tuple[int, int]] = []  # (depth, node_index)
    last_heading_depth = -1

    def add_node(title: str, depth: int, line_no: int) -> int:
        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent_index = stack[-1][1] if stack else -1
        node = {
            "title": title,
            "depth": depth,
            "parent_index": parent_index,
            "sort_order": len(nodes),
            "line": line_no,
            "content": "",
        }
        idx = len(nodes)
        nodes.append(node)
        stack.append((depth, idx))
        return idx

    for line_no, raw in enumerate(content.splitlines(), start=1):
        stripped = raw.lstrip(" ")
        if not stripped:
            continue
        if stripped.startswith("---"):
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            title = _strip_md(heading.group(2))
            if not title:
                continue
            # 单级 # 视为文档名，不进树
            if level == 1:
                continue
            depth = level - 2  # ## -> 0
            add_node(title, depth, line_no)
            last_heading_depth = depth
            continue

        indent = len(raw) - len(stripped)
        if _LIST_RE.match(stripped):
            title = _strip_md(stripped)
            if not title:
                continue
            # 有标题上下文：列表挂在当前标题下；否则纯列表按缩进
            if last_heading_depth >= 0:
                depth = last_heading_depth + 1 + (indent // 2)
            else:
                depth = indent // 2
            add_node(title, depth, line_no)
            continue

        # 普通段落 / 公式行：记入最近节点 content
        if nodes and not stripped.startswith("<!--"):
            _append_content(nodes[-1], stripped)

    return nodes


def _build_path(parent_path: str | None, title: str) -> str:
    if not parent_path:
        return title
    return f"{parent_path}/{title}"


def _preserved_from_node(n: KnowledgeNode) -> dict:
    return {
        "my_note": n.my_note or "",
        "is_starred": bool(n.is_starred),
        "mastery_level": n.mastery_level or "new",
        "next_review_at": n.next_review_at,
        "review_count": int(n.review_count or 0),
        "last_reviewed_at": n.last_reviewed_at,
    }


def sync_knowledge(db: Session, force: bool = False, only_tree_key: str | None = None) -> dict:
    """从知识库目录同步 md 到数据库（merge 模式，保留 App 侧字段）

    force 参数预留，目前 merge 总是会执行。
    only_tree_key 只同步某一棵树（上传单个 md 时用）。
    """
    kb_dir = _resolve_kb_dir()
    if not kb_dir:
        return {"error": "知识库目录不存在，请设置 KNOWLEDGE_KB_DIR 或上传 md"}

    result: dict[str, int] = {}
    md_files = sorted(kb_dir.glob("*.md"))
    if only_tree_key:
        md_files = [f for f in md_files if f.stem == only_tree_key]

    # 私人健康笔记勿进知识框架（文件名含关键词则跳过）
    _HEALTH_SKIP = ("心理和身体", "恢复计划", "健康日记", "湿气", "湿疹")

    for md_file in md_files:
        tree_key = md_file.stem  # 用文件名 stem 作为 tree_key，允许任意主题
        if any(k in tree_key for k in _HEALTH_SKIP):
            continue
        # 注册标题（若未在 TREE_TITLES 里，用 stem 作标题）
        TREE_TITLES.setdefault(tree_key, tree_key)

        # 读旧节点：按 path 索引保留 App 侧字段
        old_nodes = (
            db.query(KnowledgeNode)
            .filter(KnowledgeNode.tree_key == tree_key)
            .all()
        )
        old_by_path: dict[str, dict] = {}
        for n in old_nodes:
            if n.path:
                old_by_path[n.path] = _preserved_from_node(n)

        # 解析新 md
        content = md_file.read_text(encoding="utf-8")
        parsed = _parse_md_to_tree(content, tree_key, md_file.name)

        # 先建 id，再补 parent_id / path
        id_to_node: dict[str, dict] = {}
        for n in parsed:
            n["id"] = gen_id("kn")
            id_to_node[n["id"]] = n

        # 删除旧节点：用原生 SQL 整批删除，规避 ORM 外键级联检查
        from sqlalchemy import text as _text

        db.execute(_text("UPDATE knowledge_nodes SET parent_id = NULL WHERE tree_key = :tk"), {"tk": tree_key})
        db.execute(_text("DELETE FROM knowledge_nodes WHERE tree_key = :tk"), {"tk": tree_key})
        db.commit()

        # 插入新节点，按 path 保留 App 侧字段
        # 需要先建父节点再建子节点，按 sort_order 顺序即可（解析时父在前）
        path_by_id: dict[str, str] = {}
        for n in parsed:
            parent_id = None
            parent_path = None
            if n["parent_index"] >= 0:
                parent_id = parsed[n["parent_index"]]["id"]
                parent_path = path_by_id.get(parent_id)
            title = n["title"]
            path = _build_path(parent_path, title)
            path_by_id[n["id"]] = path
            n["parent_id"] = parent_id
            n["path"] = path

            old = old_by_path.get(path) or {}
            kwargs = {k: old.get(k) for k in _PRESERVE_FIELDS}
            kwargs.setdefault("my_note", "")
            kwargs.setdefault("is_starred", False)
            kwargs.setdefault("mastery_level", "new")
            kwargs.setdefault("review_count", 0)

            db.add(
                KnowledgeNode(
                    id=n["id"],
                    tree_key=tree_key,
                    parent_id=parent_id,
                    title=title,
                    content=n["content"],
                    depth=n["depth"],
                    sort_order=n["sort_order"],
                    path=path,
                    source_file=md_file.name,
                    source_line=n["line"],
                    **kwargs,
                )
            )
        db.commit()
        result[tree_key] = len(parsed)

    return result


def _node_to_out(n: KnowledgeNode, children_map: dict[str | None, list[KnowledgeNode]]) -> KnowledgeNodeOut:
    children = children_map.get(n.id, [])
    return KnowledgeNodeOut(
        id=n.id,
        treeKey=n.tree_key,
        parentId=n.parent_id,
        title=n.title,
        content=n.content or "",
        myNote=n.my_note or "",
        isStarred=bool(n.is_starred),
        masteryLevel=n.mastery_level or "new",
        nextReviewAt=n.next_review_at,
        reviewCount=int(n.review_count or 0),
        lastReviewedAt=n.last_reviewed_at,
        depth=n.depth,
        sortOrder=n.sort_order,
        path=n.path or "",
        sourceFile=n.source_file or "",
        children=[_node_to_out(c, children_map) for c in children] if children else None,
    )


def list_trees(db: Session) -> list[KnowledgeTreeOut]:
    """列出所有知识树（按 tree_key 分组，组成树形结构）"""
    all_nodes = db.query(KnowledgeNode).order_by(KnowledgeNode.tree_key, KnowledgeNode.sort_order).all()
    by_tree: dict[str, list[KnowledgeNode]] = {}
    tree_keys_in_order: list[str] = []
    for n in all_nodes:
        if n.tree_key not in by_tree:
            tree_keys_in_order.append(n.tree_key)
        by_tree.setdefault(n.tree_key, []).append(n)

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
                title=TREE_TITLES.get(tree_key, tree_key),
                nodes=[_node_to_out(r, children_map) for r in roots],
            )
        )
    return out


def get_tree(db: Session, tree_key: str) -> KnowledgeTreeOut | None:
    nodes = (
        db.query(KnowledgeNode)
        .filter(KnowledgeNode.tree_key == tree_key)
        .order_by(KnowledgeNode.sort_order)
        .all()
    )
    if not nodes:
        return None
    children_map: dict[str | None, list[KnowledgeNode]] = {}
    for n in nodes:
        children_map.setdefault(n.parent_id, []).append(n)
    roots = children_map.get(None, [])
    return KnowledgeTreeOut(
        treeKey=tree_key,
        title=TREE_TITLES.get(tree_key, tree_key),
        nodes=[_node_to_out(r, children_map) for r in roots],
    )


def update_node(db: Session, node_id: str, body: KnowledgeNodeUpdate) -> KnowledgeNodeOut | None:
    n = db.get(KnowledgeNode, node_id)
    if not n:
        return None
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        key = {"myNote": "my_note", "isStarred": "is_starred"}.get(k, k)
        setattr(n, key, v)
    db.commit()
    db.refresh(n)
    return KnowledgeNodeOut(
        id=n.id,
        treeKey=n.tree_key,
        parentId=n.parent_id,
        title=n.title,
        content=n.content or "",
        myNote=n.my_note or "",
        isStarred=bool(n.is_starred),
        masteryLevel=n.mastery_level or "new",
        nextReviewAt=n.next_review_at,
        reviewCount=int(n.review_count or 0),
        lastReviewedAt=n.last_reviewed_at,
        depth=n.depth,
        sortOrder=n.sort_order,
        path=n.path or "",
        sourceFile=n.source_file or "",
    )


def create_node(db: Session, body: KnowledgeNodeCreate) -> KnowledgeNodeOut | None:
    """手动新增一个节点（不来自 md）"""
    tree_key = body.treeKey
    TREE_TITLES.setdefault(tree_key, tree_key)
    # 父节点
    parent_path = None
    depth = 0
    if body.parentId:
        parent = db.get(KnowledgeNode, body.parentId)
        if not parent or parent.tree_key != tree_key:
            return None
        parent_path = parent.path or parent.title
        depth = parent.depth + 1
    # 排序取末尾
    max_order = (
        db.query(KnowledgeNode)
        .filter(KnowledgeNode.tree_key == tree_key)
        .count()
    )
    path = _build_path(parent_path, body.title)
    n = KnowledgeNode(
        id=gen_id("kn"),
        tree_key=tree_key,
        parent_id=body.parentId,
        title=body.title,
        content=body.content,
        my_note="",
        is_starred=False,
        depth=depth,
        sort_order=max_order,
        path=path,
        source_file="",
        source_line=0,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return KnowledgeNodeOut(
        id=n.id,
        treeKey=n.tree_key,
        parentId=n.parent_id,
        title=n.title,
        content=n.content or "",
        myNote=n.my_note or "",
        isStarred=bool(n.is_starred),
        masteryLevel=n.mastery_level or "new",
        nextReviewAt=n.next_review_at,
        reviewCount=int(n.review_count or 0),
        lastReviewedAt=n.last_reviewed_at,
        depth=n.depth,
        sortOrder=n.sort_order,
        path=n.path or "",
        sourceFile=n.source_file or "",
    )


def delete_node(db: Session, node_id: str) -> bool:
    """删除节点及其所有子孙"""
    n = db.get(KnowledgeNode, node_id)
    if not n:
        return False
    # 收集所有子孙 id（BFS）
    to_delete: list[str] = [node_id]
    pending = [node_id]
    while pending:
        pid = pending.pop()
        children = db.query(KnowledgeNode).filter(KnowledgeNode.parent_id == pid).all()
        for c in children:
            to_delete.append(c.id)
            pending.append(c.id)
    # 用 SQL 逐条删除，规避外键
    from sqlalchemy import text as _text

    db.execute(_text("UPDATE knowledge_nodes SET parent_id = NULL WHERE tree_key = :tk"), {"tk": n.tree_key})
    for cid in to_delete:
        db.execute(_text("DELETE FROM knowledge_nodes WHERE id = :id"), {"id": cid})
    db.commit()
    return True


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
