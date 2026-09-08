"""手动错题 service（行测刷题录入 + 艾宾浩斯调度）"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import AppUser, ManualWrong, gen_id
from app.schemas import ManualWrongCreate, ManualWrongOut, ManualWrongUpdate
from app.services.knowledge_service import resolve_knowledge_ref
from app.services.srs import is_due, now_naive, schedule_after_fail, schedule_after_success, schedule_first
from app.timezone import now


def _to_out(w: ManualWrong) -> ManualWrongOut:
    try:
        images = json.loads(w.images) if w.images else []
    except json.JSONDecodeError:
        images = []
    return ManualWrongOut(
        id=w.id,
        subject=w.subject or "",
        questionType=w.question_type or "",
        stem=w.stem or "",
        options=w.options or "",
        myAnswer=w.my_answer or "",
        correctAnswer=w.correct_answer or "",
        analysis=w.analysis or "",
        wrongReason=w.wrong_reason or "",
        note=w.note or "",
        images=images,
        source=w.source or "manual",
        knowledgeNodeId=getattr(w, "knowledge_node_id", None),
        knowledgeTreeKey=getattr(w, "knowledge_tree_key", None) or "",
        knowledgePath=getattr(w, "knowledge_path", None) or "",
        reviewCount=w.review_count,
        reviewStage=int(getattr(w, "review_stage", 0) or 0),
        nextReviewAt=getattr(w, "next_review_at", None),
        due=is_due(getattr(w, "next_review_at", None)) and not bool(w.mastered),
        mastered=w.mastered,
        lastWrongAt=w.last_wrong_at,
        createdAt=w.created_at,
    )


def list_wrongs(
    db: Session,
    user: AppUser,
    subject: str | None = None,
    mastered: bool | None = None,
    status: str | None = None,
) -> list[ManualWrongOut]:
    """status: review=今日到期未掌握 | waiting=未到期 | all/None=不按到期过滤"""
    q = db.query(ManualWrong).filter(ManualWrong.user_id == user.id)
    if subject:
        q = q.filter(ManualWrong.subject == subject)
    if mastered is not None:
        q = q.filter(ManualWrong.mastered == mastered)
    rows = q.order_by(ManualWrong.last_wrong_at.desc()).all()
    outs = [_to_out(w) for w in rows]
    if status == "review":
        outs = [o for o in outs if o.due and not o.mastered]
    elif status == "waiting":
        outs = [o for o in outs if not o.due and not o.mastered]
    return outs


def count_due_manual_wrongs(db: Session, user_id: str) -> int:
    ts = now_naive()
    return (
        db.query(ManualWrong)
        .filter(
            ManualWrong.user_id == user_id,
            ManualWrong.mastered.is_(False),
            (ManualWrong.next_review_at.is_(None)) | (ManualWrong.next_review_at <= ts),
        )
        .count()
    )


def count_waiting_manual_wrongs(db: Session, user_id: str) -> int:
    """未到期未掌握：今日可跳过。"""
    ts = now_naive()
    return (
        db.query(ManualWrong)
        .filter(
            ManualWrong.user_id == user_id,
            ManualWrong.mastered.is_(False),
            ManualWrong.next_review_at.isnot(None),
            ManualWrong.next_review_at > ts,
        )
        .count()
    )


DAILY_MANUAL_WRONG_CAP = 15


def recommend_manual_wrongs(db: Session, user: AppUser, limit: int = DAILY_MANUAL_WRONG_CAP) -> list[ManualWrongOut]:
    items = list_wrongs(db, user, mastered=False, status="review")
    items.sort(key=lambda o: (int(o.reviewStage or 0), -int(o.reviewCount or 0)))
    return items[: max(1, min(limit, DAILY_MANUAL_WRONG_CAP))]


def create_wrong(db: Session, user: AppUser, body: ManualWrongCreate, images: list[str] | None = None) -> ManualWrongOut:
    img_list = images if images is not None else (body.images or [])
    nid, tk, path = resolve_knowledge_ref(
        db,
        node_id=body.knowledgeNodeId,
        tree_key=body.knowledgeTreeKey,
        path=body.knowledgePath,
    )
    stage, next_at = schedule_first()
    w = ManualWrong(
        id=gen_id("mw"),
        user_id=user.id,
        subject=body.subject,
        question_type=body.questionType,
        stem=body.stem,
        options=body.options,
        my_answer=body.myAnswer,
        correct_answer=body.correctAnswer,
        analysis=body.analysis,
        wrong_reason=body.wrongReason,
        note=body.note,
        images=json.dumps(img_list, ensure_ascii=False),
        source=body.source,
        knowledge_node_id=nid,
        knowledge_tree_key=tk,
        knowledge_path=path,
        review_stage=stage,
        next_review_at=next_at,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return _to_out(w)


def review_wrong(db: Session, user: AppUser, wrong_id: str, result: str = "good") -> ManualWrongOut | None:
    """记录一次复习：good 推进间隔，again 重置。"""
    w = db.get(ManualWrong, wrong_id)
    if not w or w.user_id != user.id:
        return None
    result = (result or "good").strip().lower()
    if result == "again":
        stage, next_at = schedule_after_fail()
        w.review_stage = stage
        w.next_review_at = next_at
        w.mastered = False
    else:
        new_stage, next_at, mastered = schedule_after_success(int(w.review_stage or 0))
        w.review_stage = new_stage
        w.next_review_at = next_at
        w.mastered = mastered
    w.review_count = int(w.review_count or 0) + 1
    w.last_wrong_at = now()
    db.commit()
    db.refresh(w)
    return _to_out(w)


def update_wrong(db: Session, user: AppUser, wrong_id: str, body: ManualWrongUpdate, extra_images: list[str] | None = None) -> ManualWrongOut | None:
    w = db.get(ManualWrong, wrong_id)
    if not w or w.user_id != user.id:
        return None
    data = body.model_dump(exclude_unset=True)
    images_val = data.pop("images", None)
    kb_touched = any(k in data for k in ("knowledgeNodeId", "knowledgeTreeKey", "knowledgePath"))
    kn_id = data.pop("knowledgeNodeId", w.knowledge_node_id) if kb_touched else None
    kn_tk = data.pop("knowledgeTreeKey", w.knowledge_tree_key) if kb_touched else None
    kn_path = data.pop("knowledgePath", w.knowledge_path) if kb_touched else None

    # 兼容旧客户端：reviewCount 增加视为一次成功复习
    bump_review = (
        "reviewCount" in data
        and data["reviewCount"] is not None
        and int(data["reviewCount"]) > int(w.review_count or 0)
    )
    if bump_review:
        data.pop("reviewCount", None)

    for k, v in data.items():
        key = {
            "questionType": "question_type",
            "myAnswer": "my_answer",
            "correctAnswer": "correct_answer",
            "wrongReason": "wrong_reason",
            "reviewCount": "review_count",
            "reviewStage": "review_stage",
            "nextReviewAt": "next_review_at",
        }.get(k, k)
        setattr(w, key, v)

    if kb_touched:
        if not kn_id and not kn_path:
            w.knowledge_node_id = None
            w.knowledge_tree_key = ""
            w.knowledge_path = ""
        else:
            nid, tk, path = resolve_knowledge_ref(
                db,
                node_id=kn_id,
                tree_key=kn_tk or "",
                path=kn_path or "",
            )
            w.knowledge_node_id = nid
            w.knowledge_tree_key = tk
            w.knowledge_path = path

    if images_val is not None:
        w.images = json.dumps(images_val, ensure_ascii=False)
    elif extra_images is not None:
        try:
            current = json.loads(w.images) if w.images else []
        except json.JSONDecodeError:
            current = []
        w.images = json.dumps(current + extra_images, ensure_ascii=False)
    if bump_review:
        db.commit()
        return review_wrong(db, user, wrong_id, "good")

    if body.mastered is True:
        w.mastered = True
        w.next_review_at = None
        w.last_wrong_at = now()
    elif body.mastered is False:
        stage, next_at = schedule_first()
        w.mastered = False
        w.review_stage = stage
        w.next_review_at = next_at
        w.last_wrong_at = now()
    db.commit()
    db.refresh(w)
    return _to_out(w)


def delete_wrong(db: Session, user: AppUser, wrong_id: str) -> bool:
    w = db.get(ManualWrong, wrong_id)
    if not w or w.user_id != user.id:
        return False
    db.delete(w)
    db.commit()
    return True
