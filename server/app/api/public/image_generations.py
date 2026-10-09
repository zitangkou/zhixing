"""Authenticated image style generation endpoints."""

import re
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_app_user
from app.core.response import ApiResponse
from app.database import get_db
from app.models import AppUser
from app.product import ProductContext, get_product_context
from app.services.image_generation_service import MAX_INPUT_BYTES, RESULTS_DIR, generate_style_image
from app.upload_paths import detect_image_ext

router = APIRouter()


@router.post("/image-generations")
async def create_image_generation(
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
    try:
        result_id = await run_in_threadpool(generate_style_image, db, product, style_id, raw, mime, user.id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        # Do not return provider response bodies, prompts, or credentials to the mini-program.
        raise HTTPException(502, "图片生成服务暂时失败，请稍后重试") from exc
    return ApiResponse.ok({"resultId": result_id, "status": "succeeded"}, message="图片生成成功")


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
