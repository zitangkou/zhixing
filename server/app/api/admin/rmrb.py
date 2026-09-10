from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 人民日报模块 =====


@router.get("/rmrb/articles")
def admin_rmrb_articles(
    tag: str | None = None,
    _admin=Depends(require_permission("rmrb:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(
        [a.model_dump() for a in list_rmrb_articles_admin(db, published_only=False, tag=tag, include_html=True)]
    )


@router.post("/rmrb/article")
def admin_rmrb_create_article(
    body: RmrbArticleCreate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        out = create_rmrb_article(db, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


class _RmrbPreviewHtmlBody(BaseModel):
    html: str


@router.post("/rmrb/preview-html")
def admin_rmrb_preview_html(
    body: _RmrbPreviewHtmlBody,
    _admin=Depends(require_permission("rmrb:write")),
):
    from app.services.article_import import parse_rmrb_source_html

    try:
        parsed, parse_errors = parse_rmrb_source_html(body.html)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok({
        "title": parsed["title"],
        "source": parsed.get("source") or "",
        "sourceUrl": parsed.get("source_url") or "",
        "publishDate": parsed.get("publish_date") or "",
        "summary": parsed["summary"],
        "tags": parsed.get("tags") or [],
        "stats": parsed["stats"],
        "parse_warnings": parse_errors,
    })


@router.put("/rmrb/article/{article_id}")
def admin_rmrb_update_article(
    article_id: str,
    body: RmrbArticleUpdate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        out = update_rmrb_article(db, article_id, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    if not out:
        return ApiResponse.fail("文章不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/rmrb/article/{article_id}")
def admin_rmrb_delete_article(
    article_id: str,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    if not delete_rmrb_article(db, article_id):
        return ApiResponse.fail("文章不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.get("/rmrb/meta")
def admin_rmrb_meta(
    _admin=Depends(require_permission("rmrb:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_rmrb_meta(db, enabled_only=False).model_dump())


# ---- 规范词分类 ----

@router.get("/rmrb/term-categories")
def admin_rmrb_term_categories(
    _admin=Depends(require_permission("rmrb:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([c.model_dump() for c in list_rmrb_term_categories(db)])


@router.post("/rmrb/term-categories")
def admin_rmrb_create_term_category(
    body: ShenlunTermCategoryCreate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        out = create_rmrb_term_category(db, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.put("/rmrb/term-categories/{cat_id}")
def admin_rmrb_update_term_category(
    cat_id: str,
    body: ShenlunTermCategoryUpdate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        out = update_rmrb_term_category(db, cat_id, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    if not out:
        return ApiResponse.fail("分类不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/rmrb/term-categories/{cat_id}")
def admin_rmrb_delete_term_category(
    cat_id: str,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    if not delete_rmrb_term_category(db, cat_id):
        return ApiResponse.fail("分类不存在", code=404)
    return ApiResponse.ok({"ok": True})


# ---- 骨架模版 ----

@router.get("/rmrb/skeleton-templates")
def admin_rmrb_skeletons(
    _admin=Depends(require_permission("rmrb:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([t.model_dump() for t in list_rmrb_skeletons(db)])


@router.post("/rmrb/skeleton-templates")
def admin_rmrb_create_skeleton(
    body: ShenlunSkeletonTemplateCreate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        out = create_rmrb_skeleton(db, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.put("/rmrb/skeleton-templates/{tpl_id}")
def admin_rmrb_update_skeleton(
    tpl_id: str,
    body: ShenlunSkeletonTemplateUpdate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        out = update_rmrb_skeleton(db, tpl_id, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    if not out:
        return ApiResponse.fail("模版不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/rmrb/skeleton-templates/{tpl_id}")
def admin_rmrb_delete_skeleton(
    tpl_id: str,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    if not delete_rmrb_skeleton(db, tpl_id):
        return ApiResponse.fail("模版不存在", code=404)
    return ApiResponse.ok({"ok": True})


# ---- 句式类型 ----

@router.get("/rmrb/sentence-types")
def admin_rmrb_sentence_types(
    _admin=Depends(require_permission("rmrb:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([t.model_dump() for t in list_rmrb_sentence_types(db)])


@router.post("/rmrb/sentence-types")
def admin_rmrb_create_sentence_type(
    body: ShenlunSentenceTypeCreate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        out = create_rmrb_sentence_type(db, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.put("/rmrb/sentence-types/{type_id}")
def admin_rmrb_update_sentence_type(
    type_id: str,
    body: ShenlunSentenceTypeUpdate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        out = update_rmrb_sentence_type(db, type_id, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    if not out:
        return ApiResponse.fail("类型不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/rmrb/sentence-types/{type_id}")
def admin_rmrb_delete_sentence_type(
    type_id: str,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    if not delete_rmrb_sentence_type(db, type_id):
        return ApiResponse.fail("类型不存在", code=404)
    return ApiResponse.ok({"ok": True})


# ---- 论证方法 ----

@router.get("/rmrb/argument-methods")
def admin_rmrb_argument_methods(
    _admin=Depends(require_permission("rmrb:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([t.model_dump() for t in list_rmrb_argument_methods(db)])


@router.post("/rmrb/argument-methods")
def admin_rmrb_create_argument_method(
    body: ShenlunArgumentMethodCreate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        out = create_rmrb_argument_method(db, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.put("/rmrb/argument-methods/{method_id}")
def admin_rmrb_update_argument_method(
    method_id: str,
    body: ShenlunArgumentMethodUpdate,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    try:
        out = update_rmrb_argument_method(db, method_id, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    if not out:
        return ApiResponse.fail("方法不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/rmrb/argument-methods/{method_id}")
def admin_rmrb_delete_argument_method(
    method_id: str,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    if not delete_rmrb_argument_method(db, method_id):
        return ApiResponse.fail("方法不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.get("/rmrb/vocab-inbox")
def admin_rmrb_vocab_inbox(
    kind: str | None = Query(None),
    _admin=Depends(require_permission("rmrb:read")),
    db: Session = Depends(get_db),
):
    from app.services.vocab_inbox_service import KINDS, list_inbox

    rmrb_kinds = [k for k in KINDS if k != "theory_category"]
    if kind and kind not in rmrb_kinds:
        return ApiResponse.fail("无效类型", code=400)
    kinds = [kind] if kind else rmrb_kinds
    return ApiResponse.ok(list_inbox(db, kinds=kinds))


@router.post("/rmrb/vocab-inbox/{inbox_id}/promote")
def admin_rmrb_vocab_promote(
    inbox_id: str,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    from app.models import VocabInbox
    from app.services.vocab_inbox_service import promote_inbox

    row = db.get(VocabInbox, inbox_id)
    if not row:
        return ApiResponse.fail("待收录项不存在", code=404)
    if row.kind == "theory_category":
        return ApiResponse.fail("请在分类管理中收录", code=400)
    try:
        return ApiResponse.ok(promote_inbox(db, inbox_id))
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)


@router.post("/rmrb/vocab-inbox/{inbox_id}/ignore")
def admin_rmrb_vocab_ignore(
    inbox_id: str,
    _admin=Depends(require_permission("rmrb:write")),
    db: Session = Depends(get_db),
):
    from app.models import VocabInbox
    from app.services.vocab_inbox_service import ignore_inbox

    row = db.get(VocabInbox, inbox_id)
    if not row:
        return ApiResponse.fail("待收录项不存在", code=404)
    if row.kind == "theory_category":
        return ApiResponse.fail("请在分类管理中处理", code=400)
    out = ignore_inbox(db, inbox_id)
    return ApiResponse.ok(out)


