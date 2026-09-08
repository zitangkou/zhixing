from app.api.public._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 知识框架 =====


@router.get("/knowledge/trees")
def knowledge_trees(db: Session = Depends(get_db)):
    return ApiResponse.ok([t.model_dump() for t in list_knowledge_trees(db)])


@router.get("/knowledge/tree/{tree_key}")
def knowledge_tree_detail(tree_key: str, db: Session = Depends(get_db)):
    t = get_knowledge_tree(db, tree_key)
    if not t:
        return ApiResponse.fail("知识树不存在", code=404)
    return ApiResponse.ok(t.model_dump())


@router.post("/knowledge/sync")
def knowledge_sync(
    tree_key: str | None = None,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    result = sync_knowledge(db, only_tree_key=tree_key)
    if "error" in result:
        return ApiResponse.fail(result["error"], code=400)
    return ApiResponse.ok(result)


@router.get("/knowledge/status")
def knowledge_status(db: Session = Depends(get_db)):
    return ApiResponse.ok(knowledge_sync_status(db))


@router.put("/knowledge/node/{node_id}")
def knowledge_node_update(
    node_id: str,
    body: KnowledgeNodeUpdate,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """App 端只能改 my_note / is_starred / content（不能改 title 等结构）"""
    # 限制只能改 my_note / is_starred / content
    data = body.model_dump(exclude_unset=True)
    safe = {}
    if "myNote" in data:
        safe["myNote"] = data["myNote"]
    if "isStarred" in data:
        safe["isStarred"] = data["isStarred"]
    if "content" in data:
        safe["content"] = data["content"]
    if not safe:
        return ApiResponse.fail("没有可更新的字段", code=400)
    out = update_knowledge_node(db, node_id, KnowledgeNodeUpdate(**safe))
    if not out:
        return ApiResponse.fail("节点不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.get("/knowledge/review/due")
def knowledge_review_due(
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_knowledge_review_due(db).model_dump())


@router.post("/knowledge/review/session")
def knowledge_review_session(
    body: KnowledgeReviewSessionBody,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(create_knowledge_review_session(db, body.count).model_dump())


@router.post("/knowledge/review/answer")
def knowledge_review_answer(
    body: KnowledgeReviewAnswerBody,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = answer_knowledge_review(db, body.nodeId, body.result)
    if not out:
        return ApiResponse.fail("节点不存在或结果无效", code=400)
    return ApiResponse.ok(out.model_dump())


