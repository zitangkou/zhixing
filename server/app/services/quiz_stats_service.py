"""套题答题统计与排行榜"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AppUser, QuizAttempt
from app.services.activity_service import record_event


def _accuracy(correct: int, total: int) -> int:
    if total <= 0:
        return 0
    return round(correct * 100 / total)


def submit_quiz_attempt(
    db: Session,
    user_id: str,
    *,
    article_id: str | None,
    quiz_mode: str,
    total: int,
    correct: int,
) -> dict:
    accuracy = _accuracy(correct, total)
    attempt = QuizAttempt(
        user_id=user_id,
        article_id=article_id,
        quiz_mode=quiz_mode,
        total_count=total,
        correct_count=correct,
        accuracy=accuracy,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    record_event(
        db,
        user_id,
        "quiz_done",
        {"articleId": article_id, "quizMode": quiz_mode, "total": total, "correct": correct, "accuracy": accuracy},
    )

    rank, total_participants = _calc_user_rank(db, user_id, article_id=article_id, quiz_mode=quiz_mode)
    best = _best_accuracy(db, user_id, article_id=article_id, quiz_mode=quiz_mode)
    return {
        "accuracy": accuracy,
        "rank": rank,
        "totalParticipants": total_participants,
        "bestAccuracy": best,
    }


def _best_subquery(db: Session, article_id: str | None, quiz_mode: str):
    q = db.query(
        QuizAttempt.user_id.label("user_id"),
        func.max(QuizAttempt.accuracy).label("best_accuracy"),
        func.max(QuizAttempt.correct_count).label("best_correct"),
    )
    if article_id:
        q = q.filter(QuizAttempt.article_id == article_id)
    else:
        q = q.filter(QuizAttempt.article_id.is_(None), QuizAttempt.quiz_mode == quiz_mode)
    return q.group_by(QuizAttempt.user_id).subquery()


def _calc_user_rank(
    db: Session,
    user_id: str,
    *,
    article_id: str | None,
    quiz_mode: str,
) -> tuple[int, int]:
    sub = _best_subquery(db, article_id, quiz_mode)
    rows = (
        db.query(sub.c.user_id, sub.c.best_accuracy, sub.c.best_correct)
        .order_by(sub.c.best_accuracy.desc(), sub.c.best_correct.desc())
        .all()
    )
    total = len(rows)
    rank = total
    for i, (uid, acc, _correct) in enumerate(rows):
        if uid == user_id:
            rank = i + 1
            break
    return rank, total


def _best_accuracy(
    db: Session,
    user_id: str,
    *,
    article_id: str | None,
    quiz_mode: str,
) -> int | None:
    q = db.query(func.max(QuizAttempt.accuracy)).filter(QuizAttempt.user_id == user_id)
    if article_id:
        q = q.filter(QuizAttempt.article_id == article_id)
    else:
        q = q.filter(QuizAttempt.article_id.is_(None), QuizAttempt.quiz_mode == quiz_mode)
    val = q.scalar()
    return int(val) if val is not None else None


def get_quiz_rank(
    db: Session,
    *,
    article_id: str | None,
    quiz_mode: str = "article",
    limit: int = 20,
) -> list[dict]:
    sub = _best_subquery(db, article_id, quiz_mode)
    rows = (
        db.query(sub, AppUser)
        .join(AppUser, AppUser.id == sub.c.user_id)
        .filter(AppUser.is_active.is_(True))
        .order_by(sub.c.best_accuracy.desc(), sub.c.best_correct.desc())
        .limit(limit)
        .all()
    )
    items = []
    for i, (best, user) in enumerate(rows):
        total_q = (
            db.query(QuizAttempt)
            .filter(
                QuizAttempt.user_id == user.id,
                QuizAttempt.accuracy == best.best_accuracy,
            )
        )
        if article_id:
            total_q = total_q.filter(QuizAttempt.article_id == article_id)
        else:
            total_q = total_q.filter(QuizAttempt.article_id.is_(None), QuizAttempt.quiz_mode == quiz_mode)
        attempt = total_q.order_by(QuizAttempt.correct_count.desc()).first()
        items.append(
            {
                "rank": i + 1,
                "userId": user.id,
                "nickname": user.nickname,
                "avatar": user.avatar,
                "accuracy": int(best.best_accuracy),
                "correctCount": attempt.correct_count if attempt else 0,
                "totalCount": attempt.total_count if attempt else 0,
                "isSelf": False,
            }
        )
    return items


def get_user_quiz_stats(
    db: Session,
    user_id: str,
    *,
    article_id: str | None,
    quiz_mode: str = "article",
) -> dict | None:
    q = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id)
    if article_id:
        q = q.filter(QuizAttempt.article_id == article_id)
    else:
        q = q.filter(QuizAttempt.article_id.is_(None), QuizAttempt.quiz_mode == quiz_mode)
    attempts = q.order_by(QuizAttempt.created_at.desc()).all()
    if not attempts:
        return None
    best = max(attempts, key=lambda a: (a.accuracy, a.correct_count))
    rank, total_participants = _calc_user_rank(db, user_id, article_id=article_id, quiz_mode=quiz_mode)
    return {
        "attemptCount": len(attempts),
        "bestAccuracy": best.accuracy,
        "bestCorrect": best.correct_count,
        "bestTotal": best.total_count,
        "lastAccuracy": attempts[0].accuracy,
        "rank": rank,
        "totalParticipants": total_participants,
    }
