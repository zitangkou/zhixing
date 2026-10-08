"""用户私有知识库文档。原文件保存在非公开 uploads 目录之外。"""
from datetime import datetime

from app.models.base import (
    Base,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Mapped,
    gen_id,
    mapped_column,
    utcnow,
)


class LibraryDocument(Base):
    __tablename__ = "library_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ld"))
    owner_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("app_users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    uploaded_by_admin_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    file_name: Mapped[str] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(256), default="")
    category: Mapped[str] = mapped_column(String(64), default="未分类", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    file_format: Mapped[str] = mapped_column(String(16), index=True)
    content_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    file_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_path: Mapped[str] = mapped_column(String(1024))
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    extraction_status: Mapped[str] = mapped_column(String(24), default="ready", index=True)
    extraction_error: Mapped[str] = mapped_column(Text, default="")
    is_published: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
