from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 学习计划模板 =====


@router.get("/plan/templates")
def admin_plan_templates(
    day_type: str | None = None,
    _admin=Depends(require_permission("plan:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([t.model_dump() for t in list_plan_templates(db, day_type)])


@router.post("/plan/templates/seed")
def admin_plan_seed(
    _admin=Depends(require_permission("plan:write")),
    db: Session = Depends(get_db),
):
    """重新 seed 默认模板（不会清空已有，仅当表空时填充）"""
    seed_default_templates(db)
    return ApiResponse.ok({"ok": True})


@router.post("/plan/templates/replace-defaults")
def admin_plan_replace_defaults(
    reset_week_tasks: bool = Query(True, description="是否清空本自然周用户任务以便按新模板重建"),
    _admin=Depends(require_permission("plan:write")),
    db: Session = Depends(get_db),
):
    """用内置周计划覆盖全部模板，并可选重建本周用户任务"""
    result = replace_default_templates(db, reset_week_tasks=reset_week_tasks)
    return ApiResponse.ok(result)


@router.post("/plan/templates/copy-day")
def admin_plan_copy_day(
    from_day: str = Query(..., description="源日 mon~sun"),
    to_day: str = Query(..., description="目标日 mon~sun"),
    replace: bool = Query(True, description="是否先清空目标日再写入"),
    _admin=Depends(require_permission("plan:write")),
    db: Session = Depends(get_db),
):
    """将某一天的计划模板复制到另一天"""
    try:
        result = copy_plan_day_templates(db, from_day=from_day, to_day=to_day, replace=replace)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(result)


@router.post("/plan/templates/sync-pending")
def admin_plan_sync_pending(
    day_type: str | None = Query(None, description="mon~sun，空=全部"),
    horizon_days: int = Query(14, ge=0, le=60),
    _admin=Depends(require_permission("plan:write")),
    db: Session = Depends(get_db),
):
    """手动把模板同步到今天起未开始的用户日清单"""
    try:
        result = sync_templates_to_pending_tasks(db, day_type, horizon_days=horizon_days)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(result)


@router.post("/plan/template")
def admin_plan_create_template(
    body: PlanTemplateCreate,
    _admin=Depends(require_permission("plan:write")),
    db: Session = Depends(get_db),
):
    valid_keys = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    if body.dayType not in valid_keys:
        return ApiResponse.fail("dayType 必须是 mon/tue/wed/thu/fri/sat/sun", code=400)
    out = create_plan_template(db, body)
    return ApiResponse.ok(out.model_dump())


@router.put("/plan/template/{template_id}")
def admin_plan_update_template(
    template_id: str,
    body: PlanTemplateUpdate,
    _admin=Depends(require_permission("plan:write")),
    db: Session = Depends(get_db),
):
    out = update_plan_template(db, template_id, body)
    if not out:
        return ApiResponse.fail("模板不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/plan/template/{template_id}")
def admin_plan_delete_template(
    template_id: str,
    _admin=Depends(require_permission("plan:write")),
    db: Session = Depends(get_db),
):
    if not delete_plan_template(db, template_id):
        return ApiResponse.fail("模板不存在", code=404)
    return ApiResponse.ok({"ok": True})


