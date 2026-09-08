"""全局复习调度：用每日预算限制暴露给用户的复习量。"""
from __future__ import annotations

from math import ceil
from typing import TypedDict


DAILY_REVIEW_BUDGET = 30

MODULE_CAPS = {
    "knowledge": 8,
    "article": 4,
    "wrong": 10,
    "corpus": 3,
}

MODULE_LABELS = {
    "knowledge": "知识抽查",
    "article": "文章复习",
    "wrong": "错题复习",
    "corpus": "语料内化",
}


class ReviewModuleInput(TypedDict):
    key: str
    due: int
    cap: int
    priority: int


def build_review_plan(modules: list[ReviewModuleInput], *, budget: int = DAILY_REVIEW_BUDGET) -> dict:
    """Return capped recommendations and backlog without changing item schedules."""
    budget = max(1, int(budget or DAILY_REVIEW_BUDGET))
    remaining = budget
    plan: list[dict] = []

    for m in sorted(modules, key=lambda x: x["priority"], reverse=True):
        due = max(0, int(m["due"] or 0))
        cap = max(0, int(m["cap"] or 0))
        recommended = min(due, cap, remaining)
        remaining -= recommended
        plan.append(
            {
                "key": m["key"],
                "label": MODULE_LABELS.get(m["key"], m["key"]),
                "due": due,
                "recommended": recommended,
                "backlog": max(0, due - recommended),
                "cap": cap,
            }
        )

    today_recommended = sum(int(x["recommended"]) for x in plan)
    backlog = sum(int(x["backlog"]) for x in plan)
    return {
        "todayBudget": budget,
        "todayRecommended": today_recommended,
        "backlogCount": backlog,
        "estimatedClearDays": ceil(backlog / budget) if backlog else 0,
        "reviewPlan": plan,
    }
