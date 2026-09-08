from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import AppUser, PointsLog, Question, SignRecord, WrongAnswer, gen_id
from app.schemas import UserMeOut
from app.services.serializers import parse_correct_answer
from app.timezone import now, today as today_str


def build_user_me_out(db: Session, user: AppUser) -> UserMeOut:
    today = today_str()
    signed_today = (
        db.query(SignRecord)
        .filter(SignRecord.user_id == user.id, SignRecord.sign_date == today)
        .first()
        is not None
    )
    sign_dates = [r.sign_date for r in user.sign_records]
    return UserMeOut(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar or "",
        email=user.email or "",
        phone=user.phone or "",
        isMember=user.is_member,
        points=user.points,
        hasSignedToday=signed_today,
        signDates=sign_dates,
    )


def get_or_create_demo_user(db: Session, user_id: str | None = None) -> AppUser:
    uid = user_id or "u-demo-001"
    user = db.get(AppUser, uid)
    if not user:
        user = AppUser(id=uid, nickname="知行学员", points=120)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def add_points_log(db: Session, user: AppUser, amount: int, source: str, description: str, log_type: str = "income"):
    if log_type == "income":
        user.points += amount
    else:
        user.points -= amount
    log = PointsLog(
        id=gen_id("log"),
        user_id=user.id,
        amount=amount,
        log_type=log_type,
        source=source,
        description=description,
    )
    db.add(log)
    db.commit()
    return log


def check_answer(question: Question, answer: str | list) -> bool:
    from app.services.serializers import parse_correct_answer

    correct = parse_correct_answer(question.correct_answer or "")
    if isinstance(correct, list):
        if not isinstance(answer, list):
            return False
        return sorted(correct) == sorted(answer)
    return str(answer) == str(correct)


def record_wrong(
    db: Session,
    user_id: str,
    question_id: str,
    user_answer: str | list | None = None,
):
    from app.services.serializers import encode_correct_answer
    from app.services.wrong_service import ensure_wrong_scheduled

    encoded = encode_correct_answer(user_answer) if user_answer is not None else ""
    row = (
        db.query(WrongAnswer)
        .filter(WrongAnswer.user_id == user_id, WrongAnswer.question_id == question_id)
        .first()
    )
    if row:
        row.wrong_count += 1
        row.last_wrong_at = now()
        if encoded:
            row.user_answer = encoded
        ensure_wrong_scheduled(row)
    else:
        row = WrongAnswer(
            user_id=user_id,
            question_id=question_id,
            user_answer=encoded,
        )
        ensure_wrong_scheduled(row)
        db.add(row)
    db.commit()


def calc_sign_streak(db: Session, user_id: str, today: str) -> int:
    from datetime import timedelta

    streak = 0
    current = datetime.strptime(today, "%Y-%m-%d").date()
    while True:
        d = current.strftime("%Y-%m-%d")
        exists = (
            db.query(SignRecord)
            .filter(SignRecord.user_id == user_id, SignRecord.sign_date == d)
            .first()
        )
        if not exists:
            break
        streak += 1
        current -= timedelta(days=1)
    return streak
