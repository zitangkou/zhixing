"""学习数据导出/导入 service（核心进度：错题本/语料本/计划复习/积分）。

导出范围由用户确认：仅「核心进度」4 类，共 6 张用户表。导出为纯 JSON，
导入为整表替换（先清空该用户该表旧数据，再逐行插入），事务内完成、失败回滚。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.orm import Session

from app.models import CorpusItem, DailyReview, ManualWrong, PlanTask, PointsLog, WrongAnswer
from app.timezone import now

EXPORT_VERSION = 1

# key -> (Model, 导出字段列表)。
# 约定：排除 user_id 与 relationship(user)；int 自增主键（WrongAnswer）不导出 id，
# 字符串主键（gen_id 前缀）保留 id，保证跨端一致 + 引用不漂移。
CORE_TABLES: list[tuple[str, type, list[str]]] = [
    ("wrongAnswers", WrongAnswer, [
        "question_id", "wrong_count", "last_wrong_at", "user_answer",
        "review_stage", "next_review_at",
    ]),
    ("manualWrongs", ManualWrong, [
        "id", "subject", "question_type", "stem", "options", "my_answer",
        "correct_answer", "analysis", "wrong_reason", "note", "images", "source",
        "knowledge_node_id", "knowledge_tree_key", "knowledge_path",
        "review_count", "review_stage", "next_review_at", "mastered",
        "last_wrong_at", "created_at", "updated_at",
    ]),
    ("corpusItems", CorpusItem, [
        "id", "original", "kind", "source_type", "source_title", "tags_json",
        "plain_note", "rewrite", "practice", "status", "used_count",
        "promoted_term_id", "knowledge_node_id", "knowledge_tree_key",
        "knowledge_path", "created_at", "updated_at",
    ]),
    ("planTasks", PlanTask, [
        "id", "plan_date", "time_slot", "subject", "content", "priority",
        "expected_minutes", "actual_minutes", "status", "sort_order", "note",
        "created_at", "updated_at",
    ]),
    ("dailyReviews", DailyReview, [
        "id", "review_date", "completion", "total_minutes", "weak_point",
        "tomorrow_focus", "mood", "note", "created_at", "updated_at",
    ]),
    ("pointsLogs", PointsLog, [
        "id", "amount", "log_type", "source", "description", "created_at",
    ]),
]


def _jsonable(value: Any) -> Any:
    """datetime -> 无时区 ISO 字符串（与 SQLite 存 naive 北京时间的习惯一致）。"""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.replace(tzinfo=None)
        return value.isoformat()
    return value


def _parse_dt(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def _coerce_value(model: type, field: str, value: Any) -> Any:
    """按模型列类型还原 JSON 值（重点把 ISO 字符串还原为 datetime）。"""
    if value is None:
        return None
    col = model.__table__.columns.get(field)
    if col is not None and isinstance(col.type, DateTime) and isinstance(value, str):
        return _parse_dt(value)
    return value


def export_core_data(db: Session, user_id: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": EXPORT_VERSION,
        "exportedAt": now().replace(tzinfo=None).isoformat(),
    }
    for key, model, fields in CORE_TABLES:
        rows = db.query(model).filter(model.user_id == user_id).all()
        payload[key] = [
            {f: _jsonable(getattr(r, f)) for f in fields}
            for r in rows
        ]
    return payload


def import_core_data(db: Session, user_id: str, body: dict[str, Any]) -> dict[str, int]:
    """整表替换导入；返回各表导入行数。校验失败抛 ValueError，事务回滚。"""
    counts: dict[str, int] = {}
    try:
        for key, model, fields in CORE_TABLES:
            items = body.get(key) or []
            if not isinstance(items, list):
                raise ValueError(f"{key} 必须是数组")
            db.query(model).filter(model.user_id == user_id).delete(
                synchronize_session=False
            )
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError(f"{key} 内含非对象条目")
                kwargs: dict[str, Any] = {}
                for f in fields:
                    if f in item:
                        kwargs[f] = _coerce_value(model, f, item[f])
                if "id" in fields and not kwargs.get("id"):
                    kwargs.pop("id", None)  # 让 model default gen_id 兜底
                db.add(model(user_id=user_id, **kwargs))
            counts[key] = len(items)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return counts
