from app.api.public._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 人民日报模块（独立：时评 / 开采本 / 规范词） =====


@router.get("/rmrb/meta")
def rmrb_meta(
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """三刀解剖元数据：规范词分类 / 骨架模版 / 句式类型"""
    return ApiResponse.ok(get_rmrb_meta(db, enabled_only=True).model_dump())


@router.post("/rmrb/skeleton-templates")
def rmrb_skeleton_create(
    body: ShenlunSkeletonTemplateCreate,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """用户在三刀页快捷新增骨架模版"""
    try:
        out = create_rmrb_skeleton(db, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.post("/rmrb/term-categories")
def rmrb_term_category_create(
    body: ShenlunTermCategoryCreate,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """移动端快捷新增规范词/动词分类（kind: term | verb）"""
    try:
        out = create_rmrb_term_category(db, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.get("/rmrb/stats")
def rmrb_stats(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_shenlun_stats(db, user).model_dump())


@router.get("/rmrb/articles")
def rmrb_articles_list(
    tag: str | None = None,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(
        [a.model_dump() for a in list_rmrb_articles(db, published_only=True, tag=tag)]
    )


@router.get("/rmrb/articles/{article_id}")
def rmrb_article_detail(
    article_id: str,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    a = get_rmrb_article(db, article_id, bump_read=True)
    if not a or not a.isPublished:
        return ApiResponse.fail("文章不存在", code=404)
    return ApiResponse.ok(a.model_dump())


@router.get("/rmrb/mines")
def rmrb_mines_list(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([m.model_dump() for m in list_shenlun_mines(db, user)])


@router.get("/rmrb/mines/by-date/{mine_date}")
def rmrb_mine_by_date(
    mine_date: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    m = get_shenlun_mine_by_date(db, user, mine_date)
    if not m:
        return ApiResponse.fail("当日尚无开采记录", code=404)
    return ApiResponse.ok(m.model_dump())


@router.get("/rmrb/mines/{mine_id}")
def rmrb_mine_detail(
    mine_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    m = get_shenlun_mine(db, user, mine_id)
    if not m:
        return ApiResponse.fail("开采记录不存在", code=404)
    return ApiResponse.ok(m.model_dump())


@router.post("/rmrb/mines")
def rmrb_mine_upsert(
    body: ShenlunMineLogUpsert,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = upsert_shenlun_mine(db, user, body)
    return ApiResponse.ok(out.model_dump())


@router.put("/rmrb/mines/{mine_id}")
def rmrb_mine_update(
    mine_id: str,
    body: ShenlunMineLogUpdate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = update_shenlun_mine(db, user, mine_id, body)
    if not out:
        return ApiResponse.fail("开采记录不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/rmrb/mines/{mine_id}")
def rmrb_mine_delete(
    mine_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if not delete_shenlun_mine(db, user, mine_id):
        return ApiResponse.fail("开采记录不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.get("/rmrb/terms")
def rmrb_terms_list(
    status: str | None = None,
    category: str | None = None,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(
        [t.model_dump() for t in list_shenlun_terms(db, user, status=status, category=category)]
    )


@router.post("/rmrb/terms")
def rmrb_term_add(
    body: ShenlunNormTermAdd,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        out = add_shenlun_term(db, user, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.put("/rmrb/terms/{term_id}")
def rmrb_term_update(
    term_id: str,
    body: ShenlunNormTermUpdate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = update_shenlun_term(db, user, term_id, body)
    if not out:
        return ApiResponse.fail("规范词不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/rmrb/terms/{term_id}")
def rmrb_term_delete(
    term_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if not delete_shenlun_term(db, user, term_id):
        return ApiResponse.fail("规范词不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.get("/rmrb/drills")
def rmrb_drills_list(
    drill_type: str | None = None,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([d.model_dump() for d in list_shenlun_drills(db, user, drill_type)])


@router.post("/rmrb/drills")
def rmrb_drill_add(
    body: ShenlunDrillCreate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        out = add_shenlun_drill(db, user, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.get("/growth/overview")
def growth_overview(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """知行足迹：个人成长总览"""
    return ApiResponse.ok(get_growth_overview(db, user).model_dump())


