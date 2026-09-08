"""艾宾浩斯风格固定间隔（与文章复习一致），不做完整 SM-2。"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.timezone import now

# 答对后的下一档间隔（天）：第 1～6 次成功分别推迟这些天数，之后视为掌握
SRS_INTERVALS = [1, 2, 4, 7, 15, 30]


def now_naive() -> datetime:
    return now().replace(tzinfo=None)


def is_due(next_review_at: datetime | None, *, treat_null_as_due: bool = True) -> bool:
    if next_review_at is None:
        return treat_null_as_due
    return next_review_at <= now_naive()


def schedule_first() -> tuple[int, datetime]:
    """首次进入复习队列：立即到期。"""
    return 0, now_naive()


def schedule_after_success(stage: int) -> tuple[int, datetime | None, bool]:
    """答对/复习成功：推进一档。

    Returns: (new_stage, next_review_at, mastered)
    mastered=True 时 next_review_at 为 None。
    """
    stage = max(0, int(stage or 0))
    if stage >= len(SRS_INTERVALS):
        return stage, None, True
    days = SRS_INTERVALS[stage]
    new_stage = stage + 1
    next_at = now_naive() + timedelta(days=days)
    mastered = new_stage >= len(SRS_INTERVALS)
    if mastered:
        return new_stage, None, True
    return new_stage, next_at, False


def schedule_after_fail() -> tuple[int, datetime]:
    """答错/遗忘：回到第 0 档，明天再来（避免同日刷爆）。"""
    return 0, now_naive() + timedelta(days=1)
