"""只记录大模型调用元数据和用量，不保存提示词、原文或模型输出。"""
from datetime import datetime
from app.models.base import Base, Mapped, mapped_column, String, Integer, DateTime, Text, utcnow, gen_id

class LlmUsageLog(Base):
    __tablename__ = 'llm_usage_logs'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id('llu'))
    purpose: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(24), default='success', index=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str] = mapped_column(String(64), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
