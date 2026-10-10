"""Authenticated image style generation endpoints."""

import re
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_app_user
from app.core.response import ApiResponse
from app.database import get_db
from app.models import AppUser, ImageGenerationJob
from app.product import ProductContext, get_product_context
from app.services.image_generation_service import MAX_INPUT_BYTES, RESULTS_DIR
from app.services.image_generation_jobs import run_image_generation_job
from app.upload_paths import DATA_DIR, detect_image_ext

router = APIRouter()


@router.post("/image-generations")
async def create_image_generation(
    background_tasks: BackgroundTasks,
    style_id: str = Form(..., min_length=1, max_length=64),
    file: UploadFile = File(...),
    user: AppUser = Depends(get_app_user),
    product: ProductContext = Depends(get_product_context),
    db: Session = Depends(get_db),
):
    raw = await file.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise HTTPException(413, "图片不能超过 8 MB")
    ext = detect_image_ext(file.content_type or "", file.filename or "", raw)
    if ext not in {".jpg", ".png", ".webp"}:
        raise HTTPException(400, "仅支持 JPG、PNG、WEBP 图片")
    mime = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}[ext]
    task_id = uuid.uuid4().hex
    input_dir = DATA_DIR / "private" / "image-generation-inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / f"{task_id}{ext}"
    input_path.write_bytes(raw)
    input_path.chmod(0o600)
    job = ImageGenerationJob(
        id=task_id,
        user_id=user.id,
        product_key=product.key,
        style_id=style_id,
        status="queued",
        input_path=str(input_path),
    )
    db.add(job)
    db.commit()
    background_tasks.add_task(run_image_generation_job, task_id)
    return ApiResponse.ok({"taskId": task_id, "status": "queued"}, message="已提交图片生成任务")


@router.get("/image-generations/{task_id}")
def get_image_generation_status(task_id: str, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    if not re.fullmatch(r"[a-f0-9]{32}", task_id):
        raise HTTPException(404, "图片生成任务不存在")
    job = db.get(ImageGenerationJob, task_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "图片生成任务不存在")
    return ApiResponse.ok({
        "taskId": job.id,
        "status": job.status,
        "resultId": job.result_id or None,
        "errorCode": job.error_code or None,
        "errorMessage": job.error_message or None,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "startedAt": job.started_at.isoformat() if job.started_at else None,
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
    })


@router.get("/image-generations/{result_id}/result")
def get_image_generation_result(result_id: str, user: AppUser = Depends(get_app_user)):
    if not re.fullmatch(r"[a-f0-9]{32}", result_id):
        raise HTTPException(404, "图片结果不存在或已过期")
    owner_id = re.sub(r"[^A-Za-z0-9_-]", "_", user.id)[:80]
    owner_dir = RESULTS_DIR / owner_id
    candidates = [path for path in owner_dir.glob(f"{result_id}.*") if path.suffix.lower() in {".png", ".jpg", ".webp"}]
    if not candidates:
        raise HTTPException(404, "图片结果不存在或已过期")
    path = candidates[0]
    if path.stat().st_mtime < time.time() - 24 * 60 * 60:
        path.unlink(missing_ok=True)
        raise HTTPException(404, "图片结果已过期，请重新生成")
    media_type = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}[path.suffix.lower()]
    return FileResponse(path, media_type=media_type, filename=f"{result_id}{path.suffix}")
