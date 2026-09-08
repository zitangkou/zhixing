"""游客练习登录合并：版本化、幂等，且不写入积分/错题/个人开采。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import UserGuestLearningRecord
from app.models.base import gen_id
from app.timezone import now

ALLOWED_TYPES = {
    "theory": {"theory_article_quiz"},
    "shenlun": {"shenlun_short_practice"},
}
MAX_PAYLOAD_BYTES = 50_000


def _naive(value: datetime) -> datetime:
    return value.replace(tzinfo=None) if value.tzinfo else value


def _record_out(row: UserGuestLearningRecord) -> dict:
    try:
        payload = json.loads(row.payload_json)
    except (TypeError, json.JSONDecodeError):
        payload = {}
    return {
        "recordType": row.record_type,
        "contentId": row.content_id,
        "revision": row.revision,
        "payload": payload if isinstance(payload, dict) else {},
        "updatedAt": row.client_updated_at.isoformat(),
    }


def list_records(db: Session, user_id: str, product_key: str) -> list[dict]:
    rows = db.query(UserGuestLearningRecord).filter(
        UserGuestLearningRecord.user_id == user_id,
        UserGuestLearningRecord.product_key == product_key,
    ).order_by(UserGuestLearningRecord.client_updated_at.desc()).all()
    return [_record_out(row) for row in rows]


def merge_records(
    db: Session,
    user_id: str,
    product_key: str,
    device_id: str,
    records: list,
) -> dict:
    allowed = ALLOWED_TYPES.get(product_key, set())
    accepted = 0
    unchanged = 0
    for item in records:
        record_type = item.recordType
        if record_type not in allowed:
            raise HTTPException(422, "记录类型与当前产品不匹配")
        payload_json = json.dumps(item.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(payload_json.encode()) > MAX_PAYLOAD_BYTES:
            raise HTTPException(422, "单条游客记录过大")
        record_key = f"{record_type}:{item.contentId}:{item.revision}"
        client_updated_at = _naive(item.updatedAt)
        if client_updated_at > _naive(now()) + timedelta(days=1):
            raise HTTPException(422, "游客记录时间异常")
        row = db.query(UserGuestLearningRecord).filter(
            UserGuestLearningRecord.user_id == user_id,
            UserGuestLearningRecord.product_key == product_key,
            UserGuestLearningRecord.record_key == record_key,
        ).first()
        if row and _naive(row.client_updated_at) >= client_updated_at:
            unchanged += 1
            continue
        if not row:
            row = UserGuestLearningRecord(
                id=gen_id("glr"), user_id=user_id, product_key=product_key,
                record_key=record_key, record_type=record_type,
                content_id=item.contentId, revision=item.revision,
                client_updated_at=client_updated_at,
            )
            db.add(row)
        row.payload_json = payload_json
        row.source_device_id = device_id
        row.client_updated_at = client_updated_at
        accepted += 1
    db.commit()
    return {
        "accepted": accepted,
        "unchanged": unchanged,
        "records": list_records(db, user_id, product_key),
    }
