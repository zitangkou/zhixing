from app.api.public._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 每日学习清单 =====


@router.get("/plan/today")
def plan_today(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    from app.services.plan_service import _today_str

    return ApiResponse.ok(get_day_plan(db, user, _today_str()).model_dump())


@router.get("/plan/day/{date_str}")
def plan_day(date_str: str, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    return ApiResponse.ok(get_day_plan(db, user, date_str).model_dump())


@router.get("/plan/week")
def plan_week(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    return ApiResponse.ok([d.model_dump() for d in list_recent_days(db, user, 7)])


@router.put("/plan/task/{task_id}")
def plan_task_update(
    task_id: str,
    body: PlanTaskUpdate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = update_task(db, user, task_id, body)
    if not out:
        return ApiResponse.fail("任务不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.post("/plan/task")
def plan_task_add(
    body: PlanTaskCreate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = add_task(db, user, body)
    return ApiResponse.ok(out.model_dump())


@router.delete("/plan/task/{task_id}")
def plan_task_delete(
    task_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if not delete_task(db, user, task_id):
        return ApiResponse.fail("任务不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.post("/plan/review")
def plan_review_upsert(
    body: DailyReviewUpsert,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = upsert_review(db, user, body)
    return ApiResponse.ok(out.model_dump())


