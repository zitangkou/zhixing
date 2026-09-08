"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class GrowthDayBar(BaseModel):
    date: str
    label: str
    minutes: int
    isToday: bool = False


class GrowthDomainProgress(BaseModel):
    key: str
    name: str
    percent: int
    detail: str = ""


class GrowthOverviewOut(BaseModel):
    signStreak: int
    signDays: int
    points: int
    weekMinutes: int
    weekQuizTotal: int
    weekQuizCorrect: int
    articleReadCount: int
    examFinishedCount: int
    weekBars: list[GrowthDayBar]
    domains: list[GrowthDomainProgress]

