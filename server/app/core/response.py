from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    data: T | None = None
    message: str = "success"

    @classmethod
    def ok(cls, data: T, message: str = "success") -> "ApiResponse[T]":
        return cls(code=0, data=data, message=message)

    @classmethod
    def fail(cls, message: str, code: int = 400, data: T | None = None) -> "ApiResponse[T]":
        return cls(code=code, data=data, message=message)
