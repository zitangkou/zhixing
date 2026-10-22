import json
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import EnglishScene, EnglishStudyAttempt, EnglishStudyRecord, EnglishUnit, EnglishUnitProgress, gen_id, utcnow
from app.services.activity_service import record_event

REVIEW_INTERVALS_DAYS = (1, 3, 7, 14)


def scene_dict(row: EnglishScene) -> dict:
    return {"id": row.id, "title": row.title, "description": row.description, "level": row.level,
            "sortOrder": row.sort_order, "isPublished": row.is_published}


def unit_dict(row: EnglishUnit, include_content: bool = True, public: bool = False) -> dict:
    item = {"id": row.id, "sceneId": row.scene_id, "title": row.title, "level": row.level,
            "durationMin": row.duration_min, "goal": row.goal, "sortOrder": row.sort_order,
            "isPublished": row.is_published}
    if include_content:
        try:
            content = json.loads(row.content_json or "{}")
            if public and isinstance(content, dict):
                item["content"] = _public_content(content)
            else:
                item["content"] = content
        except (TypeError, json.JSONDecodeError):
            item["content"] = {}
    return item


def _public_content(content: dict) -> dict:
    """Expose learning material only; omit editorial/rights notes and unknown admin fields."""
    allowed = {"transcript", "dialogue", "phrases", "prompt", "tasks", "vocabulary", "grammar", "tips"}
    result = {key: content[key] for key in allowed if key in content}
    media = content.get("media")
    if isinstance(media, dict):
        media_keys = {"type", "audioUrl", "videoUrl", "posterUrl", "sourceUrl", "rightsStatus", "startSeconds", "endSeconds"}
        result["media"] = {key: media[key] for key in media_keys if key in media}
    if isinstance(content.get("dialogueAudioUrl"), str):
        result["dialogueAudioUrl"] = content["dialogueAudioUrl"]
    for key in ("transcript", "dialogue"):
        turns = result.get(key)
        if isinstance(turns, list):
            result[key] = [
                {field: turn[field] for field in ("speaker", "en", "zh", "audioUrl", "startSeconds", "endSeconds") if field in turn}
                for turn in turns if isinstance(turn, dict)
            ]
    return result


def list_public_scenes(db: Session) -> list[dict]:
    scenes = db.query(EnglishScene).filter(EnglishScene.is_published.is_(True)).order_by(EnglishScene.sort_order, EnglishScene.title).all()
    output = []
    for scene in scenes:
        item = scene_dict(scene)
        # Published lesson content is returned with the catalogue so the mini-program
        # can render the learning flow without a second request per unit.
        item["units"] = [unit_dict(unit, public=True) for unit in db.query(EnglishUnit).filter(
            EnglishUnit.scene_id == scene.id, EnglishUnit.is_published.is_(True)
        ).order_by(EnglishUnit.sort_order, EnglishUnit.title).all()]
        output.append(item)
    return output


def complete_unit(db: Session, user_id: str, unit_id: str) -> dict:
    now = utcnow().replace(tzinfo=None)
    row = EnglishStudyRecord(user_id=user_id, unit_id=unit_id, completed_at=now, next_review_at=now + timedelta(days=1))
    db.add(row)
    db.commit()
    return {"id": row.id, "completedAt": row.completed_at.isoformat(), "nextReviewAt": row.next_review_at.isoformat()}


def learner_progress(db: Session, user_id: str) -> dict:
    states = db.query(EnglishUnitProgress).filter_by(user_id=user_id).all()
    state_by_unit = {row.unit_id: row for row in states}
    # Include pre-upgrade histories so existing learners keep their completed courses/review dates.
    legacy = db.query(EnglishStudyRecord).filter_by(user_id=user_id).order_by(EnglishStudyRecord.completed_at.desc()).all()
    for row in legacy:
        if row.unit_id not in state_by_unit:
            state_by_unit[row.unit_id] = row
    now = utcnow().replace(tzinfo=None)
    due = []
    for unit_id, state in state_by_unit.items():
        next_review = state.next_review_at
        if next_review and next_review <= now:
            unit = db.get(EnglishUnit, unit_id)
            if unit and unit.is_published:
                due.append({"unitId": unit_id, "title": unit.title, "level": unit.level,
                            "nextReviewAt": next_review.isoformat(), "reviewStage": getattr(state, "review_stage", 0)})
    due.sort(key=lambda item: item["nextReviewAt"])
    return {"completedUnitIds": list(state_by_unit), "dueReviews": due[:30], "completedUnits": len(state_by_unit)}


def submit_study_result(db: Session, user_id: str, unit_id: str, attempt_id: str, result: str) -> dict:
    previous = db.query(EnglishStudyAttempt).filter_by(user_id=user_id, attempt_id=attempt_id).first()
    if previous:
        if previous.unit_id != unit_id:
            raise ValueError("attempt_id 已用于其他课程")
        state = db.query(EnglishUnitProgress).filter_by(user_id=user_id, unit_id=unit_id).first()
        return {"completed": True, "duplicate": True,
                "nextReviewAt": state.next_review_at.isoformat() if state and state.next_review_at else None,
                "reviewStage": state.review_stage if state else 0}

    now = utcnow().replace(tzinfo=None)
    state = db.query(EnglishUnitProgress).filter_by(user_id=user_id, unit_id=unit_id).first()
    if state is None:
        state = EnglishUnitProgress(user_id=user_id, unit_id=unit_id, completed_at=now, last_studied_at=now,
                                    next_review_at=now + timedelta(days=1), review_stage=0, review_count=0)
        db.add(state)
    else:
        state.last_studied_at = now
        state.review_count += 1
        if result == "independent":
            state.review_stage = min(state.review_stage + 1, len(REVIEW_INTERVALS_DAYS) - 1)
            next_days = REVIEW_INTERVALS_DAYS[state.review_stage]
        else:
            next_days = 1
        state.next_review_at = now + timedelta(days=next_days)
    state.last_result = result
    db.add(EnglishStudyAttempt(user_id=user_id, unit_id=unit_id, attempt_id=attempt_id, result=result, created_at=now))
    history = EnglishStudyRecord(id=gen_id("enr"), user_id=user_id, unit_id=unit_id, completed_at=now,
                                 next_review_at=state.next_review_at, review_stage=state.review_stage)
    db.add(history)
    record_event(db, user_id, "english_study_completed", {"unitId": unit_id, "result": result,
                 "reviewStage": state.review_stage}, commit=False)
    db.commit()
    return {"completed": True, "duplicate": False, "nextReviewAt": state.next_review_at.isoformat(),
            "reviewStage": state.review_stage}
