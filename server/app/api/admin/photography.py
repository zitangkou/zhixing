import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import PhotographyLesson, PhotographyStage, gen_id
from app.schemas.photography import PhotographyLessonInput, PhotographyStageInput
from app.services.photography_service import lesson_dict, stage_dict

router = APIRouter(prefix="/photography", tags=["摄影学习管理"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), _admin=Depends(require_permission("photography:read"))):
    return ApiResponse.ok({"stages": db.query(PhotographyStage).count(),
                           "lessons": db.query(PhotographyLesson).count(),
                           "publishedLessons": db.query(PhotographyLesson).filter(PhotographyLesson.is_published.is_(True)).count()})


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
