"""多产品今日任务 schema。"""

from typing import Any, Literal

from pydantic import BaseModel, Field


TaskState = Literal["not_started", "in_progress", "submitted", "reviewed", "completed"]
TaskEvent = Literal["start", "save", "submit", "review", "complete"]


class DailyTaskProgressOut(BaseModel):
    state: TaskState
    currentStep: int
    totalSteps: int
    draft: dict[str, Any]
    startedAt: str | None = None
    submittedAt: str | None = None
    reviewedAt: str | None = None
    completedAt: str | None = None
    updatedAt: str | None = None


class DailyLearningTaskOut(BaseModel):
    id: str
    productKey: str
    taskDate: str
    taskType: str
    title: str
    description: str
    contentType: str
    contentId: str
    estimatedMinutes: int
    totalSteps: int
    sortOrder: int
    metadata: dict[str, Any]
    progress: DailyTaskProgressOut


class DailyTaskListOut(BaseModel):
    date: str
    productKey: str
    completion: int
    completedCount: int
    totalCount: int
    estimatedMinutes: int
    tasks: list[DailyLearningTaskOut]


class DailyTaskProgressBody(BaseModel):
    event: TaskEvent
    currentStep: int | None = Field(default=None, ge=0)
    totalSteps: int | None = Field(default=None, ge=1)
    draft: dict[str, Any] | None = None


class TopicItem(BaseModel):
    no: str = Field(default="", max_length=2)
    title: str = Field(min_length=1, max_length=64)
    desc: str = Field(default="", max_length=128)


class TopicListOut(BaseModel):
    productKey: str
    items: list[TopicItem]
