from app.api.public._deps import *  # noqa: F401,F403
from app.schemas import ZiliaoQuickSessionCreate, ZiliaoQuickAnswerIn, ZiliaoQuickCompleteIn, ZiliaoQuickRetryIn

router = APIRouter()
# ===== 资料分析 =====


@router.get("/ziliao/quick-calc/methods")
def quick_calc_methods(_user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import list_methods
    return ApiResponse.ok(list_methods(db, published_only=True))


@router.post("/ziliao/quick-calc/sessions")
def quick_calc_create_session(body: ZiliaoQuickSessionCreate, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import create_session
    try:
        return ApiResponse.ok(create_session(db, user.id, body.mode, body.count))
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)


@router.get("/ziliao/quick-calc/history")
def quick_calc_history(limit: int = 10, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import user_history
    return ApiResponse.ok(user_history(db, user.id, limit))


@router.post("/ziliao/quick-calc/sessions/{session_id}/retry-wrong")
def quick_calc_retry_wrong(session_id: str, body: ZiliaoQuickRetryIn, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import retry_wrong
    try:
        result = retry_wrong(db, user.id, session_id, body.questionIds)
        return ApiResponse.ok(result) if result else ApiResponse.fail("原练习不存在", code=404)
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)


@router.post("/ziliao/quick-calc/sessions/{session_id}/answers")
def quick_calc_answer(session_id: str, body: ZiliaoQuickAnswerIn, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import answer_question
    try:
        result = answer_question(db, user.id, session_id, body.questionId, body.selected, body.seconds)
        return ApiResponse.ok(result) if result else ApiResponse.fail("练习不存在或已结束", code=404)
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)


@router.post("/ziliao/quick-calc/sessions/{session_id}/complete")
def quick_calc_complete(session_id: str, body: ZiliaoQuickCompleteIn, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import complete_session
    try:
        result = complete_session(db, user.id, session_id, body.totalSeconds)
        return ApiResponse.ok(result) if result else ApiResponse.fail("练习不存在", code=404)
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)


@router.get("/ziliao/overview")
def ziliao_overview(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_ziliao_overview(db, user.id).model_dump())


@router.get("/ziliao/formulas")
def ziliao_formulas(
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([x.model_dump() for x in list_ziliao_formulas(db)])


@router.get("/ziliao/formulas/{formula_id}")
def ziliao_formula_detail(
    formula_id: str,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = get_ziliao_formula(db, formula_id)
    if not out:
        return ApiResponse.fail("公式不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.get("/ziliao/types")
def ziliao_types(
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([x.model_dump() for x in list_ziliao_types(db)])


@router.get("/ziliao/types/{type_id}")
def ziliao_type_detail(
    type_id: str,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = get_ziliao_type(db, type_id)
    if not out:
        return ApiResponse.fail("题型不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.get("/ziliao/tricks")
def ziliao_tricks(
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([x.model_dump() for x in list_ziliao_tricks(db)])


@router.get("/ziliao/tricks/{trick_id}")
def ziliao_trick_detail(
    trick_id: str,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = get_ziliao_trick(db, trick_id)
    if not out:
        return ApiResponse.fail("技巧不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.get("/ziliao/drill/sets")
def ziliao_drill_sets(
    typeCode: str | None = None,
    includeSample: bool | None = None,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(
        [
            x.model_dump()
            for x in list_ziliao_drill_sets(db, type_code=typeCode, include_sample=includeSample)
        ]
    )


@router.get("/ziliao/drill/set/{set_id}")
def ziliao_drill_set_detail(
    set_id: str,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = get_ziliao_drill_set(db, set_id)
    if not out:
        return ApiResponse.fail("练习组不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.post("/ziliao/drill/submit")
def ziliao_drill_submit(
    body: ZiliaoDrillSubmitIn,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = submit_ziliao_drill(db, user, body)
    if not out:
        return ApiResponse.fail("练习组不存在", code=404)
    return ApiResponse.ok(out.model_dump())


