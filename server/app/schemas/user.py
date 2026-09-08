"""Pydantic schema · 域模块

按业务域拆分，统一由 app/schemas/__init__.py re-export，保持 from app.schemas import X 兼容。
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
class UserMeOut(BaseModel):
    id: str
    username: str | None = None
    nickname: str
    avatar: str
    email: str = ""
    phone: str = ""
    isMember: bool
    points: int
    hasSignedToday: bool
    signDates: list[str]


class AppUserProfileUpdate(BaseModel):
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None


class AppUserPasswordChange(BaseModel):
    oldPassword: str
    newPassword: str
    newPasswordConfirm: str


class AppRegisterBody(BaseModel):
    username: str
    password: str
    passwordConfirm: str


class AppLoginBody(BaseModel):
    username: str
    password: str


class AppAuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserMeOut


class FeedbackOut(BaseModel):
    id: str
    userId: str
    username: str = ""
    productKey: str = ""
    content: str
    status: str
    note: str = ""
    createdAt: datetime | None = None
    handledAt: datetime | None = None


class FeedbackHandleBody(BaseModel):
    action: str = Field(pattern="^(adopted|rejected)$")
    note: str = Field(default="", max_length=256)
    points: int = Field(default=0, ge=0, le=100)


