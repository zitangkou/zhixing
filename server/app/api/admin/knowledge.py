from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 知识框架管理 =====


@router.get("/knowledge/trees")
def admin_knowledge_trees(_admin=Depends(require_permission("knowledge:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok([t.model_dump() for t in list_knowledge_trees(db)])


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
def admin_knowledge_sync(
    tree_key: str | None = None,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    result = sync_knowledge(db, only_tree_key=tree_key)
    if "error" in result:
        return ApiResponse.fail(result["error"], code=400)
    return ApiResponse.ok(result)


@router.post("/knowledge/upload-md")
async def admin_knowledge_upload_md(
    file: UploadFile = File(...),
    sync: bool = True,
    _admin=Depends(require_permission("knowledge:write")),
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
    sync_result: dict = {}
    if sync:
        sync_result = sync_knowledge(db, only_tree_key=tree_key)
        if "error" in sync_result:
            return ApiResponse.fail(sync_result["error"], code=400)
    return ApiResponse.ok({"savedPath": saved_path, "treeKey": tree_key, "sync": sync_result})


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
def admin_knowledge_delete_tree(
    tree_key: str,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    """删除整棵知识树（含所有节点，不删本地 md 文件）"""
    from sqlalchemy import text as _text

    from app.models import KnowledgeNode

    rows = db.query(KnowledgeNode).filter(KnowledgeNode.tree_key == tree_key).all()
    if not rows:
        return ApiResponse.fail("知识树不存在", code=404)
    db.execute(_text("UPDATE knowledge_nodes SET parent_id = NULL WHERE tree_key = :tk"), {"tk": tree_key})
    db.execute(_text("DELETE FROM knowledge_nodes WHERE tree_key = :tk"), {"tk": tree_key})
    db.commit()
    return ApiResponse.ok({"ok": True, "deleted": len(rows)})


