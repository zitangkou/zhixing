"""微信公众号回复配置草稿与不可变发布版本。"""

from datetime import datetime

from app.models.base import (
    Base,
    DateTime,
    ForeignKey,
    Integer,
    Mapped,
    String,
    Text,
    UniqueConstraint,
    mapped_column,
    utcnow,
)


class WechatReplyRelease(Base):
    __tablename__ = "wechat_reply_releases"
    __table_args__ = (UniqueConstraint("version", name="uq_wechat_reply_release_version"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, index=True)
    snapshot_json: Mapped[str] = mapped_column(Text)
    published_by_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    published_by_name: Mapped[str] = mapped_column(String(64), default="")
    rollback_from_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class WechatReplyConfiguration(Base):
    __tablename__ = "wechat_reply_configurations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default="default")
    draft_json: Mapped[str] = mapped_column(Text)
    published_release_id: Mapped[str | None] = mapped_column(
        ForeignKey("wechat_reply_releases.id"), nullable=True, index=True
    )
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    updated_by_name: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
