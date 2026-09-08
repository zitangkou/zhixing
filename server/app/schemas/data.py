"""Pydantic schema · 数据导出/导入"""
from typing import Any

from pydantic import BaseModel


class DataImportIn(BaseModel):
    """导入体：与导出体同构，便于把导出的 JSON 文本直接粘贴回导。"""

    version: int = 1
    exportedAt: str | None = None
    wrongAnswers: list[dict[str, Any]] = []
    manualWrongs: list[dict[str, Any]] = []
    corpusItems: list[dict[str, Any]] = []
    planTasks: list[dict[str, Any]] = []
    dailyReviews: list[dict[str, Any]] = []
    pointsLogs: list[dict[str, Any]] = []
