import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import PhotographyCase, PhotographyLesson, PhotographyStage, gen_id
from app.schemas.photography import PhotographyCaseInput, PhotographyLessonInput, PhotographyStageInput
from app.services.photography_service import case_dict, case_input_values, lesson_dict, stage_dict
from app.upload_paths import UPLOADS_DIR

router = APIRouter(prefix="/photography", tags=["摄影学习管理"])


@router.post("/cases/upload-image")
async def upload_case_image(file: UploadFile = File(...), _admin=Depends(require_permission("photography:write"))):
    from uuid import uuid4

    raw = await file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, "案例图片不能超过 5MB")
    ext = ".png" if raw.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg" if raw.startswith(b"\xff\xd8\xff") else ""
    if not ext:
        raise HTTPException(415, "请上传 PNG 或 JPEG 图片")
    folder = UPLOADS_DIR / "photography-cases"
    folder.mkdir(parents=True, exist_ok=True)
    filename = uuid4().hex + ext
    (folder / filename).write_bytes(raw)
    return ApiResponse.ok({"url": f"/uploads/photography-cases/{filename}"})


@router.get("/summary")
def summary(db: Session = Depends(get_db), _admin=Depends(require_permission("photography:read"))):
    return ApiResponse.ok({"stages": db.query(PhotographyStage).count(),
                           "lessons": db.query(PhotographyLesson).count(),
                           "publishedLessons": db.query(PhotographyLesson).filter(PhotographyLesson.is_published.is_(True)).count(),
                           "cases": db.query(PhotographyCase).count(),
                           "publishedCases": db.query(PhotographyCase).filter(PhotographyCase.is_published.is_(True)).count()})


@router.get("/cases")
def list_cases(db: Session = Depends(get_db), _admin=Depends(require_permission("photography:read"))):
    rows = db.query(PhotographyCase).order_by(PhotographyCase.sort_order, PhotographyCase.title).all()
    return ApiResponse.ok([case_dict(row) for row in rows])


@router.post("/cases")
def create_case(body: PhotographyCaseInput, db: Session = Depends(get_db), _admin=Depends(require_permission("photography:write"))):
    row = PhotographyCase(id=gen_id("phc"), **case_input_values(body))
    db.add(row); db.commit(); db.refresh(row)
    return ApiResponse.ok(case_dict(row))


@router.put("/cases/{case_id}")
def update_case(case_id: str, body: PhotographyCaseInput, db: Session = Depends(get_db), _admin=Depends(require_permission("photography:write"))):
    row = db.get(PhotographyCase, case_id)
    if not row: raise HTTPException(404, "摄影案例不存在")
    for key, value in case_input_values(body).items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    return ApiResponse.ok(case_dict(row))


@router.delete("/cases/{case_id}")
def delete_case(case_id: str, db: Session = Depends(get_db), _admin=Depends(require_permission("photography:write"))):
    row = db.get(PhotographyCase, case_id)
    if not row: raise HTTPException(404, "摄影案例不存在")
    db.delete(row); db.commit()
    return ApiResponse.ok({"ok": True})


@router.get("/stages")
def list_stages(db: Session = Depends(get_db), _admin=Depends(require_permission("photography:read"))):
    rows = db.query(PhotographyStage).order_by(PhotographyStage.sort_order, PhotographyStage.title).all()
    return ApiResponse.ok([stage_dict(row) for row in rows])


@router.post("/stages")
def create_stage(body: PhotographyStageInput, db: Session = Depends(get_db), _admin=Depends(require_permission("photography:write"))):
    row = PhotographyStage(id=gen_id("phs"), title=body.title.strip(), items=body.items,
        description=body.description, sort_order=body.sort_order, is_published=body.is_published)
    db.add(row); db.commit(); db.refresh(row)
    return ApiResponse.ok(stage_dict(row))


@router.put("/stages/{stage_id}")
def update_stage(stage_id: str, body: PhotographyStageInput, db: Session = Depends(get_db), _admin=Depends(require_permission("photography:write"))):
    row = db.get(PhotographyStage, stage_id)
    if not row: raise HTTPException(404, "知识阶段不存在")
    for key, value in body.model_dump().items(): setattr(row, key, value.strip() if key == "title" else value)
    db.commit(); db.refresh(row)
    return ApiResponse.ok(stage_dict(row))


@router.delete("/stages/{stage_id}")
def delete_stage(stage_id: str, db: Session = Depends(get_db), _admin=Depends(require_permission("photography:write"))):
    row = db.get(PhotographyStage, stage_id)
    if not row: raise HTTPException(404, "知识阶段不存在")
    if db.query(PhotographyLesson).filter(PhotographyLesson.stage_id == stage_id).first():
        raise HTTPException(409, "阶段下仍有课程，请先调整课程所属阶段")
    db.delete(row); db.commit()
    return ApiResponse.ok({"ok": True})


@router.get("/lessons")
def list_lessons(db: Session = Depends(get_db), _admin=Depends(require_permission("photography:read"))):
    rows = db.query(PhotographyLesson).order_by(PhotographyLesson.sort_order, PhotographyLesson.title).all()
    return ApiResponse.ok([lesson_dict(row) for row in rows])


@router.post("/lessons")
def create_lesson(body: PhotographyLessonInput, db: Session = Depends(get_db), _admin=Depends(require_permission("photography:write"))):
    if not db.get(PhotographyStage, body.stage_id): raise HTTPException(404, "所属知识阶段不存在")
    data = body.model_dump()
    data["steps_json"] = json.dumps(data.pop("steps"), ensure_ascii=False)
    row = PhotographyLesson(id=gen_id("phl"), **data)
    db.add(row); db.commit(); db.refresh(row)
    return ApiResponse.ok(lesson_dict(row))


@router.put("/lessons/{lesson_id}")
def update_lesson(lesson_id: str, body: PhotographyLessonInput, db: Session = Depends(get_db), _admin=Depends(require_permission("photography:write"))):
    row = db.get(PhotographyLesson, lesson_id)
    if not row: raise HTTPException(404, "技巧课程不存在")
    if not db.get(PhotographyStage, body.stage_id): raise HTTPException(404, "所属知识阶段不存在")
    data = body.model_dump()
    data["steps_json"] = json.dumps(data.pop("steps"), ensure_ascii=False)
    for key, value in data.items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    return ApiResponse.ok(lesson_dict(row))


@router.delete("/lessons/{lesson_id}")
def delete_lesson(lesson_id: str, db: Session = Depends(get_db), _admin=Depends(require_permission("photography:write"))):
    row = db.get(PhotographyLesson, lesson_id)
    if not row: raise HTTPException(404, "技巧课程不存在")
    db.delete(row); db.commit()
    return ApiResponse.ok({"ok": True})
