from app.api.public._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 考试倒计时 =====

@router.get("/countdown")
def countdown_get(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = get_countdown(db, user)
    return ApiResponse.ok(out.model_dump() if out else None)


@router.put("/countdown")
def countdown_upsert(
    body: ExamCountdownUpsert,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        out = upsert_countdown(db, user, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.delete("/countdown")
def countdown_delete(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    deleted = delete_countdown(db, user)
    if not deleted:
        return ApiResponse.fail("尚未设置考试倒计时", code=404)
    return ApiResponse.ok({"deleted": True})
