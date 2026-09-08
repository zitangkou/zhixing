from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ---- 三刀解剖导入 ----

class ThreeKnifeImportBody(BaseModel):
    markdown: str
    userId: str | None = None  # 指定用户；为空则用管理员关联的默认用户


@router.post("/rmrb/import-three-knife")
def admin_rmrb_import_three_knife(
    body: ThreeKnifeImportBody,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    """解析三刀解剖 Markdown 并存入开采本（ShenlunMineLog）。"""
    from app.services.shenlun_import_service import parse_three_knife_markdown
    from app.services.shenlun_service import upsert_mine

    md = (body.markdown or "").strip()
    if not md:
        return ApiResponse.fail("Markdown 内容不能为空", code=400)

    # 确定目标用户
    if body.userId:
        user = db.get(AppUser, body.userId)
        if not user:
            return ApiResponse.fail("指定用户不存在", code=404)
    else:
        # 取第一个管理员关联用户或系统第一个用户
        user = db.query(AppUser).first()
        if not user:
            return ApiResponse.fail("系统中暂无用户", code=400)

    try:
        parsed = parse_three_knife_markdown(md)
    except Exception as e:
        return ApiResponse.fail(f"Markdown 解析失败：{e}", code=400)

    if not parsed.articleTitle:
        return ApiResponse.fail("未能从 Markdown 中解析出文章标题", code=400)

    out = upsert_mine(db, user, parsed)
    return ApiResponse.ok({
        "mine": out.model_dump(),
        "summary": {
            "articleTitle": parsed.articleTitle,
            "mineDate": parsed.mineDate,
            "termsCount": len(parsed.terms),
            "quotesCount": len(parsed.quotes),
            "verbsCount": len(parsed.verbs),
            "pointsCount": len(parsed.argument.points) if parsed.argument else 0,
            "templatesCount": len(parsed.templates),
        },
    })


@router.post("/rmrb/preview-three-knife")
def admin_rmrb_preview_three_knife(
    body: ThreeKnifeImportBody,
    _admin=Depends(require_permission("rmrb:read")),
):
    """仅解析不保存，返回结构化预览。"""
    from app.services.shenlun_import_service import parse_three_knife_markdown

    md = (body.markdown or "").strip()
    if not md:
        return ApiResponse.fail("Markdown 内容不能为空", code=400)

    try:
        parsed = parse_three_knife_markdown(md)
    except Exception as e:
        return ApiResponse.fail(f"Markdown 解析失败：{e}", code=400)

    return ApiResponse.ok({
        "parsed": parsed.model_dump(),
        "summary": {
            "articleTitle": parsed.articleTitle,
            "mineDate": parsed.mineDate,
            "termsCount": len(parsed.terms),
            "quotesCount": len(parsed.quotes),
            "verbsCount": len(parsed.verbs),
            "pointsCount": len(parsed.argument.points) if parsed.argument else 0,
            "templatesCount": len(parsed.templates),
        },
    })


# ============================================================
# 语料本管理（corpus）
# ============================================================

@router.get("/corpus/items")
def admin_corpus_items(
    user_id: str | None = None,
    status: str | None = None,
    kind: str | None = None,
    q: str | None = None,
    _admin=Depends(require_permission("corpus:read")),
    db: Session = Depends(get_db),
):
    """跨用户查看语料本条目。"""
    query = db.query(CorpusItem)
    if user_id:
        query = query.filter(CorpusItem.user_id == user_id)
    if status:
        query = query.filter(CorpusItem.status == status)
    if kind:
        query = query.filter(CorpusItem.kind == kind)
    if q:
        query = query.filter(CorpusItem.original.contains(q))
    items = query.order_by(CorpusItem.created_at.desc()).limit(200).all()
    from app.services.corpus_service import _item_out
    return ApiResponse.ok([_item_out(i).model_dump() for i in items])


@router.get("/corpus/stats")
def admin_corpus_stats(
    user_id: str | None = None,
    _admin=Depends(require_permission("corpus:read")),
    db: Session = Depends(get_db),
):
    """语料本统计（可按用户筛选）。"""
    from sqlalchemy import func
    base = db.query(CorpusItem.status, func.count(CorpusItem.id))
    if user_id:
        base = base.filter(CorpusItem.user_id == user_id)
    rows = base.group_by(CorpusItem.status).all()
    stats = {s: c for s, c in rows}
    return ApiResponse.ok({
        "total": sum(stats.values()),
        "inbox": stats.get("inbox", 0),
        "clarified": stats.get("clarified", 0),
        "owned": stats.get("owned", 0),
        "used": stats.get("used", 0),
    })


@router.put("/corpus/item/{item_id}")
def admin_corpus_update_item(
    item_id: str,
    body: dict,
    _admin=Depends(require_permission("corpus:write")),
    db: Session = Depends(get_db),
):
    """管理员编辑语料条目（状态/标签/备注等）。"""
    item = db.get(CorpusItem, item_id)
    if not item:
        return ApiResponse.fail("条目不存在", code=404)
    allowed = {"status", "plain_note", "rewrite", "practice", "tags_json", "kind", "source_type", "source_title"}
    for k, v in body.items():
        if k in allowed:
            setattr(item, k, v)
    db.commit()
    db.refresh(item)
    from app.services.corpus_service import _item_out
    return ApiResponse.ok(_item_out(item).model_dump())


@router.delete("/corpus/item/{item_id}")
def admin_corpus_delete_item(
    item_id: str,
    _admin=Depends(require_permission("corpus:write")),
    db: Session = Depends(get_db),
):
    item = db.get(CorpusItem, item_id)
    if not item:
        return ApiResponse.fail("条目不存在", code=404)
    db.delete(item)
    db.commit()
    return ApiResponse.ok({"ok": True})


# ============================================================
# 时事事件管理（events）
# ============================================================

@router.get("/events/list")
def admin_events_list(
    user_id: str | None = None,
    tree_key: str | None = None,
    q: str | None = None,
    _admin=Depends(require_permission("events:read")),
    db: Session = Depends(get_db),
):
    """跨用户查看时事事件。"""
    query = db.query(EventImpression)
    if user_id:
        query = query.filter(EventImpression.user_id == user_id)
    if tree_key:
        query = query.filter(EventImpression.knowledge_tree_key == tree_key)
    if q:
        query = query.filter(EventImpression.title.contains(q))
    items = query.order_by(EventImpression.event_date.desc()).limit(200).all()
    from app.services.event_impression_service import _to_out
    return ApiResponse.ok([_to_out(i).model_dump() for i in items])


@router.get("/events/hub")
def admin_events_hub(
    user_id: str,
    _admin=Depends(require_permission("events:read")),
    db: Session = Depends(get_db),
):
    """指定用户的事件中心概览。"""
    user = db.get(AppUser, user_id)
    if not user:
        return ApiResponse.fail("用户不存在", code=404)
    from app.services.event_impression_service import get_hub
    return ApiResponse.ok(get_hub(db, user).model_dump())


@router.put("/events/{event_id}")
def admin_events_update(
    event_id: str,
    body: dict,
    _admin=Depends(require_permission("events:write")),
    db: Session = Depends(get_db),
):
    ev = db.get(EventImpression, event_id)
    if not ev:
        return ApiResponse.fail("事件不存在", code=404)
    allowed = {"title", "event_date", "place", "core_content", "note",
               "knowledge_node_id", "knowledge_tree_key", "knowledge_path"}
    for k, v in body.items():
        if k in allowed:
            setattr(ev, k, v)
    db.commit()
    db.refresh(ev)
    from app.services.event_impression_service import _to_out
    return ApiResponse.ok(_to_out(ev).model_dump())


@router.delete("/events/{event_id}")
def admin_events_delete(
    event_id: str,
    _admin=Depends(require_permission("events:write")),
    db: Session = Depends(get_db),
):
    ev = db.get(EventImpression, event_id)
    if not ev:
        return ApiResponse.fail("事件不存在", code=404)
    db.delete(ev)
    db.commit()
    return ApiResponse.ok({"ok": True})

