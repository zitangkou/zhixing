from app.api.public._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 手动错题 =====


@router.get("/manual-wrong")
def manual_wrong_list(
    subject: str | None = None,
    mastered: bool | None = None,
    status: str | None = None,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """status: review（今日到期）| waiting | 不传则不过滤到期"""
    if status and status not in ("review", "waiting", "all"):
        status = None
    if status == "all":
        status = None
    return ApiResponse.ok(
        [w.model_dump() for w in list_wrongs(db, user, subject, mastered, status=status)]
    )


@router.post("/manual-wrong")
def manual_wrong_create(
    body: ManualWrongCreate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = create_wrong(db, user, body)
    return ApiResponse.ok(out.model_dump())


@router.post("/manual-wrong/{wrong_id}/review")
def manual_wrong_review(
    wrong_id: str,
    result: str = "good",
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """result: good（推进间隔）| again（重置）"""
    out = review_manual_wrong(db, user, wrong_id, result)
    if not out:
        return ApiResponse.fail("错题不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.put("/manual-wrong/{wrong_id}")
def manual_wrong_update(
    wrong_id: str,
    body: ManualWrongUpdate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = update_wrong(db, user, wrong_id, body)
    if not out:
        return ApiResponse.fail("错题不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/manual-wrong/{wrong_id}")
def manual_wrong_delete(
    wrong_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if not delete_wrong(db, user, wrong_id):
        return ApiResponse.fail("错题不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.post("/manual-wrong/upload")
async def manual_wrong_upload(
    file: UploadFile = File(...),
    user: AppUser = Depends(get_app_user),
):
    from uuid import uuid4

    from app.upload_paths import detect_image_ext, is_heic_like, uploads_subdir

    raw = await file.read()
    if not raw:
        return ApiResponse.fail("文件为空", code=400)
    if len(raw) > 5 * 1024 * 1024:
        return ApiResponse.fail("图片不能超过 5MB", code=400)

    if is_heic_like(file.content_type or "", file.filename or "", raw):
        return ApiResponse.fail("暂不支持 HEIC/HEIF，请用相册选图并选「最兼容」或先转为 jpg/png", code=400)

    ext = detect_image_ext(file.content_type or "", file.filename or "", raw)
    if not ext:
        return ApiResponse.fail("仅支持 jpg/png/webp/gif 图片", code=400)

    try:
        upload_dir = uploads_subdir("wrong")
        filename = f"{user.id}_{uuid4().hex[:12]}{ext}"
        dest = upload_dir / filename
        dest.write_bytes(raw)
    except OSError as e:
        return ApiResponse.fail(f"保存失败：{e}", code=500)

    return ApiResponse.ok({"url": f"/uploads/wrong/{filename}"})


