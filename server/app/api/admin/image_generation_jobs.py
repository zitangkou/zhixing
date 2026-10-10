"""Admin visibility into image generation task status and failures."""

import re
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import AppUser, ImageGenerationJob
from app.product import resolve_product
from app.services.image_generation_jobs import run_image_generation_job
from app.services.image_generation_service import MAX_INPUT_BYTES, RESULTS_DIR
from app.services.image_style_service import get_image_style_config
from app.upload_paths import DATA_DIR, detect_image_ext

router = APIRouter()


@router.post("/image-generation-jobs/test")
async def admin_start_image_generation_test(
    background_tasks: BackgroundTasks,
    style_id: str = Form(..., min_length=1, max_length=64),
    file: UploadFile = File(...),
    _admin=Depends(require_permission("setting:write")),
    db: Session = Depends(get_db),
):
    raw = await file.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise HTTPException(413, "测试图片不能超过 8 MB")
    ext = detect_image_ext(file.content_type or "", file.filename or "", raw)
    if ext not in {".jpg", ".png", ".webp"}:
        raise HTTPException(400, "仅支持 JPG、PNG、WEBP 图片")

    style = next((item for item in get_image_style_config(db)["items"] if item["id"] == style_id), None)
    if not style or style.get("status") not in {"active", "draft"}:
        raise HTTPException(400, "只能测试已保存的草稿或已启用风格；已归档风格不可测试")
    product_key = style.get("productKey") if style.get("productKey") != "*" else "general"
    product = resolve_product(product_key or "general")

    task_id = uuid.uuid4().hex
    input_dir = DATA_DIR / "private" / "image-generation-inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / f"{task_id}{ext}"
    input_path.write_bytes(raw)
    input_path.chmod(0o600)
    db.add(ImageGenerationJob(
        id=task_id,
        user_id="admin-test",
        product_key=product.key,
        style_id=style_id,
        status="queued",
        allow_draft=True,
        input_path=str(input_path),
    ))
    db.commit()
    background_tasks.add_task(run_image_generation_job, task_id)
    return ApiResponse.ok({"taskId": task_id, "status": "queued"}, message="测试任务已提交")


@router.get("/image-generation-jobs/{job_id}")
def admin_get_image_generation_job(
    job_id: str,
    _admin=Depends(require_permission("setting:read")),
    db: Session = Depends(get_db),
):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise HTTPException(404, "图片生成任务不存在")
    job = db.get(ImageGenerationJob, job_id)
    if not job:
        raise HTTPException(404, "图片生成任务不存在")
    return ApiResponse.ok({
        "id": job.id,
        "status": job.status,
        "styleId": job.style_id,
        "modelId": job.model_id or None,
        "provider": job.provider or None,
        "resultId": job.result_id or None,
        "errorCode": job.error_code or None,
        "errorMessage": job.error_message or None,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "startedAt": job.started_at.isoformat() if job.started_at else None,
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
    })


@router.get("/image-generation-jobs/{job_id}/result")
def admin_get_image_generation_job_result(
    job_id: str,
    _admin=Depends(require_permission("setting:read")),
    db: Session = Depends(get_db),
):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise HTTPException(404, "图片结果不存在或已过期")
    job = db.get(ImageGenerationJob, job_id)
    if not job or job.status != "succeeded" or not job.result_id:
        raise HTTPException(404, "图片结果不存在或尚未生成")
    owner_dir = RESULTS_DIR / re.sub(r"[^A-Za-z0-9_-]", "_", job.user_id)[:80]
    candidates = [path for path in owner_dir.glob(f"{job.result_id}.*") if path.suffix.lower() in {".png", ".jpg", ".webp"}]
    if not candidates:
        raise HTTPException(404, "图片结果不存在或已过期")
    path = candidates[0]
    if path.stat().st_mtime < time.time() - 24 * 60 * 60:
        path.unlink(missing_ok=True)
        raise HTTPException(404, "图片结果已过期，请重新生成")
    media_type = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}[path.suffix.lower()]
    return FileResponse(path, media_type=media_type, filename=f"{job.result_id}{path.suffix}")


@router.get("/image-generation-jobs")
def admin_list_image_generation_jobs(
    status: str | None = Query(default=None, pattern="^(queued|running|succeeded|failed)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    _admin=Depends(require_permission("setting:read")),
    db: Session = Depends(get_db),
):
    query = db.query(ImageGenerationJob)
    if status:
        query = query.filter(ImageGenerationJob.status == status)
    total = query.count()
    rows = query.order_by(ImageGenerationJob.created_at.desc()).offset((page - 1) * size).limit(size).all()
    user_ids = {row.user_id for row in rows}
    users = {user.id: user for user in db.query(AppUser).filter(AppUser.id.in_(user_ids)).all()} if user_ids else {}
    items = []
    for row in rows:
        user = users.get(row.user_id)
        items.append({
            "id": row.id,
            "userId": row.user_id,
            "userName": "后台测试" if row.user_id == "admin-test" else (user.nickname if user else "已删除用户"),
            "productKey": row.product_key,
            "styleId": row.style_id,
            "modelId": row.model_id or None,
            "provider": row.provider or None,
            "status": row.status,
            "resultId": row.result_id or None,
            "errorCode": row.error_code or None,
            "errorMessage": row.error_message or None,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "startedAt": row.started_at.isoformat() if row.started_at else None,
            "completedAt": row.completed_at.isoformat() if row.completed_at else None,
        })
    return ApiResponse.ok({"items": items, "total": total, "page": page, "size": size})
