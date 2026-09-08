"""ORM 模型 · 域模块

按业务域拆分，统一由 app/models/__init__.py re-export，保持 from app.models import X 兼容。
"""
from datetime import datetime

from app.models.base import (
    Base,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Mapped,
    gen_id,
    mapped_column,
    relationship,
    utcnow,
)


class RmrbArticle(Base):
    """人民日报模块 · 时评/评论文章（独立于首页文章流）"""
    __tablename__ = "rmrb_articles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("rmrb"))
    title: Mapped[str] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(64), default="人民时评")  # 人民时评 / 评论
    source_url: Mapped[str] = mapped_column(String(512), default="")
    publish_date: Mapped[str] = mapped_column(String(10), default="")  # YYYY-MM-DD
    summary: Mapped[str] = mapped_column(String(512), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    # 主题标签 JSON 数组，如 ["政绩观","乡村振兴"]
    tags: Mapped[str] = mapped_column(Text, default="[]")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    read_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ShenlunTeachingExample(Base):
    """公共教研示范；与用户个人开采记录严格分表。"""
    __tablename__ = "shenlun_teaching_examples"
    __table_args__ = (
        UniqueConstraint("article_id", "version", name="uq_shenlun_teaching_article_version"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("ste"))
    article_id: Mapped[str] = mapped_column(ForeignKey("rmrb_articles.id"), index=True)
    version: Mapped[str] = mapped_column(String(32), default="1")
    source_excerpt: Mapped[str] = mapped_column(Text, default="")
    argument_json: Mapped[str] = mapped_column(Text, default="{}")
    terms_json: Mapped[str] = mapped_column(Text, default="[]")
    quotes_json: Mapped[str] = mapped_column(Text, default="[]")
    verbs_json: Mapped[str] = mapped_column(Text, default="[]")
    templates_json: Mapped[str] = mapped_column(Text, default="[]")
    practice_json: Mapped[str] = mapped_column(Text, default="{}")
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ShenlunMineLog(Base):
    """人民日报模块 · 开采本：一日一行（三刀解剖）"""
    __tablename__ = "shenlun_mine_logs"
    __table_args__ = (UniqueConstraint("user_id", "mine_date", name="uq_user_mine_date"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("sml"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    mine_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    article_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    article_title: Mapped[str] = mapped_column(String(256), default="")
    source_excerpt: Mapped[str] = mapped_column(Text, default="")
    argument_chain: Mapped[str] = mapped_column(Text, default="")  # 总骨架摘要（兼容）
    template_sentence: Mapped[str] = mapped_column(Text, default="")  # 句式摘要（兼容）
    terms_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON [{term,category,plainWord}]
    argument_json: Mapped[str] = mapped_column(Text, default="{}")  # JSON {overview,points[],...}
    templates_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON [{type,original,template,imitate}]
    quotes_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON [{text,source}] 经典金句
    verbs_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON [{verb,usage,category}] 高频动词
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ShenlunNormTerm(Base):
    """申论规范词库（分类积累）"""
    __tablename__ = "shenlun_norm_terms"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("snt"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    term: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(32), default="其他")  # 发展理念/战略方法/...
    usage_note: Mapped[str] = mapped_column(String(256), default="")  # 兼容旧数据；新流程不再填写
    source_title: Mapped[str] = mapped_column(String(256), default="")
    example_sentence: Mapped[str] = mapped_column(Text, default="")
    article_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    familiarity: Mapped[int] = mapped_column(Integer, default=1)  # 1-5
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ShenlunDrillLog(Base):
    """阶梯训练记录：造句 / 仿写 / 口述"""
    __tablename__ = "shenlun_drill_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("sdl"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id"), index=True)
    drill_type: Mapped[str] = mapped_column(String(16), index=True)  # sentence | imitate | oral
    content: Mapped[str] = mapped_column(Text, default="")
    prompt: Mapped[str] = mapped_column(Text, default="")  # 抽到的词/句式提示
    ref_mine_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_term_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[str]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ShenlunTermCategory(Base):
    """规范词 / 动词分类（后台与移动端可维护）"""
    __tablename__ = "shenlun_term_categories"
    __table_args__ = (UniqueConstraint("kind", "name", name="uq_shenlun_cat_kind_name"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("stc"))
    name: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="term", index=True)  # term | verb
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ShenlunSkeletonTemplate(Base):
    """论证骨架模版（总分论点 / 问题-原因-对策 等）"""
    __tablename__ = "shenlun_skeleton_templates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("skt"))
    name: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(String(256), default="")
    mode: Mapped[str] = mapped_column(String(16), default="linear")  # linear | points
    structure_json: Mapped[str] = mapped_column(Text, default="{}")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ShenlunSentenceType(Base):
    """万能句式类型（后台可维护，三刀第三刀下拉）"""
    __tablename__ = "shenlun_sentence_types"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("sst"))
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    tip: Mapped[str] = mapped_column(String(128), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ShenlunArgumentMethod(Base):
    """具体论证方法预设（后台可维护，三刀第二刀论证方法下拉）"""
    __tablename__ = "shenlun_argument_methods"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: gen_id("sam"))
    name: Mapped[str] = mapped_column(String(128), index=True)
    scope: Mapped[str] = mapped_column(String(16), default="point")  # overview | point
    note: Mapped[str] = mapped_column(String(256), default="")
    template: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
