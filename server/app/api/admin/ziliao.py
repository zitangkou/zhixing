from app.api.admin._deps import *  # noqa: F401,F403
from app.schemas import ZiliaoQuickMethodUpsert

router = APIRouter()
# ===== 资料分析管理 =====


@router.get("/ziliao/quick-calc/methods")
def admin_quick_methods(_admin=Depends(require_permission("ziliao:read")), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import list_methods
    return ApiResponse.ok(list_methods(db))


@router.post("/ziliao/quick-calc/methods")
def admin_quick_method_create(body: ZiliaoQuickMethodUpsert, _admin=Depends(require_permission("ziliao:write")), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import upsert_method
    try:
        return ApiResponse.ok(upsert_method(db, body))
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)


@router.put("/ziliao/quick-calc/methods/{method_id}")
def admin_quick_method_update(method_id: str, body: ZiliaoQuickMethodUpsert, _admin=Depends(require_permission("ziliao:write")), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import upsert_method
    try:
        result = upsert_method(db, body, method_id)
        return ApiResponse.ok(result) if result else ApiResponse.fail("训练方法不存在", code=404)
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)


@router.post("/ziliao/quick-calc/methods/{method_id}/preview")
def admin_quick_method_preview(method_id: str, _admin=Depends(require_permission("ziliao:read")), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import preview
    methods = {x["id"]: x["code"] for x in list_ziliao_quick_methods(db)}
    code = methods.get(method_id)
    if not code:
        return ApiResponse.fail("训练方法不存在", code=404)
    try:
        return ApiResponse.ok(preview(db, code))
    except (ValueError, AssertionError) as exc:
        return ApiResponse.fail(f"规则校验失败：{exc}", code=400)


@router.post("/ziliao/quick-calc/methods/{method_id}/publish")
def admin_quick_method_publish(method_id: str, _admin=Depends(require_permission("ziliao:write")), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import publish_method
    try:
        result = publish_method(db, method_id)
        return ApiResponse.ok(result) if result else ApiResponse.fail("训练方法不存在", code=404)
    except (ValueError, AssertionError) as exc:
        return ApiResponse.fail(f"发布校验失败：{exc}", code=400)


@router.get("/ziliao/quick-calc/methods/{method_id}/versions")
def admin_quick_method_versions(method_id: str, _admin=Depends(require_permission("ziliao:read")), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import list_method_versions
    result = list_method_versions(db, method_id)
    return ApiResponse.ok(result) if result is not None else ApiResponse.fail("训练方法不存在", code=404)


@router.post("/ziliao/quick-calc/methods/{method_id}/rollback/{version_number}")
def admin_quick_method_rollback(method_id: str, version_number: int, _admin=Depends(require_permission("ziliao:write")), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import rollback_method
    try:
        result = rollback_method(db, method_id, version_number)
        return ApiResponse.ok(result) if result else ApiResponse.fail("训练方法或版本不存在", code=404)
    except (ValueError, AssertionError) as exc:
        return ApiResponse.fail(f"回滚发布失败：{exc}", code=400)


@router.get("/ziliao/quick-calc/analytics")
def admin_quick_analytics(days: int = Query(30, ge=1, le=365), _admin=Depends(require_permission("ziliao:read")), db: Session = Depends(get_db)):
    from app.services.ziliao_quick_calc_service import analytics
    return ApiResponse.ok(analytics(db, days))


def list_ziliao_quick_methods(db: Session):
    from app.services.ziliao_quick_calc_service import list_methods
    return list_methods(db)


@router.get("/ziliao/formulas")
def admin_ziliao_formulas(
    _admin=Depends(require_permission("ziliao:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([x.model_dump() for x in list_ziliao_formulas_admin(db, published_only=False)])


@router.post("/ziliao/formulas")
def admin_ziliao_create_formula(
    body: ZiliaoFormulaCreate,
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(create_ziliao_formula(db, body).model_dump())


@router.post("/ziliao/formulas/import-json")
def admin_ziliao_import_formulas_json(
    body: ZiliaoFormulaImportBody,
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    result = import_ziliao_formulas_from_json(
        db,
        body.content,
        overwrite=body.overwrite,
        publish_default=body.publishDefault,
    )
    return ApiResponse.ok(result.model_dump())


@router.post("/ziliao/formulas/upload-json")
async def admin_ziliao_upload_formulas_json(
    file: UploadFile = File(...),
    overwrite: bool = Query(True),
    publish_default: bool = Query(True),
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".json"):
        return ApiResponse.fail("仅支持 .json 文件")
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        return ApiResponse.fail("文件不能超过 2MB")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ApiResponse.fail("文件必须使用 UTF-8 编码")
    result = import_ziliao_formulas_from_json(
        db,
        content,
        overwrite=overwrite,
        publish_default=publish_default,
    )
    return ApiResponse.ok(result.model_dump())


@router.put("/ziliao/formulas/{formula_id}")
def admin_ziliao_update_formula(
    formula_id: str,
    body: ZiliaoFormulaUpdate,
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    out = update_ziliao_formula(db, formula_id, body)
    if not out:
        return ApiResponse.fail("公式不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/ziliao/formulas/{formula_id}")
def admin_ziliao_delete_formula(
    formula_id: str,
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    if not delete_ziliao_formula(db, formula_id):
        return ApiResponse.fail("公式不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.get("/ziliao/types")
def admin_ziliao_types(
    _admin=Depends(require_permission("ziliao:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([x.model_dump() for x in list_ziliao_types_admin(db, published_only=False)])


@router.post("/ziliao/types")
def admin_ziliao_create_type(
    body: ZiliaoQuestionTypeCreate,
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(create_ziliao_type(db, body).model_dump())


@router.put("/ziliao/types/{type_id}")
def admin_ziliao_update_type(
    type_id: str,
    body: ZiliaoQuestionTypeUpdate,
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    out = update_ziliao_type(db, type_id, body)
    if not out:
        return ApiResponse.fail("题型不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/ziliao/types/{type_id}")
def admin_ziliao_delete_type(
    type_id: str,
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    if not delete_ziliao_type(db, type_id):
        return ApiResponse.fail("题型不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.get("/ziliao/tricks")
def admin_ziliao_tricks(
    _admin=Depends(require_permission("ziliao:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([x.model_dump() for x in list_ziliao_tricks_admin(db, published_only=False)])


@router.post("/ziliao/tricks")
def admin_ziliao_create_trick(
    body: ZiliaoTrickCreate,
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(create_ziliao_trick(db, body).model_dump())


@router.put("/ziliao/tricks/{trick_id}")
def admin_ziliao_update_trick(
    trick_id: str,
    body: ZiliaoTrickUpdate,
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    out = update_ziliao_trick(db, trick_id, body)
    if not out:
        return ApiResponse.fail("技巧不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/ziliao/tricks/{trick_id}")
def admin_ziliao_delete_trick(
    trick_id: str,
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    if not delete_ziliao_trick(db, trick_id):
        return ApiResponse.fail("技巧不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.post("/ziliao/seed")
def admin_ziliao_seed(
    force: bool = Query(False),
    _admin=Depends(require_permission("ziliao:write")),
    db: Session = Depends(get_db),
):
    counts = seed_ziliao_resources(db, force=force)
    seeded_paper = seed_sample_drill_paper(db)
    return ApiResponse.ok({**counts, "samplePaper": seeded_paper})


@router.get("/ziliao/import-guide")
def admin_ziliao_import_guide(
    _admin=Depends(require_permission("ziliao:read")),
):
    path = Path(__file__).resolve().parents[3] / "data" / "ziliao" / "IMPORT.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "导入规范文件缺失：server/data/ziliao/IMPORT.md"
    return ApiResponse.ok({"markdown": text, "examplePath": "server/data/ziliao/examples/guokao-style-sample.md"})


