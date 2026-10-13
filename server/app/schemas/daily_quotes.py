"""每日金句管理请求。"""
from datetime import date
from pydantic import BaseModel, Field


class QuoteImportRequest(BaseModel):
    collected_date: date
    items: list[dict] = Field(min_length=1, max_length=500)


class QuoteSaveRequest(BaseModel):
    collected_date: date
    item: dict


class QuoteRunRequest(BaseModel):
    issue_date: date


class QuoteSelectionRequest(BaseModel):
    issue_date: date
    quote_ids: list[str] = Field(max_length=100)
