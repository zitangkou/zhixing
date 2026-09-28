from app.api.public._deps import *  # noqa: F401,F403
from app.models import KnowledgeNode
from app.schemas import KnowledgeUserStateUpdate
from app.services import knowledge_doc_service as docs

router = APIRouter()
# ===== 知识框架 =====


@router.get("/knowledge/maps")
def knowledge_maps(db: Session = Depends(get_db)):
    return ApiResponse.ok(docs.list_public_maps(db))


@router.get("/knowledge/maps/{tree_key}")
def knowledge_map_detail(tree_key: str, db: Session = Depends(get_db)):
    detail = docs.get_public_map(db, tree_key)
    if not detail:
        return ApiResponse.fail("知识导图不存在或未发布", code=404)
    return ApiResponse.ok(detail)


@router.get("/knowledge/trees")
def knowledge_trees(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    return ApiResponse.ok([t.model_dump() for t in list_knowledge_trees(db, user_id=user.id, visible_only=True)])


@router.get("/knowledge/tree/{tree_key}")
def knowledge_tree_detail(
    tree_key: str, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)
):
    t = get_knowledge_tree(db, tree_key, user_id=user.id, visible_only=True)
    if not t:
        return ApiResponse.fail("知识树不存在", code=404)
    return ApiResponse.ok(t.model_dump())


@router.put("/knowledge/node/{node_id}")
def knowledge_node_update(
    node_id: str,
    body: KnowledgeUserStateUpdate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """学员只能改本人备注/星标，不能改全局 content。"""
    data = body.model_dump(exclude_unset=True)
    if not data:
        return ApiResponse.fail("没有可更新的字段", code=400)
    st = docs.upsert_user_state(
        db,
        user.id,
        node_id,
        my_note=data.get("myNote"),
        is_starred=data.get("isStarred"),
    )
    if not st:
        return ApiResponse.fail("节点不存在", code=404)
    node = db.get(KnowledgeNode, node_id)
    return ApiResponse.ok(
        {
            "id": node_id,
            "treeKey": node.tree_key if node else "",
            "title": node.title if node else "",
            "content": node.content if node else "",
            "myNote": st.my_note,
            "isStarred": st.is_starred,
            "masteryLevel": st.mastery_level,
            "path": node.path if node else st.path,
            "depth": node.depth if node else 0,
            "sortOrder": node.sort_order if node else 0,
            "parentId": node.parent_id if node else None,
            "sourceFile": "",
            "children": None,
        }
    )


@router.get("/knowledge/review/due")
def knowledge_review_due(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_knowledge_review_due(db, user.id).model_dump())


@router.post("/knowledge/review/session")
def knowledge_review_session(
    body: KnowledgeReviewSessionBody,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(create_knowledge_review_session(db, user.id, body.count).model_dump())


@router.post("/knowledge/review/answer")
def knowledge_review_answer(
    body: KnowledgeReviewAnswerBody,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = answer_knowledge_review(db, user.id, body.nodeId, body.result)
    if not out:
        return ApiResponse.fail("节点不存在或结果无效", code=400)
    return ApiResponse.ok(out.model_dump())
