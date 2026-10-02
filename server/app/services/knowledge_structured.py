"""知识框架通用树草稿：稳定节点 ID、可组合内容块及发布校验。"""
from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import KnowledgeNode, KnowledgeTree, gen_id, utcnow
from app.services.knowledge_md import parse_md

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_BLOCK_TYPES = {"text", "formula", "image", "example"}


def from_markdown(db: Session, tree: KnowledgeTree) -> dict[str, Any]:
    """仅在旧草稿尚未结构化时转换；按路径沿用已发布节点 ID。"""
    parsed = parse_md(tree.md_draft or "")
    existing = {
        path: node_id
        for path, node_id in db.query(KnowledgeNode.path, KnowledgeNode.id)
        .filter(KnowledgeNode.tree_key == tree.tree_key, KnowledgeNode.archived_at.is_(None))
        .all()
    }

    def convert(node: Any) -> dict[str, Any]:
        text = (node.content or "").strip()
        return {
            "id": existing.get(node.path) or gen_id("kn"),
            "title": node.title,
            "blocks": [{"type": "text", "text": text}] if text else [],
            "children": [convert(child) for child in node.children or []],
        }

    source = parsed.tree
    return {
        "schemaVersion": 2,
        "title": tree.title,
        "description": "",
        "groups": [],
        "children": [convert(child) for child in source.children or []] if source else [],
    }


def get_draft(db: Session, tree: KnowledgeTree) -> dict[str, Any]:
    if tree.draft_tree_json:
        try:
            value = json.loads(tree.draft_tree_json)
            if isinstance(value, dict) and value.get("schemaVersion") == 2:
                return value
        except (ValueError, TypeError):
            pass
    return from_markdown(db, tree)


def validate_tree(value: Any, *, strict: bool = True) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """规范化客户端草稿；不信任客户端提供的 path、depth、content。"""
    issues: list[dict[str, str]] = []
    if not isinstance(value, dict):
        return None, [{"level": "error", "message": "知识树必须是对象"}]
    title = str(value.get("title") or "").strip()
    if not title or len(title) > 64:
        issues.append({"level": "error", "message": "科目标题须为 1–64 字"})
    description = str(value.get("description") or "").strip()[:240]
    seen: set[str] = set()
    node_count = 0

    def clean_node(raw: Any, depth: int, path: str) -> dict[str, Any] | None:
        nonlocal node_count
        if not isinstance(raw, dict):
            issues.append({"level": "error", "message": f"{path}：节点格式无效"})
            return None
        node_count += 1
        if node_count > 3000 or depth > 12:
            issues.append({"level": "error", "message": "节点超过 3000 个或深度超过 12 层"})
            return None
        node_id = str(raw.get("id") or "")
        name = str(raw.get("title") or "").strip()
        where = f"{path}/{name}" if path else name

        def add_node_issue(message: str, level: str = "error") -> None:
            issues.append({"level": level, "message": f"{where}：{message}", "path": where, "nodeId": node_id})

        if not _ID_RE.fullmatch(node_id) or node_id == "root" or node_id in seen:
            add_node_issue("节点 ID 无效或重复")
        seen.add(node_id)
        if not name or len(name) > 200:
            add_node_issue("标题须为 1–200 字")
        elif len(name) > 60:
            add_node_issue("标题较长，手机上会换行", "warning")
        blocks_raw = raw.get("blocks") or []
        if not isinstance(blocks_raw, list) or len(blocks_raw) > 40:
            add_node_issue("内容块格式无效或超过 40 个")
            blocks_raw = []
        blocks: list[dict[str, str]] = []
        for block in blocks_raw:
            if not isinstance(block, dict) or block.get("type") not in _BLOCK_TYPES:
                add_node_issue("不支持的内容块")
                continue
            typ = str(block["type"])
            cleaned = {"type": typ}
            for key in ("text", "latex", "plain", "url", "alt", "question", "answer"):
                if key in block:
                    cleaned[key] = str(block[key] or "").strip()[:10000]
            if typ == "text" and not cleaned.get("text"):
                continue
            if typ == "formula" and (not cleaned.get("plain") or not cleaned.get("latex")):
                add_node_issue("公式须填写 LaTeX 和可读式", "error" if strict else "warning")
            if typ == "image" and not (cleaned.get("url", "").startswith("https://") or re.fullmatch(r"/uploads/knowledge-media/[a-f0-9]{32}\.(png|jpg)", cleaned.get("url", ""))):
                add_node_issue("图片须上传或使用 HTTPS 地址", "error" if strict else "warning")
            if typ == "example" and not cleaned.get("question"):
                add_node_issue("例题缺少题干", "error" if strict else "warning")
            blocks.append(cleaned)
        children_raw = raw.get("children") or []
        if not isinstance(children_raw, list):
            issues.append({"level": "error", "message": f"{where}：子节点必须是数组"})
            children_raw = []
        children = [n for child in children_raw if (n := clean_node(child, depth + 1, where))]
        child_names: set[str] = set()
        for child in children:
            if child["title"] in child_names:
                child_path = f"{where}/{child['title']}" if where else child["title"]
                issues.append({"level": "error", "message": f"{child_path}：同级节点标题重复", "path": child_path, "nodeId": child["id"]})
            child_names.add(child["title"])
        return {"id": node_id, "title": name, "blocks": blocks, "children": children}

    roots_raw = value.get("children") or []
    if not isinstance(roots_raw, list):
        roots_raw = []
        issues.append({"level": "error", "message": "一级分类必须是数组"})
    roots = [n for raw in roots_raw if (n := clean_node(raw, 0, ""))]
    if not roots:
        issues.append({"level": "error", "message": "至少需要一个一级分类"})
    root_names: set[str] = set()
    for node in roots:
        if node["title"] in root_names:
            issues.append({"level": "error", "message": f"{node['title']}：一级分类标题重复", "path": node["title"], "nodeId": node["id"]})
        root_names.add(node["title"])
    groups_raw = value.get("groups") or []
    groups: list[dict[str, Any]] = []
    if isinstance(groups_raw, list):
        root_ids = {n["id"] for n in roots}
        for group in groups_raw[:20]:
            if not isinstance(group, dict):
                continue
            label = str(group.get("title") or "").strip()[:40]
            ids = [str(x) for x in group.get("nodeIds", []) if str(x) in root_ids]
            if label and ids:
                groups.append({"title": label, "nodeIds": list(dict.fromkeys(ids))})
    return {"schemaVersion": 2, "title": title, "description": description, "groups": groups, "children": roots}, issues


