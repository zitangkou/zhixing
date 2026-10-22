"""Optional server-side ASR for authorized English learning media."""

import asyncio
import json
import math
from datetime import timedelta
from pathlib import Path

import httpx

from app.config import get_settings
from app.database import SessionLocal
from app.models import EnglishASRJob
from app.timezone import now


SUPPORTED_ASR_EXTENSIONS = {".mp3", ".m4a", ".wav", ".mp4"}
ASR_MAX_BYTES = 20 * 1024 * 1024


class EnglishASRError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def is_configured() -> bool:
    return bool(get_settings().yanyu_english_asr_api_key.strip())


def normalize_segments(payload: dict) -> list[dict]:
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        raise EnglishASRError("转写服务未返回逐句时间轴，请改用 SRT/VTT 字幕导入")
    transcript = []
    for segment in raw_segments[:1000]:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        try:
            start = float(segment.get("start"))
            end = float(segment.get("end"))
        except (TypeError, ValueError):
            continue
        if not text or not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            continue
        transcript.append({
            "speaker": "Speaker",
            "en": text,
            "zh": "",
            "startSeconds": round(start, 3),
            "endSeconds": round(end, 3),
        })
    if not transcript:
        raise EnglishASRError("转写结果没有可用的逐句时间轴，请改用 SRT/VTT 字幕导入")
    return transcript


async def transcribe_english_audio(raw: bytes, filename: str) -> list[dict]:
    settings = get_settings()
    if not settings.yanyu_english_asr_api_key.strip():
        raise EnglishASRError("尚未配置言遇英语 ASR 服务，请在服务端 .env 配置 YANYU_ENGLISH_ASR_API_KEY", 503)
    if not raw or len(raw) > ASR_MAX_BYTES:
        raise EnglishASRError("自动转写文件需大于 0 且不超过 20MB", 413)
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_ASR_EXTENSIONS:
        raise EnglishASRError("自动转写支持 MP3、M4A、WAV 或 MP4；MOV/AAC 请先转换格式", 415)
    mime = {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
        ".mp4": "video/mp4",
    }[ext]
    endpoint = f"{settings.yanyu_english_asr_base_url.rstrip('/')}/audio/transcriptions"
    try:
        async with httpx.AsyncClient(timeout=settings.yanyu_english_asr_timeout_seconds) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {settings.yanyu_english_asr_api_key.strip()}"},
                data={
                    "model": settings.yanyu_english_asr_model.strip() or "whisper-1",
                    "response_format": "verbose_json",
                    "language": "en",
                },
                files={"file": (Path(filename).name or f"english-media{ext}", raw, mime)},
            )
        if response.is_error:
            raise EnglishASRError(f"ASR 服务返回 HTTP {response.status_code}，请检查服务地址、模型和额度")
        payload = response.json()
        if not isinstance(payload, dict):
            raise EnglishASRError("ASR 服务返回的数据格式无效")
        return normalize_segments(payload)
    except EnglishASRError:
        raise
    except httpx.TimeoutException as exc:
        raise EnglishASRError("ASR 转写超时，请缩短素材或增加服务端超时配置", 504) from exc
    except httpx.RequestError as exc:
        raise EnglishASRError("无法连接 ASR 服务，请检查服务地址和服务器网络", 502) from exc
    except (ValueError, TypeError) as exc:
        raise EnglishASRError("ASR 服务返回的数据格式无效") from exc


def run_english_asr_job(job_id: str) -> None:
    """Run a queued caption task without holding the request open."""
    db = SessionLocal()
    input_path: Path | None = None
    try:
        job = db.get(EnglishASRJob, job_id)
        if not job or job.status not in {"queued", "running"}:
            return
        input_path = Path(job.input_path) if job.input_path else None
        job.status = "running"
        job.started_at = now()
        db.commit()
        if not input_path or not input_path.is_file():
            raise EnglishASRError("转写源文件暂存失败，请重新选择素材", 422)
        transcript = asyncio.run(transcribe_english_audio(input_path.read_bytes(), job.filename))
        job = db.get(EnglishASRJob, job_id)
        if job:
            job.transcript_json = json.dumps(transcript, ensure_ascii=False)
            job.status = "succeeded"
            job.error_message = ""
            job.completed_at = now()
            db.commit()
    except Exception as exc:
        message = str(exc)[:500] if isinstance(exc, EnglishASRError) else "ASR 转写失败，请检查服务端日志和服务配置"
        db.rollback()
        job = db.get(EnglishASRJob, job_id)
        if job:
            job.status = "failed"
            job.error_message = message
            job.completed_at = now()
            db.commit()
        print(f"[english-asr] job={job_id} failed error_type={type(exc).__name__}")
    finally:
        if input_path:
            input_path.unlink(missing_ok=True)
        db.close()


def fail_interrupted_english_asr_jobs() -> None:
    """Mark in-process jobs interrupted by a server restart as visible failures."""
    db = SessionLocal()
    try:
        jobs = db.query(EnglishASRJob).filter(EnglishASRJob.status.in_(["queued", "running"])).all()
        for job in jobs:
            if job.input_path:
                Path(job.input_path).unlink(missing_ok=True)
            job.status = "failed"
            job.error_message = "服务在字幕生成完成前重启，请重新提交转写。"
            job.completed_at = now()
        if jobs:
            db.commit()
    finally:
        db.close()


def prune_old_english_asr_jobs(days: int = 30) -> None:
    db = SessionLocal()
    try:
        cutoff = now() - timedelta(days=days)
        db.query(EnglishASRJob).filter(EnglishASRJob.created_at < cutoff).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
