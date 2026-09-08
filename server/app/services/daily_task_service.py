"""跨产品今日任务状态机与断点恢复。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AppUser, DailyLearningTask, UserDailyTaskProgress, gen_id
from app.product import ProductContext
from app.schemas import DailyLearningTaskOut, DailyTaskListOut, DailyTaskProgressBody, DailyTaskProgressOut
from app.services.activity_service import record_event
from app.timezone import now, today as today_str

VALID_STATES = ("not_started", "in_progress", "submitted", "reviewed", "completed")
EVENT_TARGET = {
    "start": "in_progress",
    "save": "in_progress",
    "submit": "submitted",
    "review": "reviewed",
    "complete": "completed",
}
ALLOWED_EVENTS = {
    "not_started": {"start", "save"},
    "in_progress": {"start", "save", "submit"},
    "submitted": {"submit", "review"},
    "reviewed": {"review", "complete"},
    "completed": {"complete"},
}


def _loads(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw or "")
    except (json.JSONDecodeError, TypeError):
        return fallback


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _empty_progress(task: DailyLearningTask) -> DailyTaskProgressOut:
    return DailyTaskProgressOut(
        state="not_started",
        currentStep=0,
        totalSteps=max(task.total_steps, 1),
        draft={},
    )


def _progress_out(row: UserDailyTaskProgress | None, task: DailyLearningTask) -> DailyTaskProgressOut:
    if not row:
        return _empty_progress(task)
    state = row.state if row.state in VALID_STATES else "not_started"
    return DailyTaskProgressOut(
        state=state,
        currentStep=row.current_step,
        totalSteps=max(row.total_steps, 1),
        draft=_loads(row.draft_json, {}),
        startedAt=_iso(row.started_at),
        submittedAt=_iso(row.submitted_at),
        reviewedAt=_iso(row.reviewed_at),
        completedAt=_iso(row.completed_at),
        updatedAt=_iso(row.updated_at),
    )


def _task_out(task: DailyLearningTask, progress: UserDailyTaskProgress | None) -> DailyLearningTaskOut:
    return DailyLearningTaskOut(
        id=task.id,
        productKey=task.product_key,
        taskDate=task.task_date,
        taskType=task.task_type,
        title=task.title,
        description=task.description,
        contentType=task.content_type,
        contentId=task.content_id,
        estimatedMinutes=task.estimated_minutes,
        totalSteps=max(task.total_steps, 1),
        sortOrder=task.sort_order,
        metadata=_loads(task.metadata_json, {}),
        progress=_progress_out(progress, task),
    )


def list_daily_tasks(
    db: Session,
    user: AppUser,
    product: ProductContext,
    task_date: str | None = None,
) -> DailyTaskListOut:
    date = task_date or today_str()
    tasks = (
        db.query(DailyLearningTask)
        .filter(
            DailyLearningTask.product_key == product.key,
            DailyLearningTask.task_date == date,
            DailyLearningTask.status == "published",
        )
        .order_by(DailyLearningTask.sort_order, DailyLearningTask.created_at)
        .all()
    )
    task_ids = [task.id for task in tasks]
    progress_by_task: dict[str, UserDailyTaskProgress] = {}
    if task_ids:
        rows = (
            db.query(UserDailyTaskProgress)
            .filter(
                UserDailyTaskProgress.user_id == user.id,
                UserDailyTaskProgress.task_id.in_(task_ids),
                UserDailyTaskProgress.product_key == product.key,
            )
            .all()
        )
        progress_by_task = {row.task_id: row for row in rows}

    items = [_task_out(task, progress_by_task.get(task.id)) for task in tasks]
    completed = sum(item.progress.state == "completed" for item in items)
    total = len(items)
    return DailyTaskListOut(
        date=date,
        productKey=product.key,
        completion=round(completed * 100 / total) if total else 0,
        completedCount=completed,
        totalCount=total,
        estimatedMinutes=sum(task.estimated_minutes for task in tasks),
        tasks=items,
    )


def update_task_progress(
    db: Session,
    user: AppUser,
    product: ProductContext,
    task_id: str,
    body: DailyTaskProgressBody,
) -> DailyLearningTaskOut:
    task = db.get(DailyLearningTask, task_id)
    if not task or task.product_key != product.key or task.status != "published":
        raise ValueError("今日任务不存在")

    row = (
        db.query(UserDailyTaskProgress)
        .filter(
            UserDailyTaskProgress.user_id == user.id,
            UserDailyTaskProgress.task_id == task.id,
        )
        .first()
    )
    if not row:
        row = UserDailyTaskProgress(
            id=gen_id("dtp"),
            user_id=user.id,
            task_id=task.id,
            product_key=product.key,
            state="not_started",
            total_steps=max(task.total_steps, 1),
        )
        db.add(row)

    current_state = row.state if row.state in VALID_STATES else "not_started"
    if body.event not in ALLOWED_EVENTS[current_state]:
        raise ValueError(f"任务状态 {current_state} 不能执行 {body.event}")

    timestamp = now()
    row.state = EVENT_TARGET[body.event]
    if body.totalSteps is not None:
        row.total_steps = body.totalSteps
    else:
        row.total_steps = max(row.total_steps, task.total_steps, 1)
    if body.currentStep is not None:
        row.current_step = min(body.currentStep, row.total_steps)
    if body.draft is not None:
        row.draft_json = json.dumps(body.draft, ensure_ascii=False)

    if row.state == "in_progress" and row.started_at is None:
        row.started_at = timestamp
    elif row.state == "submitted" and row.submitted_at is None:
        row.submitted_at = timestamp
    elif row.state == "reviewed" and row.reviewed_at is None:
        row.reviewed_at = timestamp
    elif row.state == "completed" and row.completed_at is None:
        row.current_step = row.total_steps
        row.completed_at = timestamp
        record_event(
            db,
            user.id,
            "daily_task_completed",
            {"productKey": product.key, "taskId": task.id, "taskType": task.task_type},
            commit=False,
        )

    db.commit()
    db.refresh(row)
    return _task_out(task, row)
