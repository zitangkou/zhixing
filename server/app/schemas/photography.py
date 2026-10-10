from pydantic import BaseModel, Field


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
