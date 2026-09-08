"""考试倒计时 · 每个用户一条目标考试记录（upsert 语义）。"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import AppUser, ExamCountdown, gen_id
from app.schemas import ExamCountdownOut, ExamCountdownUpsert


def _to_out(m: ExamCountdown | None) -> ExamCountdownOut | None:
    if m is None:
        return None
    days_left = 0
    if m.exam_date:
        try:
            days_left = (date.fromisoformat(m.exam_date) - date.today()).days
        except ValueError:
            days_left = 0
    return ExamCountdownOut(
        id=m.id,
        examName=m.exam_name or "",
        examDate=m.exam_date or "",
        note=m.note or "",
        daysLeft=days_left,
        createdAt=m.created_at,
        updatedAt=m.updated_at,
    )


def get_countdown(db: Session, user: AppUser) -> ExamCountdownOut | None:
    m = (
        db.query(ExamCountdown)
        .filter(ExamCountdown.user_id == user.id)
        .order_by(ExamCountdown.updated_at.desc())
        .first()
    )
    return _to_out(m)


def upsert_countdown(
    db: Session, user: AppUser, body: ExamCountdownUpsert
) -> ExamCountdownOut:
    name = (body.examName or "").strip()
    exam_date = (body.examDate or "").strip()
    if not name:
        raise ValueError("请填写考试名称")
    if not exam_date:
        raise ValueError("请选择考试日期")
    try:
        date.fromisoformat(exam_date)
    except ValueError:
        raise ValueError("考试日期格式不正确")

    m = (
        db.query(ExamCountdown)
        .filter(ExamCountdown.user_id == user.id)
        .order_by(ExamCountdown.updated_at.desc())
        .first()
    )
    if m is None:
        m = ExamCountdown(id=gen_id("ecd"), user_id=user.id)
        db.add(m)
    m.exam_name = name
    m.exam_date = exam_date
    m.note = (body.note or "").strip()
    db.commit()
    db.refresh(m)
    return _to_out(m)  # type: ignore[return-value]


def delete_countdown(db: Session, user: AppUser) -> bool:
    m = (
        db.query(ExamCountdown)
        .filter(ExamCountdown.user_id == user.id)
        .order_by(ExamCountdown.updated_at.desc())
        .first()
    )
    if not m:
        return False
    db.delete(m)
    db.commit()
    return True
