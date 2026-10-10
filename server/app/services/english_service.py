import json
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import EnglishScene, EnglishStudyRecord, EnglishUnit, utcnow


def scene_dict(row: EnglishScene) -> dict:
    return {"id": row.id, "title": row.title, "description": row.description, "level": row.level,
            "sortOrder": row.sort_order, "isPublished": row.is_published}


def unit_dict(row: EnglishUnit, include_content: bool = True) -> dict:
    item = {"id": row.id, "sceneId": row.scene_id, "title": row.title, "level": row.level,
            "durationMin": row.duration_min, "goal": row.goal, "sortOrder": row.sort_order,
            "isPublished": row.is_published}
    if include_content:
        try:
            item["content"] = json.loads(row.content_json or "{}")
        except (TypeError, json.JSONDecodeError):
            item["content"] = {}
    return item


def list_public_scenes(db: Session) -> list[dict]:
    scenes = db.query(EnglishScene).filter(EnglishScene.is_published.is_(True)).order_by(EnglishScene.sort_order, EnglishScene.title).all()
    output = []
    for scene in scenes:
        item = scene_dict(scene)
        item["units"] = [unit_dict(unit, False) for unit in db.query(EnglishUnit).filter(
            EnglishUnit.scene_id == scene.id, EnglishUnit.is_published.is_(True)
        ).order_by(EnglishUnit.sort_order, EnglishUnit.title).all()]
        output.append(item)
    return output


def complete_unit(db: Session, user_id: str, unit_id: str) -> dict:
    now = utcnow()
    row = EnglishStudyRecord(user_id=user_id, unit_id=unit_id, completed_at=now, next_review_at=now + timedelta(days=1))
    db.add(row)
    db.commit()
    return {"id": row.id, "completedAt": row.completed_at.isoformat(), "nextReviewAt": row.next_review_at.isoformat()}
