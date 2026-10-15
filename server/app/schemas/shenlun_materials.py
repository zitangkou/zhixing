from datetime import date
from pydantic import BaseModel, Field

class ShenlunMaterialImport(BaseModel):
    collected_date: date
    items: list[dict] = Field(min_length=1, max_length=300)

class ShenlunMaterialSave(BaseModel):
    collected_date: date
    item: dict
