from pydantic import BaseModel, Field


class EnglishSceneInput(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = ""
    level: str = "A1 入门"
    sort_order: int = 0
    is_published: bool = False


class EnglishUnitInput(BaseModel):
    scene_id: str
    title: str = Field(min_length=1, max_length=128)
    level: str = "A1 入门"
    duration_min: int = Field(default=8, ge=1, le=180)
    goal: str = ""
    content: dict = Field(default_factory=dict)
    sort_order: int = 0
    is_published: bool = False