def with_paths(tree: dict[str, Any]) -> tuple[dict[str, Any], list[SimpleNamespace], dict[str, int]]:
    """给发布快照派生路径与层级，返回供现有知识索引使用的扁平节点。"""
    flat: list[SimpleNamespace] = []
    leaf = max_depth = 0

    def walk(raw: dict[str, Any], depth: int, parent_index: int, parent_path: str) -> dict[str, Any]:
        nonlocal leaf, max_depth
        path = f"{parent_path}/{raw['title']}" if parent_path else raw["title"]
        idx = len(flat)
        blocks = raw.get("blocks") or []
        content = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        flat.append(SimpleNamespace(id=raw["id"], title=raw["title"], depth=depth,
                                    parent_index=parent_index, sort_order=idx, line=0,
                                    path=path, content=content))
        children = [walk(child, depth + 1, idx, path) for child in raw.get("children") or []]
        if not children:
            leaf += 1
        max_depth = max(max_depth, depth)
        return {**raw, "depth": depth, "line": 0, "path": path, "content": content, "children": children or None}

    result = {**tree, "id": "root", "depth": -1, "path": "", "blocks": [],
              "children": [walk(n, 0, -1, "") for n in tree.get("children") or []]}
    return result, flat, {"nodeCount": len(flat), "leafCount": leaf, "maxDepth": max_depth}


def save_draft(db: Session, tree: KnowledgeTree, value: dict[str, Any], base_revision: int,
               *, admin_id: str = "") -> tuple[dict[str, Any] | None, str | None]:
    if int(tree.draft_revision) != int(base_revision):
        return None, "conflict"
    cleaned, issues = validate_tree(value, strict=False)
    if any(i["level"] == "error" for i in issues) or cleaned is None:
        return {"issues": issues}, "invalid"
    _, flat, _ = with_paths(cleaned)
    ids = [n.id for n in flat]
    foreign = db.query(KnowledgeNode.id).filter(KnowledgeNode.id.in_(ids), KnowledgeNode.tree_key != tree.tree_key).first()
    if foreign:
        return {"issues": [{"level": "error", "message": "节点 ID 已被其他科目使用"}]}, "invalid"
    now = utcnow()
    result = db.execute(update(KnowledgeTree).where(
        KnowledgeTree.id == tree.id, KnowledgeTree.draft_revision == base_revision
    ).values(draft_tree_json=json.dumps(cleaned, ensure_ascii=False), title=cleaned["title"],
             draft_revision=base_revision + 1, draft_updated_at=now,
             draft_updated_by=admin_id, updated_at=now))
    if result.rowcount != 1:
        db.rollback()
        return None, "conflict"
    db.commit()
    db.refresh(tree)
    return {"draftRevision": tree.draft_revision, "issues": issues, "tree": cleaned}, None
