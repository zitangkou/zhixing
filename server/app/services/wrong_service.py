"""错题本（艾宾浩斯间隔调度）"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Article, Question, WrongAnswer
from app.services.serializers import parse_correct_answer, parse_json, question_to_out
from app.services.srs import (
    is_due,
    now_naive,
    schedule_after_fail,
    schedule_after_success,
    schedule_first,
)
from app.timezone import now


def _row_to_dict(db: Session, row: WrongAnswer) -> dict | None:
    question = db.get(Question, row.question_id)
    if not question:
        return None
    article = db.get(Article, question.article_id)
    tags = parse_json(article.tags, []) if article else []
    user_answer: str | list[str] | None = None
    if row.user_answer:
        parsed = parse_correct_answer(row.user_answer)
        user_answer = parsed if parsed else None
    due = is_due(row.next_review_at)
    return {
        "question": question_to_out(question).model_dump(),
        "wrongCount": row.wrong_count,
        "lastWrongAt": row.last_wrong_at.isoformat() if row.last_wrong_at else "",
        "userAnswer": user_answer,
        "articleTitle": article.title if article else "未知文章",
        "tag": tags[0] if tags else "综合",
        "reviewStage": int(row.review_stage or 0),
        "nextReviewAt": row.next_review_at.isoformat() if row.next_review_at else None,
        "due": due,
    }


def list_wrong_questions(
    db: Session,
    user_id: str,
    status: str | None = "review",
) -> list[dict]:
    """status: review=今日到期（默认）| waiting=未到期 | all=全部"""
    rows = (
        db.query(WrongAnswer)
        .filter(WrongAnswer.user_id == user_id)
        .order_by(WrongAnswer.last_wrong_at.desc())
        .all()
    )
    result: list[dict] = []
    for row in rows:
        item = _row_to_dict(db, row)
        if not item:
            continue
        due = item["due"]
        if status == "review" and not due:
            continue
        if status == "waiting" and due:
            continue
        result.append(item)
    # 待复习按到期优先；全部时到期靠前
    if status == "all":
        result.sort(key=lambda x: (0 if x["due"] else 1, x.get("nextReviewAt") or ""))
    return result


def count_due_wrongs(db: Session, user_id: str) -> int:
    now_ts = now_naive()
    return (
        db.query(WrongAnswer)
        .filter(
            WrongAnswer.user_id == user_id,
            (WrongAnswer.next_review_at.is_(None)) | (WrongAnswer.next_review_at <= now_ts),
        )
        .count()
    )


def count_waiting_wrongs(db: Session, user_id: str) -> int:
    """未到期：今日可跳过。"""
    now_ts = now_naive()
    return (
        db.query(WrongAnswer)
        .filter(
            WrongAnswer.user_id == user_id,
            WrongAnswer.next_review_at.isnot(None),
            WrongAnswer.next_review_at > now_ts,
        )
        .count()
    )


# 每日推荐上限，避免一次刷爆；低档位 / 错次多优先
DAILY_WRONG_CAP = 15


def recommend_wrong_questions(db: Session, user_id: str, limit: int = DAILY_WRONG_CAP) -> list[dict]:
    items = list_wrong_questions(db, user_id, status="review")
    items.sort(
        key=lambda x: (
            int(x.get("reviewStage") or 0),
            -int(x.get("wrongCount") or 0),
        )
    )
    return items[: max(1, min(limit, DAILY_WRONG_CAP))]


def remove_wrong(db: Session, user_id: str, question_id: str) -> bool:
    row = (
        db.query(WrongAnswer)
        .filter(WrongAnswer.user_id == user_id, WrongAnswer.question_id == question_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def apply_wrong_redo_result(
    db: Session,
    user_id: str,
    question_id: str,
    correct: bool,
) -> str:
    """处理错题重做结果。返回: removed | scheduled | reset | missing"""
    row = (
        db.query(WrongAnswer)
        .filter(WrongAnswer.user_id == user_id, WrongAnswer.question_id == question_id)
        .first()
    )
    if not row:
        return "missing"
    if correct:
        new_stage, next_at, mastered = schedule_after_success(int(row.review_stage or 0))
        if mastered:
            db.delete(row)
            db.commit()
            return "removed"
        row.review_stage = new_stage
        row.next_review_at = next_at
        db.commit()
        return "scheduled"
    # 答错：重置曲线，明天再来
    stage, next_at = schedule_after_fail()
    row.review_stage = stage
    row.next_review_at = next_at
    row.wrong_count = int(row.wrong_count or 0) + 1
    row.last_wrong_at = now()
    db.commit()
    return "reset"


def ensure_wrong_scheduled(row: WrongAnswer) -> None:
    """新建或再次做错时，确保进入今日到期队列。"""
    stage, next_at = schedule_first()
    row.review_stage = stage
    row.next_review_at = next_at
