"""管理端创意平台：灵感、参考物料、实践及审计事件。"""
from datetime import datetime
from sqlalchemy import Float
from app.models.base import Base, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Mapped, gen_id, mapped_column, utcnow

class CreativeIdea(Base):
    __tablename__ = "creative_ideas"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("cri"))
    title: Mapped[str] = mapped_column(String(120), default="未命名创意")
    original_text: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    idea_type: Mapped[str] = mapped_column(String(32), default="unclassified", index=True)
    status: Mapped[str] = mapped_column(String(24), default="inbox", index=True)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    starred: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("creative_ideas.id"), nullable=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id"), index=True)
    creator_id: Mapped[int] = mapped_column(Integer, index=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private", index=True)
    next_action: Mapped[str] = mapped_column(String(500), default="")
    planned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    conclusion: Mapped[str] = mapped_column(Text, default="")
    pause_reason: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, index=True)

class CreativeTag(Base):
    __tablename__ = "creative_tags"
    __table_args__ = (UniqueConstraint("owner_id", "normalized_name", name="uq_creative_tag_owner_name"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("crt"))
    owner_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id"), index=True)
    name: Mapped[str] = mapped_column(String(48))
    normalized_name: Mapped[str] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class CreativeIdeaTag(Base):
    __tablename__ = "creative_idea_tags"
    __table_args__ = (UniqueConstraint("idea_id", "tag_id", name="uq_creative_idea_tag"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idea_id: Mapped[str] = mapped_column(ForeignKey("creative_ideas.id", ondelete="CASCADE"), index=True)
    tag_id: Mapped[str] = mapped_column(ForeignKey("creative_tags.id", ondelete="CASCADE"), index=True)

class CreativeMaterial(Base):
    __tablename__ = "creative_materials"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("crm"))
    owner_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id"), index=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private", index=True)
    kind: Mapped[str] = mapped_column(String(24), default="note")
    title: Mapped[str] = mapped_column(String(240), default="")
    source_name: Mapped[str] = mapped_column(String(160), default="")
    author: Mapped[str] = mapped_column(String(120), default="")
    url: Mapped[str] = mapped_column(String(2048), default="")
    excerpt: Mapped[str] = mapped_column(Text, default="")
    insight: Mapped[str] = mapped_column(Text, default="")
    locator: Mapped[str] = mapped_column(String(240), default="")
    reference_type: Mapped[str] = mapped_column(String(32), default="")
    reference_id: Mapped[str] = mapped_column(String(64), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

class CreativeIdeaMaterial(Base):
    __tablename__ = "creative_idea_materials"
    __table_args__ = (UniqueConstraint("idea_id", "material_id", name="uq_creative_idea_material"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idea_id: Mapped[str] = mapped_column(ForeignKey("creative_ideas.id", ondelete="CASCADE"), index=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("creative_materials.id", ondelete="CASCADE"), index=True)
    insight: Mapped[str] = mapped_column(Text, default="")

class CreativeIdeaRelation(Base):
    __tablename__ = "creative_idea_relations"
    __table_args__ = (UniqueConstraint("left_id", "right_id", name="uq_creative_idea_relation"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    left_id: Mapped[str] = mapped_column(ForeignKey("creative_ideas.id", ondelete="CASCADE"), index=True)
    right_id: Mapped[str] = mapped_column(ForeignKey("creative_ideas.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class CreativePractice(Base):
    __tablename__ = "creative_practices"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("crp"))
    idea_id: Mapped[str] = mapped_column(ForeignKey("creative_ideas.id"), index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24), default="research")
    title: Mapped[str] = mapped_column(String(240), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    action: Mapped[str] = mapped_column(Text, default="")
    expectation: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")
    decision: Mapped[str] = mapped_column(String(24), default="")
    next_action: Mapped[str] = mapped_column(String(500), default="")
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    metrics_json: Mapped[str] = mapped_column(Text, default="[]")
    result_links_json: Mapped[str] = mapped_column(Text, default="[]")
    version: Mapped[int] = mapped_column(Integer, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

class CreativeEvent(Base):
    __tablename__ = "creative_events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("cre"))
    idea_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    object_type: Mapped[str] = mapped_column(String(16), default="idea", index=True)
    object_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    actor_id: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

class CreativeCaptureRequest(Base):
    __tablename__ = "creative_capture_requests"
    __table_args__ = (UniqueConstraint("admin_id", "idempotency_key", name="uq_creative_capture_admin_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    payload_hash: Mapped[str] = mapped_column(String(64))
    idea_id: Mapped[str] = mapped_column(ForeignKey("creative_ideas.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class CreativeAttachment(Base):
    __tablename__ = "creative_attachments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("cra"))
    material_id: Mapped[str] = mapped_column(ForeignKey("creative_materials.id"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id"), index=True)
    storage_key: Mapped[str] = mapped_column(String(64), unique=True)
    original_name: Mapped[str] = mapped_column(String(240))
    mime: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
