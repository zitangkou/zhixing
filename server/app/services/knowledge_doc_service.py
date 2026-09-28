"""知识框架文档：草稿 / 预览 / 发布（按 path upsert 稳定 id）/ 导图资源上传。"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

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
from app.upload_paths import uploads_subdir

_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_MAX_PNG_EDGE = 4096
_MAX_FILE_BYTES = 3 * 1024 * 1024
_MAX_TOTAL_BYTES = 30 * 1024 * 1024
_KEEP_VERSIONS = 5
_SVG_DANGER = re.compile(r"<script|on\w+\s*=|https?://", re.I)


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
    out: list[dict[str, Any]] = []
    for t in trees:
        live_n = (
            db.query(KnowledgeNode)
            .filter(KnowledgeNode.tree_key == t.tree_key, KnowledgeNode.archived_at.is_(None))
            .count()
        )
        live_ver = (
            db.query(KnowledgeTreeVersion)
            .filter(
                KnowledgeTreeVersion.tree_id == t.id,
                KnowledgeTreeVersion.version == t.live_version,
            )
            .first()
            if t.live_version
            else None
        )
        has_unpublished = False
        if t.latest_version == 0:
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
    segments = []
    for child in tree.children or []:
        def count(n: MapNode) -> int:
            return 1 + sum(count(c) for c in (n.children or []))

        segments.append(
            {
                "key": f"seg-{child.path.replace('/', '-')}" if child.path else f"seg-{child.title}",
                "title": child.title,
                "rootPath": child.path or child.title,
                "nodeCount": count(child),
            }
        )
    return {"segments": segments}


def derive_nodes(db: Session, tree_key: str, flat_nodes: list, *, source_file: str = "") -> dict[str, int]:
    """按 (tree_key, path) upsert；消失的 path 置 archived_at。"""
    existing = (
        db.query(KnowledgeNode)
        .filter(KnowledgeNode.tree_key == tree_key)
        .all()
    )
    by_path = {n.path: n for n in existing if n.path}
    seen_paths: set[str] = set()
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

        seen_paths.add(path)
        old = by_path.get(path)
        parent_id = id_by_index.get(parent_index) if parent_index >= 0 else None
        if old:
            old.title = title
            old.content = content or ""
            old.depth = depth
            old.sort_order = sort_order
            old.source_line = line
            old.source_file = source_file
            old.parent_id = parent_id
            old.archived_at = None
            old.updated_at = utcnow()
            id_by_index[i] = old.id
            kept += 1
            if old.parent_id != parent_id:
                moved += 1
        else:
            nid = gen_id("kn")
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
            added += 1

    archived = 0
    now = utcnow()
    for path, n in by_path.items():
        if path not in seen_paths and n.archived_at is None:
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


def _attach_real_ids(tree: MapNode, db: Session, tree_key: str) -> MapNode:
    by_path = {
        n.path: n.id
        for n in db.query(KnowledgeNode)
        .filter(KnowledgeNode.tree_key == tree_key, KnowledgeNode.archived_at.is_(None))
        .all()
        if n.path
    }

    def walk(n: MapNode) -> None:
        if n.path and n.path in by_path:
            n.id = by_path[n.path]
        for c in n.children or []:
            walk(c)

    walk(tree)
    return tree


def publish_tree(
    db: Session,
    tree_key: str,
    base_revision: int,
    *,
    note: str = "",
    admin_id: str = "",
) -> tuple[dict[str, Any] | None, str | None, list[dict] | None]:
    """返回 (result, error_code, issues). error: not_found|conflict|invalid"""
    t = get_or_none_tree(db, tree_key)
    if not t:
        return None, "not_found", None
    if int(base_revision) != int(t.draft_revision):
        return None, "conflict", None
    parsed = parse_md(t.md_draft or "")
    if parsed.has_errors:
        return None, "invalid", [i.to_dict() for i in parsed.issues]

    version = int(t.latest_version) + 1
    node_diff = derive_nodes(db, tree_key, parsed.nodes, source_file=f"publish-v{version}")
    if parsed.tree:
        _attach_real_ids(parsed.tree, db, tree_key)

    ver = KnowledgeTreeVersion(
        tree_id=t.id,
        version=version,
        md_content=t.md_draft or "",
        md_sha256=_sha256_text(t.md_draft or ""),
        tree_json=json.dumps(parsed.tree.to_dict() if parsed.tree else {}, ensure_ascii=False),
        node_count=parsed.stats.get("nodeCount", 0),
        leaf_count=parsed.stats.get("leafCount", 0),
        max_depth=parsed.stats.get("maxDepth", 0),
        note=note or "",
        created_by=admin_id,
        assets_ready=False,
    )
    db.add(ver)
    t.latest_version = version
    t.updated_at = utcnow()
    db.commit()
    db.refresh(ver)

    return {
        "version": version,
        "tree": parsed.tree.to_dict() if parsed.tree else None,
        "stats": parsed.stats,
        "nodeDiff": node_diff,
        "exportPlan": _export_plan(parsed.tree) if parsed.tree else {"segments": []},
        "issues": [i.to_dict() for i in parsed.issues],
    }, None, None


def save_version_assets(
    db: Session,
    tree_key: str,
    version: int,
    *,
    manifest: dict[str, Any],
    files: dict[str, bytes],
) -> tuple[dict[str, Any] | None, str]:
    """files: filename -> bytes. 成功后 assets_ready=True 且 live_version=version。"""
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

    total = sum(len(b) for b in files.values())
    if total > _MAX_TOTAL_BYTES:
        return None, "too_large"

    dest = uploads_subdir("knowledge", t.id, f"v{version}")
    # clean previous files for this version dir
    if dest.exists():
        for p in dest.iterdir():
            if p.is_file():
                p.unlink()

    written_manifest = dict(manifest)
    written_manifest["version"] = version

    def store_asset(meta: dict[str, Any] | None, kind: str) -> dict[str, Any] | None:
        if not meta:
            return meta
        url_name = Path(str(meta.get("url", ""))).name
        if not url_name or url_name not in files:
            # allow thumbUrl similarly
            return meta
        raw = files[url_name]
        if len(raw) > _MAX_FILE_BYTES:
            raise ValueError("file_too_large")
        if url_name.endswith(".png"):
            if raw[:8] != _PNG_SIG:
                raise ValueError("bad_png")
            size = _png_size(raw)
            if not size:
                raise ValueError("bad_png")
            w, h = size
            if max(w, h) > _MAX_PNG_EDGE:
                raise ValueError("png_too_big")
            meta["width"] = w
            meta["height"] = h
            meta["bytes"] = len(raw)
            expect = meta.get("sha256")
            got = _sha256_bytes(raw)
            if expect and expect != got:
                raise ValueError("sha_mismatch")
            meta["sha256"] = got
        elif url_name.endswith(".svg"):
            text = raw.decode("utf-8", errors="ignore")
            if _SVG_DANGER.search(text):
                raise ValueError("bad_svg")
            meta["bytes"] = len(raw)
        elif url_name.endswith(".json"):
            json.loads(raw.decode("utf-8"))
            meta["bytes"] = len(raw)
        else:
            raise ValueError("bad_type")
        (dest / url_name).write_bytes(raw)
        meta["url"] = f"/uploads/knowledge/{t.id}/v{version}/{url_name}"
        thumb = meta.get("thumbUrl")
        if thumb:
            thumb_name = Path(str(thumb)).name
            if thumb_name in files:
                tr = files[thumb_name]
                if tr[:8] != _PNG_SIG or len(tr) > _MAX_FILE_BYTES:
                    raise ValueError("bad_thumb")
                (dest / thumb_name).write_bytes(tr)
                meta["thumbUrl"] = f"/uploads/knowledge/{t.id}/v{version}/{thumb_name}"
                ts = _png_size(tr)
                if ts:
                    meta["thumbWidth"], meta["thumbHeight"] = ts
        return meta

    try:
        if "overview" in written_manifest:
            written_manifest["overview"] = store_asset(written_manifest.get("overview"), "overview")
        segs = []
        for seg in written_manifest.get("segments") or []:
            segs.append(store_asset(seg, "segment"))
        written_manifest["segments"] = segs
        if written_manifest.get("svg"):
            written_manifest["svg"] = store_asset(written_manifest.get("svg"), "svg")
        # tree json file optional
        tj = written_manifest.get("treeJsonUrl")
        if tj:
            name = Path(str(tj)).name
            if name in files:
                (dest / name).write_bytes(files[name])
                written_manifest["treeJsonUrl"] = f"/uploads/knowledge/{t.id}/v{version}/{name}"
    except ValueError as e:
        return None, str(e)

    ver.manifest_json = json.dumps(written_manifest, ensure_ascii=False)
    ver.assets_ready = True
    t.live_version = version
    t.updated_at = utcnow()
    db.commit()

    _cleanup_old_versions(db, t)
    return {
        "version": version,
        "liveVersion": t.live_version,
        "manifest": written_manifest,
    }, ""


def _cleanup_old_versions(db: Session, t: KnowledgeTree) -> None:
    vers = (
        db.query(KnowledgeTreeVersion)
        .filter(KnowledgeTreeVersion.tree_id == t.id)
        .order_by(KnowledgeTreeVersion.version.desc())
        .all()
    )
    for old in vers[_KEEP_VERSIONS:]:
        d = Path(__file__).resolve().parents[2] / "data" / "uploads" / "knowledge" / t.id / f"v{old.version}"
        if d.is_dir():
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
    t.draft_revision = int(t.draft_revision) + 1
    t.draft_updated_at = utcnow()
    t.draft_updated_by = admin_id
    db.commit()
    return get_doc(db, tree_key)


def import_md_to_draft(
    db: Session,
    tree_key: str,
    title: str,
    md: str,
    *,
    admin_id: str = "",
    publish: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    t = get_or_none_tree(db, tree_key)
    if t and not force and t.md_draft.strip():
        return {"ok": False, "error": "exists", "treeKey": tree_key}
    if not t:
        t = create_tree(db, tree_key, title, md=md, admin_id=admin_id)
        if not t:
            return {"ok": False, "error": "create_failed"}
    else:
        t.md_draft = md
        t.title = title or t.title
        t.draft_revision = int(t.draft_revision) + 1
        t.draft_updated_at = utcnow()
        t.draft_updated_by = admin_id
        db.commit()
        db.refresh(t)
    result: dict[str, Any] = {"ok": True, "treeKey": tree_key, "draftRevision": t.draft_revision}
    if publish:
        pub, err, issues = publish_tree(db, tree_key, t.draft_revision, admin_id=admin_id, note="import")
        if err:
            result["publishError"] = err
            result["issues"] = issues
        else:
            # import without assets still sets latest; mark live so maps can show outline
            t2 = get_or_none_tree(db, tree_key)
            if t2 and pub:
                t2.live_version = pub["version"]
                t2.is_visible = True
                db.commit()
                result["version"] = pub["version"]
                result["nodeDiff"] = pub.get("nodeDiff")
    return result


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
                "title": t.title,
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
    return {
        "treeKey": t.tree_key,
        "title": t.title,
        "version": t.live_version,
        "publishedAt": detail.get("createdAt"),
        "tree": detail.get("tree") or {},
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
