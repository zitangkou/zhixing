from pathlib import Path

from fastapi import File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.admin._deps import *  # noqa: F401,F403
from app.schemas import (
    KnowledgeDocPutBody,
    KnowledgePreviewBody,
    KnowledgePublishBody,
    KnowledgeTreeCreateBody,
    KnowledgeTreePatchBody,
)
from app.services import knowledge_doc_service as docs

router = APIRouter()


def _admin_id(admin) -> str:
    return getattr(admin, "id", "") or ""


@router.get("/knowledge/trees")
def admin_knowledge_trees(_admin=Depends(require_permission("knowledge:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(docs.list_tree_metas(db))


@router.post("/knowledge/trees")
def admin_knowledge_create_tree(
    body: KnowledgeTreeCreateBody,
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    t = docs.create_tree(db, body.treeKey, body.title, body.md or "", admin_id=_admin_id(admin))
    if not t:
        return ApiResponse.fail("创建失败（treeKey 为空或已存在）", code=400)
    meta = next((m for m in docs.list_tree_metas(db) if m["treeKey"] == t.tree_key), None)
    return ApiResponse.ok(meta)


@router.patch("/knowledge/trees/{tree_key}")
def admin_knowledge_patch_tree(
    tree_key: str,
    body: KnowledgeTreePatchBody,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    t = docs.patch_tree(db, tree_key, body.model_dump(exclude_unset=True))
    if not t:
        return ApiResponse.fail("知识树不存在", code=404)
    meta = next((m for m in docs.list_tree_metas(db) if m["treeKey"] == tree_key), None)
    return ApiResponse.ok(meta)


@router.delete("/knowledge/trees/{tree_key}")
def admin_knowledge_delete_tree_doc(
    tree_key: str,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    from app.models import KnowledgeNode, utcnow

    t = docs.get_or_none_tree(db, tree_key)
    if not t:
        return ApiResponse.fail("知识树不存在", code=404)
    now = utcnow()
    for n in db.query(KnowledgeNode).filter(KnowledgeNode.tree_key == tree_key, KnowledgeNode.archived_at.is_(None)):
        n.archived_at = now
    t.is_visible = False
    db.commit()
    return ApiResponse.ok({"ok": True, "treeKey": tree_key})


@router.get("/knowledge/trees/{tree_key}/doc")
def admin_knowledge_get_doc(
    tree_key: str,
    _admin=Depends(require_permission("knowledge:read")),
    db: Session = Depends(get_db),
):
    doc = docs.get_doc(db, tree_key)
    if not doc:
        return ApiResponse.fail("知识树不存在", code=404)
    return ApiResponse.ok(doc)


@router.put("/knowledge/trees/{tree_key}/doc")
def admin_knowledge_put_doc(
    tree_key: str,
    body: KnowledgeDocPutBody,
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    out, err = docs.save_draft(db, tree_key, body.md, body.baseRevision, admin_id=_admin_id(admin))
    if err == "not_found":
        return ApiResponse.fail("知识树不存在", code=404)
    if err == "conflict":
        return ApiResponse.fail("草稿已被他人更新，请重新加载", code=409)
    return ApiResponse.ok(out)


@router.post("/knowledge/preview")
def admin_knowledge_preview(
    body: KnowledgePreviewBody,
    _admin=Depends(require_permission("knowledge:write")),
):
    return ApiResponse.ok(docs.preview_md(body.md))


@router.post("/knowledge/trees/{tree_key}/publish")
def admin_knowledge_publish(
    tree_key: str,
    body: KnowledgePublishBody,
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    out, err, issues = docs.publish_tree(
        db, tree_key, body.baseRevision, note=body.note or "", admin_id=_admin_id(admin)
    )
    if err == "not_found":
        return ApiResponse.fail("知识树不存在", code=404)
    if err == "conflict":
        return ApiResponse.fail("草稿版本冲突，请重新加载", code=409)
    if err == "invalid":
        return ApiResponse.fail("存在错误级校验问题，无法发布", code=400, data={"issues": issues})
    return ApiResponse.ok(out)


@router.post("/knowledge/trees/{tree_key}/versions/{version}/assets")
async def admin_knowledge_upload_assets(
    tree_key: str,
    version: int,
    manifest: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    import json

    try:
        man = json.loads(manifest)
    except json.JSONDecodeError:
        return ApiResponse.fail("manifest 不是合法 JSON", code=400)
    blob: dict[str, bytes] = {}
    for f in files:
        name = Path(f.filename or "").name
        if not name:
            continue
        raw = await f.read()
        blob[name] = raw
    out, err = docs.save_version_assets(db, tree_key, version, manifest=man, files=blob)
    if err == "not_found":
        return ApiResponse.fail("版本不存在", code=404)
    if err:
        return ApiResponse.fail(f"资源校验失败: {err}", code=400)
    return ApiResponse.ok(out)


@router.get("/knowledge/trees/{tree_key}/versions")
def admin_knowledge_versions(
    tree_key: str,
    _admin=Depends(require_permission("knowledge:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(docs.list_versions(db, tree_key))


@router.get("/knowledge/trees/{tree_key}/versions/{version}")
def admin_knowledge_version_detail(
    tree_key: str,
    version: int,
    _admin=Depends(require_permission("knowledge:read")),
    db: Session = Depends(get_db),
):
    detail = docs.get_version(db, tree_key, version)
    if not detail:
        return ApiResponse.fail("版本不存在", code=404)
    return ApiResponse.ok(detail)


@router.post("/knowledge/trees/{tree_key}/versions/{version}/rollback")
def admin_knowledge_rollback(
    tree_key: str,
    version: int,
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    doc = docs.rollback_version_to_draft(db, tree_key, version, admin_id=_admin_id(admin))
    if not doc:
        return ApiResponse.fail("版本不存在", code=404)
    return ApiResponse.ok(doc)


@router.get("/knowledge/tree/{tree_key}")
def admin_knowledge_tree_detail(
    tree_key: str,
    _admin=Depends(require_permission("knowledge:read")),
    db: Session = Depends(get_db),
):
    t = get_knowledge_tree(db, tree_key)
    if not t:
        return ApiResponse.fail("知识树不存在", code=404)
    return ApiResponse.ok(t.model_dump())


@router.get("/knowledge/status")
def admin_knowledge_status(_admin=Depends(require_permission("knowledge:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(knowledge_sync_status(db))


@router.post("/knowledge/sync")
def admin_knowledge_sync_as_import(
    tree_key: str | None = None,
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    from app.services.knowledge_service import _resolve_kb_dir

    kb = _resolve_kb_dir()
    if not kb:
        return ApiResponse.fail("知识库目录不存在，请设置 KNOWLEDGE_KB_DIR 或上传 md", code=400)
    results = []
    files = sorted(kb.glob("*.md"))
    if tree_key:
        files = [f for f in files if f.stem == tree_key]
    for f in files:
        md = f.read_text(encoding="utf-8")
        results.append(
            docs.import_md_to_draft(
                db, f.stem, f.stem, md, admin_id=_admin_id(admin), publish=False, force=True
            )
        )
    return ApiResponse.ok({"imports": results})


@router.post("/knowledge/upload-md")
async def admin_knowledge_upload_md(
    file: UploadFile = File(...),
    sync: bool = True,
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    if not raw:
        return ApiResponse.fail("文件为空", code=400)
    if len(raw) > 1 * 1024 * 1024:
        return ApiResponse.fail("md 文件不能超过 1MB", code=400)
    name = file.filename or ""
    saved_path, err = save_uploaded_md(name, raw)
    if err:
        return ApiResponse.fail(err, code=400)
    tree_key = Path(name).stem
    md = raw.decode("utf-8", errors="ignore")
    imp = docs.import_md_to_draft(
        db, tree_key, tree_key, md, admin_id=_admin_id(admin), publish=False, force=True
    )
    return ApiResponse.ok({"savedPath": saved_path, "treeKey": tree_key, "import": imp, "sync": sync})


@router.post("/knowledge/node")
def admin_knowledge_create_node(
    body: KnowledgeNodeCreate,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    out = create_knowledge_node(db, body)
    if not out:
        return ApiResponse.fail("创建失败，父节点不存在或不匹配", code=400)
    return ApiResponse.ok(out.model_dump())


@router.put("/knowledge/node/{node_id}")
def admin_knowledge_update_node(
    node_id: str,
    body: KnowledgeNodeUpdate,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    out = update_knowledge_node(db, node_id, body)
    if not out:
        return ApiResponse.fail("节点不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/knowledge/node/{node_id}")
def admin_knowledge_delete_node(
    node_id: str,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    if not delete_knowledge_node(db, node_id):
        return ApiResponse.fail("节点不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.delete("/knowledge/tree/{tree_key}")
def admin_knowledge_delete_tree_legacy(
    tree_key: str,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    return admin_knowledge_delete_tree_doc(tree_key, _admin=_admin, db=db)
