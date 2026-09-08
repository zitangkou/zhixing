from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 资料分析管理 =====


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


