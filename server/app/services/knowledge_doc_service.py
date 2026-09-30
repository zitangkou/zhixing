"""知识框架文档：草稿 / 预览 / 发布（按 path upsert 稳定 id）/ 导图资源上传。"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    KnowledgeNode,
    KnowledgeTree,
    KnowledgeTreeVersion,
    UserKnowledgeState,
    gen_id,
    utcnow,
)
from app.services.knowledge_md import MapNode, parse_md

_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_MAX_PNG_EDGE = 4096
_MAX_FILE_BYTES = 3 * 1024 * 1024
_MAX_TOTAL_BYTES = 30 * 1024 * 1024
_KEEP_VERSIONS = 5


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _png_size(raw: bytes) -> tuple[int, int] | None:
    if len(raw) < 24 or raw[:8] != _PNG_SIG:
        return None
    w = int.from_bytes(raw[16:20], "big")
    h = int.from_bytes(raw[20:24], "big")
    return w, h


def get_or_none_tree(db: Session, tree_key: str) -> KnowledgeTree | None:
    return db.query(KnowledgeTree).filter(KnowledgeTree.tree_key == tree_key).first()


def list_tree_metas(db: Session) -> list[dict[str, Any]]:
    trees = db.query(KnowledgeTree).order_by(KnowledgeTree.sort_order, KnowledgeTree.tree_key).all()
    # 两次聚合查询代替每棵树 2 次查询（N+1）；版本只取需要的列，不加载 md_content/tree_json
    node_counts = dict(
        db.query(KnowledgeNode.tree_key, func.count(KnowledgeNode.id))
        .filter(KnowledgeNode.archived_at.is_(None))
        .group_by(KnowledgeNode.tree_key)
        .all()
    )
    live_pairs = [(t.id, t.live_version) for t in trees if t.live_version]
    live_rows: dict[str, Any] = {}
    if live_pairs:
        rows = (
            db.query(
                KnowledgeTreeVersion.tree_id,
                KnowledgeTreeVersion.version,
                KnowledgeTreeVersion.md_sha256,
                KnowledgeTreeVersion.created_at,
            )
            .filter(KnowledgeTreeVersion.tree_id.in_([tid for tid, _ in live_pairs]))
            .filter(KnowledgeTreeVersion.version.in_({v for _, v in live_pairs}))
            .all()
        )
        wanted = set(live_pairs)
        live_rows = {r.tree_id: r for r in rows if (r.tree_id, r.version) in wanted}
    out: list[dict[str, Any]] = []
    for t in trees:
        live_n = int(node_counts.get(t.tree_key, 0))
        live_ver = live_rows.get(t.id) if t.live_version else None
        has_unpublished = False
        if t.draft_tree_json:
            live_tree = ""
            if t.live_version:
                live_row = (
                    db.query(KnowledgeTreeVersion.tree_json)
                    .filter(KnowledgeTreeVersion.tree_id == t.id,
                            KnowledgeTreeVersion.version == t.live_version)
                    .first()
                )
                live_tree = live_row[0] if live_row else ""
            if live_tree:
                try:
                    live_value = json.loads(live_tree)
                    from app.services.knowledge_structured import validate_tree
                    live_clean, _ = validate_tree(live_value)
                    draft_clean, _ = validate_tree(json.loads(t.draft_tree_json))
                    has_unpublished = draft_clean != live_clean
                except (ValueError, TypeError):
                    has_unpublished = True
            else:
                has_unpublished = True
        elif t.latest_version == 0:
            has_unpublished = bool(t.md_draft.strip())
        elif live_ver is not None:
            has_unpublished = _sha256_text(t.md_draft) != (live_ver.md_sha256 or "")
        else:
            has_unpublished = True
        out.append(
            {
                "treeKey": t.tree_key,
                "title": t.title,
                "sortOrder": t.sort_order,
                "isVisible": bool(t.is_visible),
                "draftRevision": t.draft_revision,
                "draftUpdatedAt": t.draft_updated_at,
                "latestVersion": t.latest_version,
                "liveVersion": t.live_version,
                "hasUnpublishedChanges": has_unpublished,
                "liveNodeCount": live_n,
                "livePublishedAt": live_ver.created_at if live_ver else None,
            }
        )
    return out


def create_tree(
    db: Session, tree_key: str, title: str, md: str = "", *, admin_id: str = ""
) -> KnowledgeTree | None:
    tree_key = (tree_key or "").strip()
    title = (title or "").strip() or tree_key
    if not tree_key or get_or_none_tree(db, tree_key):
        return None
    t = KnowledgeTree(
        tree_key=tree_key,
        title=title,
        md_draft=md or f"# {title}\n\n",
        draft_revision=1 if md else 0,
        draft_updated_at=utcnow() if md else None,
        draft_updated_by=admin_id,
        sort_order=db.query(KnowledgeTree).count(),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def patch_tree(db: Session, tree_key: str, data: dict[str, Any]) -> KnowledgeTree | None:
    t = get_or_none_tree(db, tree_key)
    if not t:
        return None
    if "title" in data and data["title"] is not None:
        t.title = str(data["title"]).strip() or t.title
    if "sortOrder" in data and data["sortOrder"] is not None:
        t.sort_order = int(data["sortOrder"])
    if "isVisible" in data and data["isVisible"] is not None:
        t.is_visible = bool(data["isVisible"])
    t.updated_at = utcnow()
    db.commit()
    db.refresh(t)
    return t


def get_doc(db: Session, tree_key: str) -> dict[str, Any] | None:
    t = get_or_none_tree(db, tree_key)
    if not t:
        return None
    live_md = ""
    if t.live_version:
        v = (
            db.query(KnowledgeTreeVersion)
            .filter(
                KnowledgeTreeVersion.tree_id == t.id,
                KnowledgeTreeVersion.version == t.live_version,
            )
            .first()
        )
        if v:
            live_md = v.md_content or ""
    return {
        "treeKey": t.tree_key,
        "title": t.title,
        "mdDraft": t.md_draft or "",
        "draftRevision": t.draft_revision,
        "draftUpdatedAt": t.draft_updated_at,
        "draftUpdatedBy": t.draft_updated_by or "",
        "liveVersion": t.live_version,
        "liveMd": live_md,
    }


def save_draft(
    db: Session, tree_key: str, md: str, base_revision: int, *, admin_id: str = ""
) -> tuple[dict[str, Any] | None, str | None]:
    """返回 (out, error_code) error_code=conflict|not_found"""
    t = get_or_none_tree(db, tree_key)
    if not t:
        return None, "not_found"
    if int(base_revision) != int(t.draft_revision):
        return None, "conflict"
    parsed = parse_md(md)
    t.md_draft = md
    t.draft_tree_json = ""
    t.draft_revision = int(t.draft_revision) + 1
    t.draft_updated_at = utcnow()
    t.draft_updated_by = admin_id
    t.updated_at = utcnow()
    db.commit()
    db.refresh(t)
    return {
        "draftRevision": t.draft_revision,
        "draftUpdatedAt": t.draft_updated_at,
        "issues": [i.to_dict() for i in parsed.issues],
    }, None


def preview_md(md: str) -> dict[str, Any]:
    parsed = parse_md(md)
    return {
        "title": parsed.title,
        "tree": parsed.tree.to_dict() if parsed.tree else None,
        "stats": parsed.stats,
        "issues": [i.to_dict() for i in parsed.issues],
    }


def _export_plan(tree: MapNode) -> dict[str, Any]:
    """按一级分支给出分片计划；key 为 ASCII 序号（s01、s02…），标题/路径另存。

    实际是否继续拆分由前端按渲染尺寸决定（子分片 key 形如 s01-02）。
    """

    def count(n: MapNode) -> int:
        return 1 + sum(count(c) for c in (n.children or []))

    segments = []
    for idx, child in enumerate(tree.children or [], start=1):
        segments.append(
            {
                "key": f"s{idx:02d}",
                "title": child.title,
                "rootPath": child.path or child.title,
                "nodeCount": count(child),
            }
        )
    return {"segments": segments}


def derive_nodes(db: Session, tree_key: str, flat_nodes: list, *, source_file: str = "") -> dict[str, int]:
    """结构化节点按稳定 ID 更新，旧 Markdown 按路径兼容；消失的节点归档。"""
    existing = (
        db.query(KnowledgeNode)
        .filter(KnowledgeNode.tree_key == tree_key)
        .all()
    )
    by_path = {n.path: n for n in existing if n.path}
    by_id = {n.id: n for n in existing}
    seen_ids: set[str] = set()
    id_by_index: dict[int, str] = {}
    added = kept = moved = 0

    # first pass: ensure ids for all flat nodes
    for i, fn in enumerate(flat_nodes):
        path = fn.path if hasattr(fn, "path") else fn.get("path", "")
        title = fn.title if hasattr(fn, "title") else fn["title"]
        depth = fn.depth if hasattr(fn, "depth") else fn["depth"]
        line = fn.line if hasattr(fn, "line") else fn.get("line", 0)
        content = fn.content if hasattr(fn, "content") else fn.get("content", "")
        parent_index = fn.parent_index if hasattr(fn, "parent_index") else fn["parent_index"]
        sort_order = fn.sort_order if hasattr(fn, "sort_order") else fn.get("sort_order", i)

        stable_id = fn.id if hasattr(fn, "id") else fn.get("id", "")
        old = by_id.get(stable_id) if stable_id and not stable_id.startswith("tmp-") else by_path.get(path)
        parent_id = id_by_index.get(parent_index) if parent_index >= 0 else None
        if old:
            if old.parent_id != parent_id or old.path != path:
                moved += 1
            old.title = title
            old.content = content or ""
            old.depth = depth
            old.sort_order = sort_order
            old.source_line = line
            old.source_file = source_file
            old.parent_id = parent_id
            old.path = path
            old.archived_at = None
            old.updated_at = utcnow()
            id_by_index[i] = old.id
            seen_ids.add(old.id)
            kept += 1
        else:
            nid = stable_id if stable_id and not stable_id.startswith("tmp-") else gen_id("kn")
            db.add(
                KnowledgeNode(
                    id=nid,
                    tree_key=tree_key,
                    parent_id=parent_id,
                    title=title,
                    content=content or "",
                    depth=depth,
                    sort_order=sort_order,
                    path=path,
                    source_file=source_file,
                    source_line=line,
                )
            )
            id_by_index[i] = nid
            seen_ids.add(nid)
            added += 1

    archived = 0
    now = utcnow()
    for n in existing:
        if n.id not in seen_ids and n.archived_at is None:
            n.archived_at = now
            archived += 1

    # second pass: fix parent_id now that all ids exist (for newly inserted in same flush)
    db.flush()
    for i, fn in enumerate(flat_nodes):
        parent_index = fn.parent_index if hasattr(fn, "parent_index") else fn["parent_index"]
        nid = id_by_index[i]
        node = db.get(KnowledgeNode, nid)
        if not node:
            continue
        node.parent_id = id_by_index.get(parent_index) if parent_index >= 0 else None

    return {"added": added, "archived": archived, "kept": kept, "moved": moved}


def _attach_real_ids(tree: MapNode | dict, db: Session, tree_key: str) -> Any:
    """把 live 节点的真实 id 按 path 写入树（MapNode 或 dict），读时附加，不修改版本快照。"""
    by_path = {
        p: i
        for p, i in db.query(KnowledgeNode.path, KnowledgeNode.id)
        .filter(KnowledgeNode.tree_key == tree_key, KnowledgeNode.archived_at.is_(None))
        .all()
        if p
    }

    def walk(n: Any) -> None:
        if isinstance(n, dict):
            if n.get("path") and n["path"] in by_path:
                n["id"] = by_path[n["path"]]
            for c in n.get("children") or []:
                walk(c)
        else:
            if n.path and n.path in by_path:
                n.id = by_path[n.path]
            for c in n.children or []:
                walk(c)

    if not isinstance(tree, dict) or tree.get("schemaVersion") != 2:
        walk(tree)
    return tree


def preview_node_diff(db: Session, tree_key: str, flat_nodes: list) -> dict[str, int]:
    """只读：与当前 live 派生节点比较，预估激活后的变化。"""
    live = {
        node_id: path
        for node_id, path in db.query(KnowledgeNode.id, KnowledgeNode.path)
        .filter(KnowledgeNode.tree_key == tree_key, KnowledgeNode.archived_at.is_(None))
        .all()
        if path
    }
    matched: set[str] = set()
    by_path = {path: node_id for node_id, path in live.items()}
    for node in flat_nodes:
        nid = getattr(node, "id", "")
        found = nid if nid in live else (by_path.get(node.path) if not nid or nid.startswith("tmp-") else None)
        if found:
            matched.add(found)
    kept = len(matched)
    return {"added": len(flat_nodes) - kept, "archived": len(live) - kept, "kept": kept}


def publish_tree(
    db: Session,
    tree_key: str,
    base_revision: int,
    *,
    note: str = "",
    admin_id: str = "",
) -> tuple[dict[str, Any] | None, str | None, list[dict] | None]:
    """把草稿固化为不可变版本（不改 live、不派生节点）。

    返回 (result, error_code, issues). error: not_found|conflict|invalid
    """
    from sqlalchemy.exc import IntegrityError

    t = get_or_none_tree(db, tree_key)
    if not t:
        return None, "not_found", None
    if int(base_revision) != int(t.draft_revision):
        return None, "conflict", None
    structured = bool(t.draft_tree_json)
    if structured:
        from app.services.knowledge_structured import validate_tree, with_paths

        cleaned, issues = validate_tree(json.loads(t.draft_tree_json))
        if cleaned is None or any(i["level"] == "error" for i in issues):
            return None, "invalid", issues
        tree_snapshot, flat_nodes, stats = with_paths(cleaned)
    else:
        parsed = parse_md(t.md_draft or "")
        if parsed.has_errors:
            return None, "invalid", [i.to_dict() for i in parsed.issues]
        tree_snapshot = parsed.tree.to_dict() if parsed.tree else {}
        flat_nodes = parsed.nodes
        stats = parsed.stats
        issues = [i.to_dict() for i in parsed.issues]

    version = int(t.latest_version) + 1
    ver = KnowledgeTreeVersion(
        tree_id=t.id,
        version=version,
        md_content=t.md_draft or "",
        md_sha256=_sha256_text(t.md_draft or ""),
        tree_json=json.dumps(tree_snapshot, ensure_ascii=False),
        node_count=stats.get("nodeCount", 0),
        leaf_count=stats.get("leafCount", 0),
        max_depth=stats.get("maxDepth", 0),
        note=note or "",
        created_by=admin_id,
        assets_ready=False,
    )
    db.add(ver)
    t.latest_version = version
    t.updated_at = utcnow()
    try:
        db.commit()
    except IntegrityError:
        # 并发发布撞 (tree_id, version) 唯一约束
        db.rollback()
        return None, "conflict", None
    db.refresh(ver)

    return {
        "version": version,
        "tree": tree_snapshot,
        "stats": stats,
        "nodeDiffPreview": preview_node_diff(db, tree_key, flat_nodes),
        "exportPlan": {"segments": []} if structured else _export_plan(parsed.tree) if parsed.tree else {"segments": []},
        "issues": issues,
    }, None, None


def activate_version(
    db: Session,
    tree_key: str,
    version: int,
    *,
    admin_id: str = "",
    allow_no_assets: bool = False,
    expected_live: int | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """把某个版本切为 live：此刻才按 path upsert 派生 knowledge_nodes（保留 id，消失的归档）。

    error: not_found | assets_not_ready | invalid | conflict
    """
    t = get_or_none_tree(db, tree_key)
    if not t:
        return None, "not_found"
    ver = (
        db.query(KnowledgeTreeVersion)
        .filter(KnowledgeTreeVersion.tree_id == t.id, KnowledgeTreeVersion.version == version)
        .first()
    )
    if not ver:
        return None, "not_found"
    if not ver.assets_ready and not allow_no_assets:
        return None, "assets_not_ready"
    if expected_live is not None and int(t.live_version or 0) != int(expected_live):
        return None, "conflict"
    snapshot = json.loads(ver.tree_json or "{}")
    if snapshot.get("schemaVersion") == 2:
        from app.services.knowledge_structured import validate_tree, with_paths

        cleaned, issues = validate_tree(snapshot)
        if cleaned is None or any(i["level"] == "error" for i in issues):
            return None, "invalid"
        _, flat_nodes, _ = with_paths(cleaned)
    else:
        parsed = parse_md(ver.md_content or "")
        if parsed.has_errors:
            return None, "invalid"
        flat_nodes = parsed.nodes
    node_diff = derive_nodes(db, tree_key, flat_nodes, source_file=f"v{version}")
    prev = int(t.live_version or 0)
    t.live_version = version
    t.updated_at = utcnow()
    db.commit()
    return {"treeKey": tree_key, "liveVersion": version, "previousLive": prev, "nodeDiff": node_diff}, None


# ---------------------------------------------------------------------------
# 导图资源上传：先全部校验（内存中），再写临时目录，最后原子替换版本目录
# ---------------------------------------------------------------------------

_ASSET_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,95}\.(png|svg|json)$")
_SEGMENT_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
_MAX_THUMB_EDGE = 1024
_MAX_SEGMENTS = 80
_SVG_ALLOWED_TAGS = {
    "svg", "g", "path", "circle", "ellipse", "line", "polyline", "polygon", "rect",
    "text", "tspan", "style", "title", "desc", "defs", "clipPath",
}
_SVG_NS = "http://www.w3.org/2000/svg"
_XLINK_NS = "http://www.w3.org/1999/xlink"
_CSS_DANGER = re.compile(r"@import|expression\s*\(|javascript:|behavior\s*:|url\s*\(\s*(?!['\"]?#)", re.I)


def _assets_root() -> Path:
    """知识导图资源根目录；测试中可 monkeypatch。"""
    from app.upload_paths import UPLOADS_DIR

    return UPLOADS_DIR / "knowledge"


def _asset_url(tree_id: str, version: int, name: str) -> str:
    return f"/uploads/knowledge/{tree_id}/v{version}/{name}"


def validate_svg(raw: bytes) -> str | None:
    """返回错误码；None 表示安全。

    允许 xmlns（svg / xlink 命名空间），禁止：DOCTYPE/ENTITY、脚本与 foreignObject 等非白名单元素、
    on* 事件属性、非 #锚点 的 href、样式中的外链 url()/@import/javascript:。
    """
    import xml.etree.ElementTree as ET

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "bad_svg_encoding"
    if re.search(r"<!DOCTYPE|<!ENTITY", text, re.I):
        return "bad_svg_doctype"
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return "bad_svg_xml"
    for el in root.iter():
        tag = el.tag
        if not isinstance(tag, str):
            continue
        ns, _, local = tag[1:].partition("}") if tag.startswith("{") else ("", "", tag)
        if ns not in ("", _SVG_NS) or local not in _SVG_ALLOWED_TAGS:
            return f"bad_svg_tag:{local}"
        for attr, val in el.attrib.items():
            a_ns, _, a_local = attr[1:].partition("}") if attr.startswith("{") else ("", "", attr)
            if a_ns not in ("", _XLINK_NS):
                return "bad_svg_attr_ns"
            low = a_local.lower()
            v = (val or "").strip()
            if low.startswith("on"):
                return "bad_svg_event_attr"
            if low == "href" and v and not v.startswith("#"):
                return "bad_svg_href"
            if re.search(r"javascript:|data:", v, re.I):
                return "bad_svg_attr_value"
            if low == "style" and _CSS_DANGER.search(v):
                return "bad_svg_style"
        if local == "style" and _CSS_DANGER.search(el.text or ""):
            return "bad_svg_style"
    root_local = root.tag.split("}", 1)[-1] if isinstance(root.tag, str) else ""
    if root_local != "svg":
        return "bad_svg_root"
    return None


def _check_png(raw: bytes, *, max_edge: int) -> tuple[int, int]:
    if len(raw) > _MAX_FILE_BYTES:
        raise ValueError("file_too_large")
    size = _png_size(raw)
    if not size:
        raise ValueError("bad_png")
    w, h = size
    if w <= 0 or h <= 0 or max(w, h) > max_edge:
        raise ValueError("png_too_big")
    return w, h


def _safe_asset_name(name: Any) -> str:
    n = str(name or "")
    if n != Path(n).name or "/" in n or "\\" in n or ".." in n:
        raise ValueError("bad_name")
    if not _ASSET_NAME_RE.match(n):
        raise ValueError("bad_name")
    return n


def _clip(v: Any, n: int) -> str:
    return str(v or "")[:n]


def _plan_assets(
    manifest: dict[str, Any], files: dict[str, bytes], tree_id: str, version: int
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """纯校验：返回 (服务端重建的 manifest, 需写入的 name->bytes)。任何问题抛 ValueError。"""
    for name in files:
        _safe_asset_name(name)
    to_write: dict[str, bytes] = {}

    def need(name_val: Any, kind: str) -> tuple[str, bytes]:
        name = _safe_asset_name(name_val)
        if name not in files:
            raise ValueError(f"missing_file:{name}")
        ext = name.rsplit(".", 1)[-1]
        if kind == "png" and ext != "png":
            raise ValueError("bad_type")
        if kind == "svg" and ext != "svg":
            raise ValueError("bad_type")
        if kind == "json" and ext != "json":
            raise ValueError("bad_type")
        return name, files[name]

    def image_meta(meta: Any, *, key: str | None = None) -> dict[str, Any]:
        if not isinstance(meta, dict):
            raise ValueError("bad_manifest")
        name, raw = need(meta.get("url"), "png")
        w, h = _check_png(raw, max_edge=_MAX_PNG_EDGE)
        sha = _sha256_bytes(raw)
        if meta.get("sha256") and meta.get("sha256") != sha:
            raise ValueError("sha_mismatch")
        out: dict[str, Any] = {
            "url": _asset_url(tree_id, version, name),
            "width": w,
            "height": h,
            "bytes": len(raw),
            "sha256": sha,
        }
        to_write[name] = raw
        if meta.get("thumbUrl"):
            tname, traw = need(meta.get("thumbUrl"), "png")
            tw, th = _check_png(traw, max_edge=_MAX_THUMB_EDGE)
            out.update(
                {"thumbUrl": _asset_url(tree_id, version, tname), "thumbWidth": tw, "thumbHeight": th}
            )
            to_write[tname] = traw
        if key is not None:
            out["key"] = key
        return out

    written: dict[str, Any] = {
        "version": version,
        "generatedAt": _clip(manifest.get("generatedAt"), 40),
        "theme": _clip(manifest.get("theme"), 32),
        "scale": float(manifest.get("scale") or 0) if isinstance(manifest.get("scale"), (int, float)) else 0,
    }
    if manifest.get("overview"):
        written["overview"] = image_meta(manifest["overview"])

    segs_in = manifest.get("segments") or []
    if not isinstance(segs_in, list) or len(segs_in) > _MAX_SEGMENTS:
        raise ValueError("bad_segments")
    segs: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for seg in segs_in:
        if not isinstance(seg, dict):
            raise ValueError("bad_segments")
        key = str(seg.get("key") or "")
        if not _SEGMENT_KEY_RE.match(key) or key in seen_keys:
            raise ValueError("bad_segment_key")
        seen_keys.add(key)
        m = image_meta(seg, key=key)
        m["title"] = _clip(seg.get("title"), 200)
        m["rootPath"] = _clip(seg.get("rootPath"), 1000)
        m["nodeCount"] = int(seg.get("nodeCount") or 0)
        segs.append(m)
    written["segments"] = segs

    svg_meta = manifest.get("svg")
    if svg_meta:
        if not isinstance(svg_meta, dict):
            raise ValueError("bad_manifest")
        name, raw = need(svg_meta.get("url"), "svg")
        if len(raw) > _MAX_FILE_BYTES:
            raise ValueError("file_too_large")
        err = validate_svg(raw)
        if err:
            raise ValueError(err)
        written["svg"] = {"url": _asset_url(tree_id, version, name), "bytes": len(raw)}
        to_write[name] = raw

    tj = manifest.get("treeJsonUrl")
    if tj:
        name, raw = need(tj, "json")
        if len(raw) > _MAX_FILE_BYTES:
            raise ValueError("file_too_large")
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("bad_json") from None
        if not isinstance(parsed, dict):
            raise ValueError("bad_json")
        written["treeJsonUrl"] = _asset_url(tree_id, version, name)
        to_write[name] = raw

    if not written.get("overview") and not segs:
        raise ValueError("no_images")
    return written, to_write


def _write_version_dir(tree_id: str, version: int, to_write: dict[str, bytes]) -> None:
    """写入临时目录后原子替换 v{n}/；失败时旧目录保持不变。"""
    import uuid

    base = _assets_root() / tree_id
    base.mkdir(parents=True, exist_ok=True)
    dest = base / f"v{version}"
    tmp = base / f".v{version}.tmp-{uuid.uuid4().hex[:8]}"
    old = base / f".v{version}.old-{uuid.uuid4().hex[:8]}"
    tmp.mkdir()
    try:
        for name, raw in to_write.items():
            target = (tmp / name).resolve()
            if target.parent != tmp.resolve():
                raise ValueError("bad_name")
            target.write_bytes(raw)
        if dest.exists():
            dest.rename(old)
        tmp.rename(dest)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        if old.exists() and not dest.exists():
            old.rename(dest)
        raise
    shutil.rmtree(old, ignore_errors=True)


def save_version_assets(
    db: Session,
    tree_key: str,
    version: int,
    *,
    manifest: dict[str, Any],
    files: dict[str, bytes],
    activate: bool = True,
    admin_id: str = "",
) -> tuple[dict[str, Any] | None, str]:
    """校验并保存某版本的导图资源；成功后 assets_ready=True，activate 时切为 live 并派生节点。"""
    t = get_or_none_tree(db, tree_key)
    if not t:
        return None, "not_found"
    ver = (
        db.query(KnowledgeTreeVersion)
        .filter(KnowledgeTreeVersion.tree_id == t.id, KnowledgeTreeVersion.version == version)
        .first()
    )
    if not ver:
        return None, "not_found"
    if not isinstance(manifest, dict):
        return None, "bad_manifest"
    if sum(len(b) for b in files.values()) > _MAX_TOTAL_BYTES:
        return None, "too_large"
    try:
        written_manifest, to_write = _plan_assets(manifest, files, t.id, version)
        _write_version_dir(t.id, version, to_write)
    except ValueError as e:
        return None, str(e)

    ver.manifest_json = json.dumps(written_manifest, ensure_ascii=False)
    ver.assets_ready = True
    t.updated_at = utcnow()
    db.commit()

    node_diff = None
    if activate:
        res, err = activate_version(db, tree_key, version, admin_id=admin_id)
        if err:
            return None, err
        node_diff = (res or {}).get("nodeDiff")
    db.refresh(t)
    _cleanup_old_versions(db, t)
    return {
        "version": version,
        "liveVersion": t.live_version,
        "manifest": written_manifest,
        "nodeDiff": node_diff,
    }, ""


def _cleanup_old_versions(db: Session, t: KnowledgeTree) -> None:
    """只清理资源目录（版本行永不删除）。保留：live、latest、最近 _KEEP_VERSIONS 个版本。"""
    vers = (
        db.query(KnowledgeTreeVersion.version)
        .filter(KnowledgeTreeVersion.tree_id == t.id)
        .order_by(KnowledgeTreeVersion.version.desc())
        .all()
    )
    all_versions = [v for (v,) in vers]
    keep = set(all_versions[:_KEEP_VERSIONS]) | {int(t.live_version or 0), int(t.latest_version or 0)}
    base = _assets_root() / t.id
    if not base.is_dir():
        return
    for d in base.iterdir():
        if not d.is_dir():
            continue
        m = re.fullmatch(r"v(\d+)", d.name)
        if m:
            if int(m.group(1)) not in keep:
                shutil.rmtree(d, ignore_errors=True)
        elif d.name.startswith((".v",)):
            # 残留临时目录
            shutil.rmtree(d, ignore_errors=True)


def list_versions(db: Session, tree_key: str) -> list[dict[str, Any]]:
    t = get_or_none_tree(db, tree_key)
    if not t:
        return []
    rows = (
        db.query(KnowledgeTreeVersion)
        .filter(KnowledgeTreeVersion.tree_id == t.id)
        .order_by(KnowledgeTreeVersion.version.desc())
        .all()
    )
    return [
        {
            "version": v.version,
            "note": v.note,
            "createdAt": v.created_at,
            "createdBy": v.created_by,
            "nodeCount": v.node_count,
            "assetsReady": bool(v.assets_ready),
            "isLive": int(v.version) == int(t.live_version or 0),
        }
        for v in rows
    ]


def get_version(db: Session, tree_key: str, version: int) -> dict[str, Any] | None:
    t = get_or_none_tree(db, tree_key)
    if not t:
        return None
    v = (
        db.query(KnowledgeTreeVersion)
        .filter(KnowledgeTreeVersion.tree_id == t.id, KnowledgeTreeVersion.version == version)
        .first()
    )
    if not v:
        return None
    manifest = {}
    if v.manifest_json:
        try:
            manifest = json.loads(v.manifest_json)
        except json.JSONDecodeError:
            manifest = {}
    tree = {}
    if v.tree_json:
        try:
            tree = json.loads(v.tree_json)
        except json.JSONDecodeError:
            tree = {}
    return {
        "version": v.version,
        "md": v.md_content,
        "manifest": manifest,
        "tree": tree,
        "assetsReady": bool(v.assets_ready),
        "note": v.note,
        "createdAt": v.created_at,
    }


def rollback_version_to_draft(db: Session, tree_key: str, version: int, *, admin_id: str = "") -> dict | None:
    detail = get_version(db, tree_key, version)
    if not detail:
        return None
    t = get_or_none_tree(db, tree_key)
    assert t
    t.md_draft = detail["md"]
    tree_snapshot = detail.get("tree") or {}
    if tree_snapshot.get("schemaVersion") == 2:
        from app.services.knowledge_structured import validate_tree

        cleaned, _ = validate_tree(tree_snapshot)
        t.draft_tree_json = json.dumps(cleaned, ensure_ascii=False) if cleaned else ""
    else:
        t.draft_tree_json = ""
    t.draft_revision = int(t.draft_revision) + 1
    t.draft_updated_at = utcnow()
    t.draft_updated_by = admin_id
    db.commit()
    return get_doc(db, tree_key)


def draft_has_unpublished_changes(db: Session, t: KnowledgeTree) -> bool:
    """草稿非空且与最新已发布版本的 md 不一致（或从未发布）。"""
    if not (t.md_draft or "").strip() and not t.draft_tree_json:
        return False
    latest = (
        db.query(KnowledgeTreeVersion)
        .filter(KnowledgeTreeVersion.tree_id == t.id)
        .order_by(KnowledgeTreeVersion.version.desc())
        .first()
    )
    if t.draft_tree_json:
        from app.services.knowledge_structured import validate_tree
        if latest is None:
            return True
        draft, _ = validate_tree(json.loads(t.draft_tree_json), strict=False)
        live, _ = validate_tree(json.loads(latest.tree_json or "{}"), strict=False)
        return draft != live
    return latest is None or latest.md_content != t.md_draft


def import_md_to_draft(
    db: Session,
    tree_key: str,
    title: str,
    md: str,
    *,
    admin_id: str = "",
    publish: bool = False,
    force: bool = False,
    keep_unpublished: bool = False,
) -> dict[str, Any]:
    """导入 md 为草稿。

    - force=False：已有非空草稿则拒绝（error=exists），用于 CLI 初次导入。
    - force=True, keep_unpublished=True：草稿有未发布修改时拒绝（error=draft_dirty），
      供后台上传/目录同步使用，需二次确认后再以 keep_unpublished=False 覆盖。
    - 内容与现有草稿一致时不改动（不升 revision）。
    """
    t = get_or_none_tree(db, tree_key)
    if t and not force and t.md_draft.strip():
        return {"ok": False, "error": "exists", "treeKey": tree_key}
    if t and t.md_draft == md and not t.draft_tree_json:
        return {"ok": True, "treeKey": tree_key, "draftRevision": t.draft_revision, "unchanged": True}
    if t and keep_unpublished and draft_has_unpublished_changes(db, t):
        return {"ok": False, "error": "draft_dirty", "treeKey": tree_key, "draftRevision": t.draft_revision}
    if not t:
        t = create_tree(db, tree_key, title, md=md, admin_id=admin_id)
        if not t:
            return {"ok": False, "error": "create_failed"}
    else:
        t.md_draft = md
        t.draft_tree_json = ""
        t.title = title or t.title
        t.draft_revision = int(t.draft_revision) + 1
        t.draft_updated_at = utcnow()
        t.draft_updated_by = admin_id
        db.commit()
        db.refresh(t)
    result: dict[str, Any] = {"ok": True, "treeKey": tree_key, "draftRevision": t.draft_revision}
    if publish:
        # 只固化版本；上线需在后台生成图片后激活（或显式 activate_version）
        pub, err, issues = publish_tree(db, tree_key, t.draft_revision, admin_id=admin_id, note="import")
        if err:
            result["publishError"] = err
            result["issues"] = issues
        elif pub:
            result["version"] = pub["version"]
            result["nodeDiffPreview"] = pub.get("nodeDiffPreview")
    return result


def public_tree_keys(db: Session) -> list[str]:
    """学员端可见的知识树：is_visible 且已有 live 版本（按排序）。"""
    return [
        k
        for (k,) in db.query(KnowledgeTree.tree_key)
        .filter(KnowledgeTree.is_visible.is_(True), KnowledgeTree.live_version > 0)
        .order_by(KnowledgeTree.sort_order, KnowledgeTree.tree_key)
        .all()
    ]


def list_public_maps(db: Session) -> list[dict[str, Any]]:
    trees = (
        db.query(KnowledgeTree)
        .filter(KnowledgeTree.is_visible.is_(True), KnowledgeTree.live_version > 0)
        .order_by(KnowledgeTree.sort_order, KnowledgeTree.tree_key)
        .all()
    )
    out = []
    for t in trees:
        v = (
            db.query(KnowledgeTreeVersion)
            .filter(
                KnowledgeTreeVersion.tree_id == t.id,
                KnowledgeTreeVersion.version == t.live_version,
            )
            .first()
        )
        if not v:
            continue
        manifest = {}
        if v.manifest_json:
            try:
                manifest = json.loads(v.manifest_json)
            except json.JSONDecodeError:
                pass
        cover = None
        overview = manifest.get("overview") if isinstance(manifest, dict) else None
        if isinstance(overview, dict) and (overview.get("thumbUrl") or overview.get("url")):
            cover = {
                "url": overview.get("thumbUrl") or overview.get("url"),
                "width": overview.get("thumbWidth") or overview.get("width") or 0,
                "height": overview.get("thumbHeight") or overview.get("height") or 0,
            }
        out.append(
            {
                "treeKey": t.tree_key,
                "title": (json.loads(v.tree_json or "{}").get("title") or t.title),
                "version": t.live_version,
                "publishedAt": v.created_at,
                "nodeCount": v.node_count,
                "cover": cover,
            }
        )
    return out


def get_public_map(db: Session, tree_key: str) -> dict[str, Any] | None:
    t = get_or_none_tree(db, tree_key)
    if not t or not t.is_visible or t.live_version <= 0:
        return None
    detail = get_version(db, tree_key, t.live_version)
    if not detail:
        return None
    tree = detail.get("tree") or {}
    if tree:
        _attach_real_ids(tree, db, tree_key)
    return {
        "treeKey": t.tree_key,
        "title": tree.get("title") or t.title,
        "version": t.live_version,
        "publishedAt": detail.get("createdAt"),
        "tree": tree,
        "manifest": detail.get("manifest") or {},
    }


def upsert_user_state(
    db: Session,
    user_id: str,
    node_id: str,
    *,
    my_note: str | None = None,
    is_starred: bool | None = None,
) -> UserKnowledgeState | None:
    node = db.get(KnowledgeNode, node_id)
    if not node or node.archived_at is not None:
        return None
    st = (
        db.query(UserKnowledgeState)
        .filter(UserKnowledgeState.user_id == user_id, UserKnowledgeState.node_id == node_id)
        .first()
    )
    if not st:
        st = UserKnowledgeState(
            user_id=user_id,
            node_id=node_id,
            tree_key=node.tree_key,
            path=node.path or "",
        )
        db.add(st)
    if my_note is not None:
        st.my_note = my_note
    if is_starred is not None:
        st.is_starred = bool(is_starred)
    st.tree_key = node.tree_key
    st.path = node.path or ""
    st.updated_at = utcnow()
    db.commit()
    db.refresh(st)
    return st


def get_user_states_map(db: Session, user_id: str, node_ids: list[str]) -> dict[str, UserKnowledgeState]:
    if not user_id or not node_ids:
        return {}
    rows = (
        db.query(UserKnowledgeState)
        .filter(UserKnowledgeState.user_id == user_id, UserKnowledgeState.node_id.in_(node_ids))
        .all()
    )
    return {r.node_id: r for r in rows}
