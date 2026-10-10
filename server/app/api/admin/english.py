import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import EnglishScene, EnglishStudyRecord, EnglishUnit, gen_id
from app.schemas.english import EnglishSceneInput, EnglishUnitInput
from app.services.english_service import scene_dict, unit_dict

router = APIRouter(prefix="/english", tags=["英语学习管理"])


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
    data = body.model_dump()
    row = EnglishUnit(id=gen_id("enu"), scene_id=data.pop("scene_id"), content_json=json.dumps(data.pop("content"), ensure_ascii=False), **data)
    db.add(row); db.commit(); db.refresh(row)
    return ApiResponse.ok(unit_dict(row))


@router.put("/units/{unit_id}")
def update_unit(unit_id: str, body: EnglishUnitInput, db: Session = Depends(get_db), _admin=Depends(require_permission("english:write"))):
    row = db.get(EnglishUnit, unit_id)
    if not row: raise HTTPException(404, "课程不存在")
    if not db.get(EnglishScene, body.scene_id): raise HTTPException(404, "所属场景不存在")
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
