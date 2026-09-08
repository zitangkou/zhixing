"""账号内容运营模板、发布包与双审核记录。"""
from datetime import datetime
from app.models.base import Base, DateTime, ForeignKey, Integer, Mapped, String, Text, UniqueConstraint, gen_id, mapped_column, relationship, utcnow


class ContentOperationTemplate(Base):
    __tablename__ = "content_operation_templates"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("cot"))
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    product_key: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(256), default="")
    slots_json: Mapped[str] = mapped_column(Text, default="[]")
    channels_json: Mapped[str] = mapped_column(Text, default="[]")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="enabled", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ContentPublishPackage(Base):
    __tablename__ = "content_publish_packages"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("cpp"))
    product_key: Mapped[str] = mapped_column(String(32), index=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("content_operation_templates.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    source_title: Mapped[str] = mapped_column(String(256), default="")
    campaign_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    deep_link: Mapped[str] = mapped_column(String(512), default="")
    entry_target_json: Mapped[str] = mapped_column(Text, default="{}")
    slot_values_json: Mapped[str] = mapped_column(Text, default="{}")
    variants_json: Mapped[str] = mapped_column(Text, default="{}")
    review_note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    planned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    review_records: Mapped[list["ContentReviewRecord"]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
        order_by="ContentReviewRecord.created_at",
    )


class ContentReviewRecord(Base):
    """教研/运营审核的不可覆盖留痕。"""

    __tablename__ = "content_review_records"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("crr"))
    package_id: Mapped[str] = mapped_column(ForeignKey("content_publish_packages.id"), index=True)
    stage: Mapped[str] = mapped_column(String(24), index=True)  # teaching | operations
    decision: Mapped[str] = mapped_column(String(16), index=True)  # approved | rejected
    checklist_json: Mapped[str] = mapped_column(Text, default="{}")
    note: Mapped[str] = mapped_column(Text, default="")
    reviewer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewer_username: Mapped[str] = mapped_column(String(64), default="")
    reviewer_name: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    package: Mapped[ContentPublishPackage] = relationship(back_populates="review_records")


class EntryAttributionEvent(Base):
    """跨公众号、运营渠道、H5 与小程序的入口归因事件。"""

    __tablename__ = "entry_attribution_events"
    __table_args__ = (UniqueConstraint("client_event_id", name="uq_entry_event_client_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("eae"))
    client_event_id: Mapped[str] = mapped_column(String(64), index=True)
    visitor_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("app_users.id"), nullable=True, index=True)
    product_key: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    entry_id: Mapped[str] = mapped_column(String(64), index=True)
    content_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    section: Mapped[str] = mapped_column(String(32), default="")
    channel: Mapped[str] = mapped_column(String(32), default="direct", index=True)
    campaign_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    platform: Mapped[str] = mapped_column(String(16), default="", index=True)
    scene: Mapped[str] = mapped_column(String(64), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
