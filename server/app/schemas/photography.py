from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse
import re


class PhotographyStageInput(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    items: str = Field(default="", max_length=512)
    description: str = Field(default="", max_length=512)
    sort_order: int = Field(default=0, ge=0)
    is_published: bool = True


class PhotographyLessonInput(BaseModel):
    stage_id: str
    category: str = Field(default="光线", min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=160)
    subtitle: str = Field(default="", max_length=256)
    level: str = Field(default="入门", max_length=32)
    duration_min: int = Field(default=10, ge=1, le=240)
    principle: str = ""
    steps: list[str] = Field(default_factory=list)
    task: str = ""
    review: str = ""
    sort_order: int = Field(default=0, ge=0)
    is_published: bool = False


class PhotographyCaseInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    image_url: str = Field(min_length=1, max_length=1024)
    source_url: str = Field(default="", max_length=1024)
    author: str = Field(default="", max_length=160)
    license_type: str = Field(default="", max_length=32)
    license_note: str = Field(default="", max_length=512)
    category: str = Field(default="光线", min_length=1, max_length=64)
    level: str = Field(default="入门", max_length=32)
    observations: list[str] = Field(default_factory=list, max_length=12)
    exif: dict[str, str | int | float | None] = Field(default_factory=dict)
    inferences: list[dict[str, str]] = Field(default_factory=list, max_length=8)
    practice_title: str = Field(default="", max_length=160)
    practice_goal: str = ""
    practice_steps: list[str] = Field(default_factory=list, max_length=8)
    practice_variable: str = Field(default="", max_length=256)
    criteria: list[str] = Field(default_factory=list, max_length=8)
    duration_min: int = Field(default=15, ge=1, le=240)
    sort_order: int = Field(default=0, ge=0)
    is_published: bool = False

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if value and not ((parsed.scheme == "https" and parsed.netloc) or re.fullmatch(r"/uploads/photography-cases/[a-f0-9]{32}\.(png|jpg)", value)):
            raise ValueError("案例图片须使用 HTTPS 地址或后台上传的摄影案例图片")
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if value and (parsed.scheme != "https" or not parsed.netloc):
            raise ValueError("作品来源地址必须使用 HTTPS")
        return value

    @field_validator("title", "author", "license_type", "license_note", "category", "practice_title", "practice_goal", "practice_variable", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("observations", "practice_steps", "criteria")
    @classmethod
    def trim_list_items(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]

    @field_validator("inferences")
    @classmethod
    def validate_inference_evidence(cls, values: list[dict[str, str]]) -> list[dict[str, str]]:
        for item in values:
            if not item.get("statement", "").strip() or not item.get("evidence", "").strip():
                raise ValueError("每条摄影推断都需要填写画面证据")
            if item.get("confidence", "") not in {"高", "中", "低"}:
                raise ValueError("摄影推断置信度须为高、中或低")
        return values
