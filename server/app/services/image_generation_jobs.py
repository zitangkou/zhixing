"""Background execution and safe diagnostics for image generation requests."""

from datetime import timedelta
from pathlib import Path

import httpx

from app.database import SessionLocal
from app.models import ImageGenerationJob
from app.product import resolve_product
from app.services.image_generation_service import ImageProviderHTTPError, generate_style_image
from app.services.image_model_service import resolve_image_model
from app.services.image_style_service import get_image_style_config
from app.timezone import now


def _failure(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, ImageProviderHTTPError):
        code_suffix = f"_{exc.provider_code}" if exc.provider_code else ""
        error_code = f"provider_http_{exc.status_code}{code_suffix}"[:64]
        message = f"{exc.stage}返回 HTTP {exc.status_code}。"
        if exc.provider_code:
            message += f"服务商错误码：{exc.provider_code}。"
        if exc.status_code == 404 and "下载" not in exc.stage:
            message += "请核对服务区域、模型开通状态和 API 地址。"
        elif exc.status_code == 404:
            message += "服务商返回的图片链接不可用，请重新测试。"
        else:
            message += "请检查模型配置和服务商控制台状态。"
        return error_code, message
    if isinstance(exc, httpx.TimeoutException):
        return "provider_timeout", "模型服务响应超时。请检查模型服务状态与超时配置后重试。"
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return f"provider_http_{status}", f"模型服务返回 HTTP {status}。请检查模型配置、额度和服务商状态。"
    if isinstance(exc, httpx.RequestError):
        return "provider_connection_error", "无法连接模型服务，请检查 API 地址和网络。"
    if isinstance(exc, ValueError):
        return "generation_rejected", str(exc)[:500]
    return "generation_error", f"图片生成失败（{type(exc).__name__}）。请查看服务端日志并检查模型服务。"


def run_image_generation_job(job_id: str) -> None:
    """Run in FastAPI BackgroundTasks; every invocation owns its DB session."""
    db = SessionLocal()
    input_path: Path | None = None
    try:
        job = db.get(ImageGenerationJob, job_id)
        if not job or job.status not in {"queued", "running"}:
            return
        input_path = Path(job.input_path) if job.input_path else None
        job.status = "running"
        job.started_at = now()
        db.commit()
        if not input_path or not input_path.is_file():
            raise ValueError("任务原图暂存文件不存在，请重新上传后生成")
        raw = input_path.read_bytes()
        mime = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(input_path.suffix.lower())
        if not mime:
            raise ValueError("原图格式不受支持，请重新上传")
        product = resolve_product(job.product_key)
        style = next((item for item in get_image_style_config(db)["items"] if item["id"] == job.style_id), None)
        model_id = style.get("modelId", "") if style else ""
        if model_id:
            model = resolve_image_model(db, model_id)
            job.model_id = model.get("id", model_id)
            job.provider = model.get("provider", "")
            db.commit()
        result_id = generate_style_image(db, product, job.style_id, raw, mime, job.user_id, allow_draft=job.allow_draft)
        job = db.get(ImageGenerationJob, job_id)
        if job:
            job.status = "succeeded"
            job.result_id = result_id
            job.error_code = ""
            job.error_message = ""
            job.completed_at = now()
            db.commit()
    except Exception as exc:
        code, message = _failure(exc)
        db.rollback()
        job = db.get(ImageGenerationJob, job_id)
        if job:
            job.status = "failed"
            job.error_code = code
            job.error_message = message
            job.completed_at = now()
            db.commit()
        # Keep detailed exception in server logs; avoid credentials, prompts, or response bodies.
        print(f"[image-generation] job={job_id} failed code={code} error_type={type(exc).__name__}")
    finally:
        if input_path:
            input_path.unlink(missing_ok=True)
        db.close()


def fail_interrupted_image_jobs() -> None:
    """Mark in-process jobs interrupted by a process restart as visible failures."""
    db = SessionLocal()
    try:
        rows = db.query(ImageGenerationJob).filter(ImageGenerationJob.status.in_(["queued", "running"])).all()
        for job in rows:
            if job.input_path:
                Path(job.input_path).unlink(missing_ok=True)
            job.status = "failed"
            job.error_code = "server_restarted"
            job.error_message = "服务在任务完成前重启，请重新提交生成。"
            job.completed_at = now()
        if rows:
            db.commit()
    finally:
        db.close()


def prune_old_image_jobs(days: int = 30) -> None:
    db = SessionLocal()
    try:
        cutoff = now() - timedelta(days=days)
        db.query(ImageGenerationJob).filter(ImageGenerationJob.created_at < cutoff).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
