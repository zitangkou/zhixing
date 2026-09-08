from app.api.public._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 资料分析 =====


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


