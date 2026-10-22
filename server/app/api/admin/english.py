import json
import math
import re
from html import unescape
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import EnglishASRJob, EnglishScene, EnglishStudyRecord, EnglishUnit, gen_id
from app.schemas.english import EnglishSceneInput, EnglishUnitInput
from app.services.english_asr_service import ASR_MAX_BYTES, SUPPORTED_ASR_EXTENSIONS, is_configured, run_english_asr_job
from app.services.english_service import scene_dict, unit_dict
from app.upload_paths import DATA_DIR, uploads_subdir
from app.timezone import now

router = APIRouter(prefix="/english", tags=["英语学习管理"])

MEDIA_MAX_BYTES = 80 * 1024 * 1024
SUBTITLE_MAX_BYTES = 2 * 1024 * 1024


def _media_extension(filename: str, raw: bytes) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext == ".mp3" and (raw.startswith(b"ID3") or raw[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
        return ext
    if ext == ".wav" and len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WAVE":
        return ext
    if ext == ".aac" and len(raw) >= 2 and raw[0] == 0xFF and raw[1] & 0xF6 == 0xF0:
        return ext
    if ext in {".m4a", ".mp4", ".mov"} and len(raw) >= 12 and raw[4:8] == b"ftyp":
        return ext
    return None


def _subtitle_seconds(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours, minutes, seconds = "0", parts[0], parts[1]
    else:
        raise ValueError("时间格式无效")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_subtitles(raw: bytes, filename: str) -> list[dict]:
    if Path(filename).suffix.lower() not in {".srt", ".vtt"}:
        raise ValueError("请上传 SRT 或 VTT 字幕文件")
    text = raw.decode("utf-8-sig")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cues: list[dict] = []
    timing = re.compile(r"^\s*((?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{1,3})\s+-->\s+((?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{1,3})")
    index = 0
    while index < len(lines):
        match = timing.match(lines[index])
        if not match:
            index += 1
            continue
        start = _subtitle_seconds(match.group(1))
        end = _subtitle_seconds(match.group(2))
        index += 1
        cue_lines = []
        while index < len(lines) and lines[index].strip():
            cue_lines.append(lines[index].strip())
            index += 1
        cue_text = " ".join(cue_lines)
        speaker_match = re.search(r"<v\s+([^>]+)>", cue_text, flags=re.IGNORECASE)
        speaker = speaker_match.group(1).strip() if speaker_match else "Speaker"
        cue_text = unescape(re.sub(r"<[^>]*>", "", cue_text)).strip()
        if cue_text and end > start:
            cues.append({"speaker": speaker[:64], "en": cue_text, "zh": "", "startSeconds": start, "endSeconds": end})
        if len(cues) > 1000:
            raise ValueError("字幕超过 1000 条，请先拆分文件")
    if not cues:
        raise ValueError("没有识别到有效字幕时间轴")
    return cues


@router.post("/media-upload")
async def upload_media(file: UploadFile = File(...), _admin=Depends(require_permission("english:write"))):
    filename = file.filename or ""
    raw = await file.read(MEDIA_MAX_BYTES + 1)
    if len(raw) > MEDIA_MAX_BYTES:
        raise HTTPException(413, "素材文件不能超过 80MB")
    ext = _media_extension(filename, raw)
    if not ext:
        raise HTTPException(415, "仅支持格式正确的 MP3、M4A、WAV、AAC、MP4 或 MOV 文件")
    folder = uploads_subdir("english")
    saved_name = f"{uuid4().hex}{ext}"
    (folder / saved_name).write_bytes(raw)
    kind = "video" if ext in {".mp4", ".mov"} else "audio"
    return ApiResponse.ok({"url": f"/uploads/english/{saved_name}", "kind": kind, "filename": filename})


@router.post("/subtitle-import")
async def import_subtitles(file: UploadFile = File(...), _admin=Depends(require_permission("english:write"))):
    raw = await file.read(SUBTITLE_MAX_BYTES + 1)
    if len(raw) > SUBTITLE_MAX_BYTES:
        raise HTTPException(413, "字幕文件不能超过 2MB")
    try:
        transcript = parse_subtitles(raw, file.filename or "")
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return ApiResponse.ok({"transcript": transcript, "count": len(transcript)}, message="字幕已导入草稿，请校对后保存")


@router.post("/subtitle-transcribe")
async def transcribe_subtitles(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _admin=Depends(require_permission("english:write")),
    db: Session = Depends(get_db),
):
    if not is_configured():
        raise HTTPException(503, "尚未配置言遇英语 ASR 服务，请在服务端 .env 配置 YANYU_ENGLISH_ASR_API_KEY")
    raw = await file.read(ASR_MAX_BYTES + 1)
    if not raw or len(raw) > ASR_MAX_BYTES:
        raise HTTPException(413, "自动转写文件需大于 0 且不超过 20MB")
    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() not in SUPPORTED_ASR_EXTENSIONS or not _media_extension(filename, raw):
        raise HTTPException(415, "自动转写仅支持格式正确的 MP3、M4A、WAV 或 MP4 文件")
    job_id = uuid4().hex
    input_dir = DATA_DIR / "private" / "english-asr-inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / f"{job_id}{Path(filename).suffix.lower()}"
    input_path.write_bytes(raw)
    input_path.chmod(0o600)
    db.add(EnglishASRJob(id=job_id, status="queued", filename=filename, input_path=str(input_path)))
    db.commit()
    background_tasks.add_task(run_english_asr_job, job_id)
    return ApiResponse.ok({"id": job_id, "status": "queued"}, message="字幕生成任务已提交")


@router.get("/subtitle-transcribe/{job_id}")
def get_subtitle_transcription(job_id: str, _admin=Depends(require_permission("english:write")), db: Session = Depends(get_db)):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise HTTPException(404, "字幕任务不存在")
    job = db.get(EnglishASRJob, job_id)
    if not job:
        raise HTTPException(404, "字幕任务不存在")
    transcript = json.loads(job.transcript_json or "[]") if job.status == "succeeded" else []
    return ApiResponse.ok({"id": job.id, "status": job.status, "transcript": transcript,
                           "count": len(transcript), "errorMessage": job.error_message or ""})


def _validate_published_media(body: EnglishUnitInput) -> None:
    if not body.is_published:
        return
    content = body.content or {}
    transcript = content.get("transcript") if isinstance(content.get("transcript"), list) else content.get("dialogue")
    transcript = transcript if isinstance(transcript, list) else []
    phrases = content.get("phrases") if isinstance(content.get("phrases"), list) else []
    tasks = content.get("tasks") if isinstance(content.get("tasks"), dict) else {}
    prompt = content.get("prompt") or tasks.get("roleplayPrompt") or tasks.get("retellPrompt")
    if sum(1 for line in transcript if isinstance(line, dict) and str(line.get("en", "")).strip()) < 2:
        raise HTTPException(422, "发布课程至少需要两句英文台词")
    if sum(1 for phrase in phrases if isinstance(phrase, dict) and str(phrase.get("en", "")).strip()) < 2:
        raise HTTPException(422, "发布课程至少需要两个核心表达")
    if not isinstance(prompt, str) or not prompt.strip():
        raise HTTPException(422, "发布课程需要填写自主表达任务")
    for line in transcript:
        if not isinstance(line, dict):
            continue
        start, end = line.get("startSeconds"), line.get("endSeconds")
        if (start is None) != (end is None):
            raise HTTPException(422, "逐句时间轴需要同时填写起始秒和结束秒")
        if start is not None:
            try:
                if not math.isfinite(float(start)) or not math.isfinite(float(end)) or float(start) < 0 or float(end) <= float(start):
                    raise HTTPException(422, "逐句结束秒必须大于起始秒")
            except (TypeError, ValueError):
                raise HTTPException(422, "逐句时间轴必须填写有效秒数")
    media = content.get("media") or {}
    if not isinstance(media, dict):
        media = {}
    direct_urls = [media.get("audioUrl"), media.get("videoUrl"), content.get("dialogueAudioUrl")]
    has_direct_media = any(isinstance(url, str) and url.strip() for url in direct_urls)
    has_source = bool(isinstance(media.get("sourceUrl"), str) and media["sourceUrl"].strip())
    rights = media.get("rightsStatus")
    for url in direct_urls:
        if isinstance(url, str) and url.strip():
            parsed = urlparse(url.strip())
            if parsed.scheme != "https" or not parsed.hostname or parsed.hostname in {"localhost", "127.0.0.1"}:
                raise HTTPException(422, "小程序媒体地址必须使用可访问的 HTTPS 域名")
    if rights == "rejected" and (has_direct_media or has_source):
        raise HTTPException(422, "不可使用的素材不能发布")
    if has_direct_media and rights != "licensed_hosting":
        raise HTTPException(422, "小程序直播放地址需确认已获托管许可")
    if has_source and rights == "pending_review":
        raise HTTPException(422, "请先完成素材授权核验再发布")


@router.get("/summary")
def summary(db: Session = Depends(get_db), _admin=Depends(require_permission("english:read"))):
    return ApiResponse.ok({"scenes": db.query(EnglishScene).count(), "units": db.query(EnglishUnit).count(),
                           "publishedUnits": db.query(EnglishUnit).filter(EnglishUnit.is_published.is_(True)).count(),
                           "completions": db.query(EnglishStudyRecord).count()})


@router.get("/records")
def list_records(db: Session = Depends(get_db), _admin=Depends(require_permission("english:read"))):
    rows = db.query(EnglishStudyRecord, EnglishUnit).join(EnglishUnit, EnglishUnit.id == EnglishStudyRecord.unit_id).order_by(
        EnglishStudyRecord.completed_at.desc()
    ).limit(200).all()
    return ApiResponse.ok([{"id": record.id, "learner": "学员" if record.user_id == "guest-local" else f"学员-{record.user_id[-4:]}",
                            "unitTitle": unit.title, "completedAt": record.completed_at.isoformat(),
                            "nextReviewAt": record.next_review_at.isoformat()} for record, unit in rows])


@router.get("/scenes")
def list_scenes(db: Session = Depends(get_db), _admin=Depends(require_permission("english:read"))):
    return ApiResponse.ok([scene_dict(row) for row in db.query(EnglishScene).order_by(EnglishScene.sort_order, EnglishScene.title).all()])


@router.post("/scenes")
def create_scene(body: EnglishSceneInput, db: Session = Depends(get_db), _admin=Depends(require_permission("english:write"))):
    row = EnglishScene(id=gen_id("ens"), title=body.title, description=body.description, level=body.level,
                       sort_order=body.sort_order, is_published=body.is_published)
    db.add(row); db.commit(); db.refresh(row)
    return ApiResponse.ok(scene_dict(row))


@router.put("/scenes/{scene_id}")
def update_scene(scene_id: str, body: EnglishSceneInput, db: Session = Depends(get_db), _admin=Depends(require_permission("english:write"))):
    row = db.get(EnglishScene, scene_id)
    if not row: raise HTTPException(404, "场景不存在")
    for key, value in body.model_dump().items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    return ApiResponse.ok(scene_dict(row))


@router.delete("/scenes/{scene_id}")
def delete_scene(scene_id: str, db: Session = Depends(get_db), _admin=Depends(require_permission("english:write"))):
    row = db.get(EnglishScene, scene_id)
    if not row: raise HTTPException(404, "场景不存在")
    if db.query(EnglishUnit).filter(EnglishUnit.scene_id == scene_id).first(): raise HTTPException(409, "场景下仍有课程，请先移除课程")
    db.delete(row); db.commit()
    return ApiResponse.ok({"ok": True})


@router.get("/units")
def list_units(db: Session = Depends(get_db), _admin=Depends(require_permission("english:read"))):
    return ApiResponse.ok([unit_dict(row) for row in db.query(EnglishUnit).order_by(EnglishUnit.sort_order, EnglishUnit.title).all()])


@router.post("/units")
def create_unit(body: EnglishUnitInput, db: Session = Depends(get_db), _admin=Depends(require_permission("english:write"))):
    if not db.get(EnglishScene, body.scene_id): raise HTTPException(404, "所属场景不存在")
    _validate_published_media(body)
    data = body.model_dump()
    row = EnglishUnit(id=gen_id("enu"), scene_id=data.pop("scene_id"), content_json=json.dumps(data.pop("content"), ensure_ascii=False), **data)
    db.add(row); db.commit(); db.refresh(row)
    return ApiResponse.ok(unit_dict(row))


@router.put("/units/{unit_id}")
def update_unit(unit_id: str, body: EnglishUnitInput, db: Session = Depends(get_db), _admin=Depends(require_permission("english:write"))):
    row = db.get(EnglishUnit, unit_id)
    if not row: raise HTTPException(404, "课程不存在")
    if not db.get(EnglishScene, body.scene_id): raise HTTPException(404, "所属场景不存在")
    _validate_published_media(body)
    data = body.model_dump()
    data["content_json"] = json.dumps(data.pop("content"), ensure_ascii=False)
    data["scene_id"] = data.pop("scene_id")
    for key, value in data.items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    return ApiResponse.ok(unit_dict(row))


@router.delete("/units/{unit_id}")
def delete_unit(unit_id: str, db: Session = Depends(get_db), _admin=Depends(require_permission("english:write"))):
    row = db.get(EnglishUnit, unit_id)
    if not row: raise HTTPException(404, "课程不存在")
    db.delete(row); db.commit()
    return ApiResponse.ok({"ok": True})
