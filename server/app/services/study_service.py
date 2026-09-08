"""学习记录、小节已读、复习任务"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Article, SectionRead, StudyRecord, utcnow
from app.services.activity_service import record_event
from app.timezone import today as today_str

REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30]


def _today() -> str:
    return today_str()


def upsert_study_record(db: Session, user_id: str, article_id: str, study_date: str | None = None) -> tuple[StudyRecord, bool]:
    today = study_date or _today()
    row = (
        db.query(StudyRecord)
        .filter(StudyRecord.user_id == user_id, StudyRecord.article_id == article_id)
        .first()
    )
    if row:
        row.updated_at = utcnow()
        db.commit()
        db.refresh(row)
        return row, False
    row = StudyRecord(user_id=user_id, article_id=article_id, study_date=today)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, True


def touch_study_activity(db: Session, user_id: str, article_id: str) -> StudyRecord:
    """标记文章有学习活动（打开/读段落），用于「最近在学」排序。"""
    row, _ = upsert_study_record(db, user_id, article_id)
    return row


def list_study_records(db: Session, user_id: str) -> list[dict]:
    rows = (
        db.query(StudyRecord)
        .filter(StudyRecord.user_id == user_id)
        .order_by(StudyRecord.updated_at.desc(), StudyRecord.id.desc())
        .all()
    )
    return [
        {
            "articleId": r.article_id,
            "studyDate": r.study_date,
            "reviewCount": r.review_count,
            "lastReviewDate": r.last_review_date,
            "mastered": r.mastered,
            "updatedAt": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]

def mark_section_read(db: Session, user_id: str, article_id: str, section_id: str) -> None:
    exists = (
        db.query(SectionRead)
        .filter(
            SectionRead.user_id == user_id,
            SectionRead.article_id == article_id,
            SectionRead.section_id == section_id,
        )
        .first()
    )
    if not exists:
        db.add(SectionRead(user_id=user_id, article_id=article_id, section_id=section_id))
        db.commit()
    # 无论是否新读段落，都刷新「最近在学」
    touch_study_activity(db, user_id, article_id)
    record_event(db, user_id, "article_read", {"articleId": article_id, "sectionId": section_id})

def get_section_read_map(db: Session, user_id: str) -> dict[str, list[str]]:
    rows = db.query(SectionRead).filter(SectionRead.user_id == user_id).all()
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row.article_id, []).append(row.section_id)
    return result


def complete_review(db: Session, user_id: str, article_id: str) -> StudyRecord | None:
    row = (
        db.query(StudyRecord)
        .filter(StudyRecord.user_id == user_id, StudyRecord.article_id == article_id)
        .first()
    )
    if not row:
        return None
    row.review_count += 1
    row.last_review_date = _today()
    if row.review_count >= len(REVIEW_INTERVALS):
        row.mastered = True
    db.commit()
    db.refresh(row)
    return row


def _add_days(date_str: str, days: int) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return (d + timedelta(days=days)).strftime("%Y-%m-%d")


def _days_between(from_str: str, to_str: str) -> int:
    a = datetime.strptime(from_str, "%Y-%m-%d").date()
    b = datetime.strptime(to_str, "%Y-%m-%d").date()
    return (b - a).days


def generate_review_tasks(db: Session, user_id: str, today: str | None = None) -> list[dict]:
    today = today or _today()
    records = db.query(StudyRecord).filter(StudyRecord.user_id == user_id, StudyRecord.mastered.is_(False)).all()
    if not records:
        return []

    article_ids = [r.article_id for r in records]
    articles = {a.id: a for a in db.query(Article).filter(Article.id.in_(article_ids)).all()}
    tasks: list[dict] = []

    for record in records:
        article = articles.get(record.article_id)
        if not article:
            continue
        if record.review_count >= len(REVIEW_INTERVALS):
            continue
        interval = REVIEW_INTERVALS[record.review_count]
        next_date = _add_days(record.study_date, interval)
        if next_date <= today:
            overdue = _days_between(next_date, today)
            tags = []
            try:
                import json

                tags = json.loads(article.tags or "[]")
            except json.JSONDecodeError:
                pass
            tasks.append(
                {
                    "id": f"review-{record.article_id}-{record.review_count}",
                    "articleId": record.article_id,
                    "articleTitle": article.title,
                    "reviewIndex": record.review_count,
                    "dueDate": next_date,
                    "urgency": overdue + interval,
                    "type": "article",
                }
            )

    tasks.sort(key=lambda t: t["urgency"], reverse=True)
    return tasks
