from pathlib import Path

from fastapi import File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.admin._deps import *  # noqa: F401,F403
from app.schemas import (
    KnowledgeActivateBody,
    KnowledgeDocPutBody,
    KnowledgePreviewBody,
    KnowledgePublishBody,
    KnowledgeTreeCreateBody,
    KnowledgeTreePatchBody,
)
from app.services import knowledge_doc_service as docs

router = APIRouter()


class StructuredDraftBody(BaseModel):
    tree: dict
    baseRevision: int


class StructuredPreviewBody(BaseModel):
    tree: dict
    treeKey: str = ""


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


@router.get("/knowledge/trees/{tree_key}/structured")
def admin_knowledge_structured_draft(
    tree_key: str,
    _admin=Depends(require_permission("knowledge:read")),
    db: Session = Depends(get_db),
):
    from app.services.knowledge_structured import get_draft, validate_tree

    tree = docs.get_or_none_tree(db, tree_key)
    if not tree:
        return ApiResponse.fail("知识树不存在", code=404)
    draft = get_draft(db, tree)
    _, issues = validate_tree(draft)
    return ApiResponse.ok({"tree": draft, "draftRevision": tree.draft_revision, "issues": issues})


@router.put("/knowledge/trees/{tree_key}/structured")
def admin_knowledge_save_structured(
    tree_key: str,
    body: StructuredDraftBody,
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    from app.services.knowledge_structured import save_draft

    tree = docs.get_or_none_tree(db, tree_key)
    if not tree:
        return ApiResponse.fail("知识树不存在", code=404)
    out, err = save_draft(db, tree, body.tree, body.baseRevision, admin_id=_admin_id(admin))
    if err == "conflict":
        return ApiResponse.fail("草稿已被他人更新，请重新加载", code=409)
    if err == "invalid":
        return ApiResponse.fail("草稿存在错误", code=400, data=out)
    return ApiResponse.ok(out)


@router.post("/knowledge/structured-preview")
def admin_knowledge_structured_preview(
    body: StructuredPreviewBody,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    from app.services.knowledge_structured import validate_tree, with_paths

    cleaned, issues = validate_tree(body.tree)
    if cleaned is None:
        return ApiResponse.ok({"tree": None, "issues": issues, "stats": {}})
    snapshot, flat, stats = with_paths(cleaned)
    diff = docs.preview_node_diff(db, body.treeKey, flat) if body.treeKey else None
    return ApiResponse.ok({"tree": snapshot, "issues": issues, "stats": stats, "nodeDiffPreview": diff})


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


_MAX_UPLOAD_FILE = 3 * 1024 * 1024
_MAX_UPLOAD_FILES = 200


@router.post("/knowledge/trees/{tree_key}/versions/{version}/assets")
def admin_knowledge_upload_assets(
    tree_key: str,
    version: int,
    manifest: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    activate: bool = True,
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    """同步函数：FastAPI 在线程池执行，避免阻塞事件循环。"""
    import json

    try:
        man = json.loads(manifest)
    except json.JSONDecodeError:
        return ApiResponse.fail("manifest 不是合法 JSON", code=400)
    if len(files) > _MAX_UPLOAD_FILES:
        return ApiResponse.fail("文件数量过多", code=400)
    blob: dict[str, bytes] = {}
    for f in files:
        name = f.filename or ""
        if not name:
            continue
        raw = f.file.read(_MAX_UPLOAD_FILE + 1)
        if len(raw) > _MAX_UPLOAD_FILE:
            return ApiResponse.fail(f"文件过大: {Path(name).name}", code=400)
        # 名称合法性（ASCII/后缀白名单/无路径）在 service 内统一校验
        blob[name] = raw
    out, err = docs.save_version_assets(
        db, tree_key, version, manifest=man, files=blob, activate=activate, admin_id=_admin_id(admin)
    )
    if err == "not_found":
        return ApiResponse.fail("版本不存在", code=404)
    if err:
        return ApiResponse.fail(f"资源校验失败: {err}", code=400)
    return ApiResponse.ok(out)


@router.post("/knowledge/trees/{tree_key}/versions/{version}/activate")
def admin_knowledge_activate(
    tree_key: str,
    version: int,
    body: KnowledgeActivateBody | None = None,
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    """把已生成图片的版本设为线上（回滚上线也用它，不新建版本）；此时才派生节点。"""
    b = body or KnowledgeActivateBody()
    out, err = docs.activate_version(
        db,
        tree_key,
        version,
        admin_id=_admin_id(admin),
        allow_no_assets=bool(b.allowNoAssets),
        expected_live=b.expectedLive,
    )
    if err == "not_found":
        return ApiResponse.fail("版本不存在", code=404)
    if err == "assets_not_ready":
        return ApiResponse.fail("该版本图片未生成，不能上线", code=400)
    if err == "conflict":
        return ApiResponse.fail("线上版本已被他人切换，请刷新", code=409)
    if err:
        return ApiResponse.fail(f"激活失败: {err}", code=400)
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
    force: bool = False,
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
                db, f.stem, f.stem, md, admin_id=_admin_id(admin), publish=False, force=True,
                keep_unpublished=not force,
            )
        )
    return ApiResponse.ok({"imports": results})


@router.post("/knowledge/upload-md")
async def admin_knowledge_upload_md(
    file: UploadFile = File(...),
    sync: bool = True,
    force: bool = False,
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    if not raw:
        return ApiResponse.fail("文件为空", code=400)
    if len(raw) > 1 * 1024 * 1024:
        return ApiResponse.fail("md 文件不能超过 1MB", code=400)
    name = file.filename or ""
    tree_key = Path(name).stem
    md = raw.decode("utf-8", errors="ignore")
    existing = docs.get_or_none_tree(db, tree_key)
    if (
        not force
        and existing is not None
        and existing.md_draft != md
        and docs.draft_has_unpublished_changes(db, existing)
    ):
        # 先检查再落盘，避免覆盖知识库目录里的源 md
        return ApiResponse.ok({
            "savedPath": "",
            "treeKey": tree_key,
            "import": {"ok": False, "error": "draft_dirty", "treeKey": tree_key},
            "sync": sync,
        })
    saved_path, err = save_uploaded_md(name, raw)
    if err:
        return ApiResponse.fail(err, code=400)
    # 默认不覆盖有未发布修改的草稿（import.error=draft_dirty），前端确认后带 force=true 重试
    imp = docs.import_md_to_draft(
        db, tree_key, tree_key, md, admin_id=_admin_id(admin), publish=False, force=True,
        keep_unpublished=not force,
    )
    return ApiResponse.ok({"savedPath": saved_path, "treeKey": tree_key, "import": imp, "sync": sync})


_NODE_CRUD_GONE = "节点已由 Markdown 草稿统一管理：请在「知识框架」编辑器中修改并发布（旧接口已停用，避免绕过版本/断开关联）"


@router.post("/knowledge/node")
def admin_knowledge_create_node(_admin=Depends(require_permission("knowledge:write"))):
    return ApiResponse.fail(_NODE_CRUD_GONE, code=410)


@router.put("/knowledge/node/{node_id}")
def admin_knowledge_update_node(node_id: str, _admin=Depends(require_permission("knowledge:write"))):
    return ApiResponse.fail(_NODE_CRUD_GONE, code=410)


@router.delete("/knowledge/node/{node_id}")
def admin_knowledge_delete_node(node_id: str, _admin=Depends(require_permission("knowledge:write"))):
    """旧的物理删除会断开题目/错题/语料关联，已停用；删除节点请改 md 后发布（节点归档，id 保留）。"""
    return ApiResponse.fail(_NODE_CRUD_GONE, code=410)


@router.delete("/knowledge/tree/{tree_key}")
def admin_knowledge_delete_tree_legacy(
    tree_key: str,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    return admin_knowledge_delete_tree_doc(tree_key, _admin=_admin, db=db)


@router.post("/knowledge/upload-image")
async def admin_knowledge_upload_image(
    file: UploadFile = File(...),
    _admin=Depends(require_permission("knowledge:write")),
):
    from uuid import uuid4
    from app.upload_paths import UPLOADS_DIR

    raw = await file.read(3 * 1024 * 1024 + 1)
    if len(raw) > 3 * 1024 * 1024:
        return ApiResponse.fail("图片不能超过 3MB", code=400)
    ext = ".png" if raw.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg" if raw.startswith(b"\xff\xd8\xff") else ""
    if not ext:
        return ApiResponse.fail("请上传 PNG 或 JPEG 图片", code=400)
    folder = UPLOADS_DIR / "knowledge-media"
    folder.mkdir(parents=True, exist_ok=True)
    filename = uuid4().hex + ext
    (folder / filename).write_bytes(raw)
    return ApiResponse.ok({"url": f"/uploads/knowledge-media/{filename}"})
