from app.api.public._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 语料本 =====


@router.get("/corpus/stats")
def corpus_stats(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_corpus_stats(db, user).model_dump())


@router.get("/corpus/items")
def corpus_items_list(
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=200),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([i.model_dump() for i in list_corpus_items(db, user, status, limit)])


@router.get("/corpus/items/{item_id}")
def corpus_item_detail(
    item_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = get_corpus_item(db, user, item_id)
    if not out:
        return ApiResponse.fail("记录不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.post("/corpus/items")
def corpus_item_create(
    body: CorpusItemCreate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        out = create_corpus_item(db, user, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.put("/corpus/items/{item_id}")
def corpus_item_update(
    item_id: str,
    body: CorpusItemUpdate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        out = update_corpus_item(db, user, item_id, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    if not out:
        return ApiResponse.fail("记录不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/corpus/items/{item_id}")
def corpus_item_delete(
    item_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if not delete_corpus_item(db, user, item_id):
        return ApiResponse.fail("记录不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.post("/corpus/items/{item_id}/promote-term")
def corpus_item_promote_term(
    item_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        out = promote_corpus_to_term(db, user, item_id)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    if not out:
        return ApiResponse.fail("记录不存在", code=404)
    return ApiResponse.ok(out.model_dump())


