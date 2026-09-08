from app.api.public._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 时事新闻 · 事件印象 =====


@router.get("/events/hub")
def events_hub(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_event_hub(db, user).model_dump())


@router.get("/events")
def events_list(
    treeKey: str | None = Query(None),
    path: str | None = Query(None),
    unlinked: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(
        [
            e.model_dump()
            for e in list_event_impressions(
                db, user, tree_key=treeKey, path=path, unlinked=unlinked, limit=limit
            )
        ]
    )


@router.get("/events/{event_id}")
def events_detail(
    event_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = get_event_impression(db, user, event_id)
    if not out:
        return ApiResponse.fail("记录不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.post("/events")
def events_create(
    body: EventImpressionCreate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        out = create_event_impression(db, user, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.put("/events/{event_id}")
def events_update(
    event_id: str,
    body: EventImpressionUpdate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        out = update_event_impression(db, user, event_id, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    if not out:
        return ApiResponse.fail("记录不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/events/{event_id}")
def events_delete(
    event_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if not delete_event_impression(db, user, event_id):
        return ApiResponse.fail("记录不存在", code=404)
    return ApiResponse.ok({"ok": True})


