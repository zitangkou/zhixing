"""人民日报模块 · 三刀元数据：规范词分类 / 骨架模版 / 句式类型 / 论证方法"""
from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.models import (
    ShenlunArgumentMethod,
    ShenlunSentenceType,
    ShenlunSkeletonTemplate,
    ShenlunTermCategory,
    gen_id,
)
from app.schemas import (
    ShenlunArgumentMethodCreate,
    ShenlunArgumentMethodOut,
    ShenlunArgumentMethodUpdate,
    ShenlunMetaOut,
    ShenlunSentenceTypeCreate,
    ShenlunSentenceTypeOut,
    ShenlunSentenceTypeUpdate,
    ShenlunSkeletonFieldDef,
    ShenlunSkeletonStructure,
    ShenlunSkeletonTemplateCreate,
    ShenlunSkeletonTemplateOut,
    ShenlunSkeletonTemplateUpdate,
    ShenlunTermCategoryCreate,
    ShenlunTermCategoryOut,
    ShenlunTermCategoryUpdate,
)

DEFAULT_TERM_CATEGORIES = [
    ("问题与积弊", 5),
    ("治理方法与理念", 8),
    ("成效与目标", 12),
    ("发展理念", 10),
    ("战略方法", 20),
    ("资源配置", 30),
    ("目标效能", 40),
    ("基础建设", 50),
    ("问题警示", 60),
    ("其他", 99),
]

DEFAULT_VERB_CATEGORIES = [
    ("治理动作", 10),
    ("分析评价", 20),
    ("动词其他", 99),
]

DEFAULT_ARGUMENT_METHODS = [
    {
        "name": "点例排比 + 类比延伸",
        "scope": "point",
        "note": "点例各一句话；3个排比；再类比到其他领域",
        "template": "提出分论点 → 列举3个同一领域正面案例（各一句） → 提炼共性 → 类比其他2～3个领域 → 总结升华",
        "sort": 10,
    },
    {
        "name": "问题切入 + 典型案例深描 + 原因挖掘",
        "scope": "point",
        "note": "案例稍展开：问题+做法+成效；再挖原因与对策",
        "template": "提出分论点 → 点出问题普遍性 → 典型案例1 → 典型案例2 → 提炼共性 → 挖掘原因 → 提出对策",
        "sort": 20,
    },
    {
        "name": "总—分—分—总",
        "scope": "overview",
        "note": "全文结构：总论点下并列分论点，收束升华",
        "template": "现象引题 → 提出总论点 → 分论点1 → 分论点2 → 总结升华（金句/呼吁）",
        "sort": 30,
    },
    {
        "name": "金句定调 + 排比收束",
        "scope": "overview",
        "note": "适合结尾或总论点后的升华段",
        "template": "引用金句定调 → 从……到……排比回顾案例 → 提炼主题一句 → 展望呼吁（回扣标题）",
        "sort": 40,
    },
]

DEFAULT_SENTENCE_TYPES = [
    ("dialectic", "对比转折型", "继续沿用……，与其说是……，不如说是……。", 10),
    ("direction", "排比递进型", "……并非……，而是在既有……内把……做得更……，于细微处见真章。", 20),
    ("solution", "条件递进型", "……往……方向多走一步，……就增强几分。", 30),
    ("quote", "金句型", "利民之事，丝发必兴。（结尾升华）", 40),
]

_DEFAULT_POINT_FIELDS = [
    {"key": "title", "label": "标题", "placeholder": "分论点标题"},
    {"key": "evidence", "label": "论据", "placeholder": "可选：事实/案例/论述"},
    {"key": "summary", "label": "小结", "placeholder": "可选：本点收束"},
]

DEFAULT_SKELETONS: list[dict] = [
    {
        "name": "总分论点型",
        "description": "总论点 → 分论点（标题/论据/小结）→ 总结",
        "mode": "points",
        "sort": 10,
        "structure": {
            "mode": "points",
            "overviewLabel": "总论点",
            "overviewPlaceholder": "一句话写出总论点",
            "pointFields": list(_DEFAULT_POINT_FIELDS),
            "fields": [],
        },
    },
    {
        "name": "问题-原因-对策",
        "description": "申论常见三段：问题 → 原因 → 对策",
        "mode": "linear",
        "sort": 20,
        "structure": {
            "mode": "linear",
            "fields": [
                {"key": "problem", "label": "问题", "placeholder": "指出主要问题/矛盾"},
                {"key": "cause", "label": "原因", "placeholder": "分析深层原因"},
                {"key": "solution", "label": "对策", "placeholder": "提出对策建议"},
            ],
            "pointFields": [],
        },
    },
    {
        "name": "是什么-为什么-怎么办",
        "description": "概念界定 → 必要性/原因 → 路径方法",
        "mode": "linear",
        "sort": 30,
        "structure": {
            "mode": "linear",
            "fields": [
                {"key": "what", "label": "是什么", "placeholder": "界定内涵或现象"},
                {"key": "why", "label": "为什么", "placeholder": "意义、必要性或原因"},
                {"key": "how", "label": "怎么办", "placeholder": "路径、举措"},
            ],
            "pointFields": [],
        },
    },
    {
        "name": "成绩-问题-对策",
        "description": "肯定成绩 → 指出问题 → 提出对策",
        "mode": "linear",
        "sort": 40,
        "structure": {
            "mode": "linear",
            "fields": [
                {"key": "achievement", "label": "成绩", "placeholder": "已有进展/成效"},
                {"key": "problem", "label": "问题", "placeholder": "不足与短板"},
                {"key": "solution", "label": "对策", "placeholder": "下一步怎么干"},
            ],
            "pointFields": [],
        },
    },
]


def _slug_code(name: str) -> str:
    raw = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name.strip()).strip("_")
    return (raw or "type")[:32]


def _loads(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _structure_from_raw(mode: str, raw: str | None) -> ShenlunSkeletonStructure:
    data = _loads(raw, {})
    if not isinstance(data, dict):
        data = {}
    m = str(data.get("mode") or mode or "linear")
    fields = [
        ShenlunSkeletonFieldDef(
            key=str(f.get("key") or f"f{i}"),
            label=str(f.get("label") or ""),
            placeholder=str(f.get("placeholder") or ""),
        )
        for i, f in enumerate(data.get("fields") or [])
        if isinstance(f, dict)
    ]
    point_fields = [
        ShenlunSkeletonFieldDef(
            key=str(f.get("key") or f"p{i}"),
            label=str(f.get("label") or ""),
            placeholder=str(f.get("placeholder") or ""),
        )
        for i, f in enumerate(data.get("pointFields") or [])
        if isinstance(f, dict)
    ]
    if m == "points" and not point_fields:
        point_fields = [ShenlunSkeletonFieldDef(**f) for f in _DEFAULT_POINT_FIELDS]
    return ShenlunSkeletonStructure(
        mode=m,
        fields=fields,
        overviewLabel=str(data.get("overviewLabel") or "全文总骨架"),
        overviewPlaceholder=str(data.get("overviewPlaceholder") or ""),
        pointFields=point_fields,
    )


def _structure_to_json(structure: ShenlunSkeletonStructure, mode: str | None = None) -> str:
    m = mode or structure.mode or "linear"
    payload = {
        "mode": m,
        "fields": [f.model_dump() for f in structure.fields],
        "overviewLabel": structure.overviewLabel,
        "overviewPlaceholder": structure.overviewPlaceholder,
        "pointFields": [f.model_dump() for f in structure.pointFields],
    }
    return json.dumps(payload, ensure_ascii=False)


def _default_structure_for_mode(mode: str, field_labels: list[str] | None = None) -> ShenlunSkeletonStructure:
    if mode == "points":
        return ShenlunSkeletonStructure(
            mode="points",
            overviewLabel="总论点",
            overviewPlaceholder="一句话总论点",
            pointFields=[ShenlunSkeletonFieldDef(**f) for f in _DEFAULT_POINT_FIELDS],
            fields=[],
        )
    labels = field_labels or ["问题", "原因", "对策"]
    fields = []
    for i, label in enumerate(labels):
        key = _slug_code(label) or f"step{i + 1}"
        fields.append(ShenlunSkeletonFieldDef(key=f"{key}_{i}" if i else key, label=label, placeholder=""))
    # ensure unique keys
    seen: set[str] = set()
    uniq: list[ShenlunSkeletonFieldDef] = []
    for i, f in enumerate(fields):
        k = f.key
        if k in seen:
            k = f"{f.key}_{i}"
        seen.add(k)
        uniq.append(ShenlunSkeletonFieldDef(key=k, label=f.label, placeholder=f.placeholder))
    return ShenlunSkeletonStructure(mode="linear", fields=uniq, pointFields=[])


def ensure_rmrb_meta_defaults(db: Session) -> None:
    # 规范词分类：空表全量写入；已有表则补缺
    existing_term = {
        c.name
        for c in db.query(ShenlunTermCategory).filter(ShenlunTermCategory.kind == "term").all()
    }
    # 兼容旧数据：无 kind 列时上面可能失败——迁移后再跑；此处也查全部 name
    if not existing_term:
        existing_term = {c.name for c in db.query(ShenlunTermCategory).all()}
    for name, sort in DEFAULT_TERM_CATEGORIES:
        if name in existing_term:
            continue
        db.add(
            ShenlunTermCategory(
                id=gen_id("stc"),
                name=name,
                kind="term",
                sort_order=sort,
                is_enabled=True,
            )
        )
        existing_term.add(name)

    existing_verb = {
        c.name
        for c in db.query(ShenlunTermCategory).filter(ShenlunTermCategory.kind == "verb").all()
    }
    for name, sort in DEFAULT_VERB_CATEGORIES:
        if name in existing_verb:
            continue
        db.add(
            ShenlunTermCategory(
                id=gen_id("stc"),
                name=name,
                kind="verb",
                sort_order=sort,
                is_enabled=True,
            )
        )
        existing_verb.add(name)

    if db.query(ShenlunSentenceType).count() == 0:
        for code, name, tip, sort in DEFAULT_SENTENCE_TYPES:
            db.add(
                ShenlunSentenceType(
                    id=gen_id("sst"),
                    code=code,
                    name=name,
                    tip=tip,
                    sort_order=sort,
                    is_enabled=True,
                )
            )
    else:
        # 补缺句式类型
        have = {t.code for t in db.query(ShenlunSentenceType).all()}
        for code, name, tip, sort in DEFAULT_SENTENCE_TYPES:
            if code in have:
                continue
            db.add(
                ShenlunSentenceType(
                    id=gen_id("sst"),
                    code=code,
                    name=name,
                    tip=tip,
                    sort_order=sort,
                    is_enabled=True,
                )
            )

    if db.query(ShenlunSkeletonTemplate).count() == 0:
        for item in DEFAULT_SKELETONS:
            structure = ShenlunSkeletonStructure.model_validate(item["structure"])
            db.add(
                ShenlunSkeletonTemplate(
                    id=gen_id("skt"),
                    name=item["name"],
                    description=item["description"],
                    mode=item["mode"],
                    structure_json=_structure_to_json(structure, item["mode"]),
                    sort_order=item["sort"],
                    is_enabled=True,
                )
            )

    if db.query(ShenlunArgumentMethod).count() == 0:
        for item in DEFAULT_ARGUMENT_METHODS:
            db.add(
                ShenlunArgumentMethod(
                    id=gen_id("sam"),
                    name=item["name"],
                    scope=item["scope"],
                    note=item["note"],
                    template=item["template"],
                    sort_order=item["sort"],
                    is_enabled=True,
                )
            )
    else:
        have = {m.name for m in db.query(ShenlunArgumentMethod).all()}
        for item in DEFAULT_ARGUMENT_METHODS:
            if item["name"] in have:
                continue
            db.add(
                ShenlunArgumentMethod(
                    id=gen_id("sam"),
                    name=item["name"],
                    scope=item["scope"],
                    note=item["note"],
                    template=item["template"],
                    sort_order=item["sort"],
                    is_enabled=True,
                )
            )
    db.commit()


def _cat_out(c: ShenlunTermCategory) -> ShenlunTermCategoryOut:
    return ShenlunTermCategoryOut(
        id=c.id,
        name=c.name,
        kind=getattr(c, "kind", None) or "term",
        sortOrder=c.sort_order,
        isEnabled=bool(c.is_enabled),
    )


def _skel_out(t: ShenlunSkeletonTemplate) -> ShenlunSkeletonTemplateOut:
    structure = _structure_from_raw(t.mode, t.structure_json)
    return ShenlunSkeletonTemplateOut(
        id=t.id,
        name=t.name,
        description=t.description or "",
        mode=t.mode or structure.mode,
        structure=structure,
        sortOrder=t.sort_order,
        isEnabled=bool(t.is_enabled),
    )


def _stype_out(t: ShenlunSentenceType) -> ShenlunSentenceTypeOut:
    return ShenlunSentenceTypeOut(
        id=t.id,
        code=t.code,
        name=t.name,
        tip=t.tip or "",
        sortOrder=t.sort_order,
        isEnabled=bool(t.is_enabled),
    )


def _amethod_out(m: ShenlunArgumentMethod) -> ShenlunArgumentMethodOut:
    return ShenlunArgumentMethodOut(
        id=m.id,
        name=m.name,
        scope=m.scope or "point",
        note=m.note or "",
        template=m.template or "",
        sortOrder=m.sort_order,
        isEnabled=bool(m.is_enabled),
    )


def get_meta(db: Session, enabled_only: bool = True) -> ShenlunMetaOut:
    ensure_rmrb_meta_defaults(db)
    cq = db.query(ShenlunTermCategory)
    sq = db.query(ShenlunSkeletonTemplate)
    tq = db.query(ShenlunSentenceType)
    mq = db.query(ShenlunArgumentMethod)
    if enabled_only:
        cq = cq.filter(ShenlunTermCategory.is_enabled.is_(True))
        sq = sq.filter(ShenlunSkeletonTemplate.is_enabled.is_(True))
        tq = tq.filter(ShenlunSentenceType.is_enabled.is_(True))
        mq = mq.filter(ShenlunArgumentMethod.is_enabled.is_(True))
    cats = cq.order_by(ShenlunTermCategory.sort_order, ShenlunTermCategory.name).all()
    skels = sq.order_by(ShenlunSkeletonTemplate.sort_order, ShenlunSkeletonTemplate.name).all()
    types = tq.order_by(ShenlunSentenceType.sort_order, ShenlunSentenceType.name).all()
    methods = mq.order_by(ShenlunArgumentMethod.sort_order, ShenlunArgumentMethod.name).all()
    term_cats = [_cat_out(c) for c in cats if (getattr(c, "kind", None) or "term") == "term"]
    verb_cats = [_cat_out(c) for c in cats if getattr(c, "kind", None) == "verb"]
    return ShenlunMetaOut(
        termCategories=term_cats,
        verbCategories=verb_cats,
        skeletonTemplates=[_skel_out(t) for t in skels],
        sentenceTypes=[_stype_out(t) for t in types],
        argumentMethodPresets=[_amethod_out(m) for m in methods],
    )


# ---- term categories ----

def list_term_categories(db: Session, enabled_only: bool = False) -> list[ShenlunTermCategoryOut]:
    ensure_rmrb_meta_defaults(db)
    q = db.query(ShenlunTermCategory)
    if enabled_only:
        q = q.filter(ShenlunTermCategory.is_enabled.is_(True))
    rows = q.order_by(ShenlunTermCategory.sort_order, ShenlunTermCategory.name).all()
    return [_cat_out(c) for c in rows]


def create_term_category(db: Session, body: ShenlunTermCategoryCreate) -> ShenlunTermCategoryOut:
    name = body.name.strip()
    if not name:
        raise ValueError("分类名不能为空")
    kind = (body.kind or "term").strip() or "term"
    if kind not in ("term", "verb"):
        raise ValueError("kind 须为 term 或 verb")
    exists = (
        db.query(ShenlunTermCategory)
        .filter(ShenlunTermCategory.name == name, ShenlunTermCategory.kind == kind)
        .first()
    )
    if not exists:
        # 兼容旧库仅有 name 唯一约束
        exists = db.query(ShenlunTermCategory).filter(ShenlunTermCategory.name == name).first()
        if exists and (getattr(exists, "kind", "term") or "term") != kind:
            raise ValueError("分类名与其他类型冲突，请换一个名称")
    if exists:
        raise ValueError("分类已存在")
    max_order = db.query(ShenlunTermCategory).filter(ShenlunTermCategory.kind == kind).count()
    c = ShenlunTermCategory(
        id=gen_id("stc"),
        name=name,
        kind=kind,
        sort_order=body.sortOrder if body.sortOrder else (max_order + 1) * 10,
        is_enabled=body.isEnabled,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _cat_out(c)


def update_term_category(
    db: Session, cat_id: str, body: ShenlunTermCategoryUpdate
) -> ShenlunTermCategoryOut | None:
    c = db.get(ShenlunTermCategory, cat_id)
    if not c:
        return None
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        name = str(data["name"]).strip()
        if not name:
            raise ValueError("分类名不能为空")
        other = (
            db.query(ShenlunTermCategory)
            .filter(ShenlunTermCategory.name == name, ShenlunTermCategory.id != cat_id)
            .first()
        )
        if other:
            raise ValueError("分类已存在")
        c.name = name
    if "kind" in data and data["kind"] is not None:
        kind = str(data["kind"]).strip() or "term"
        if kind not in ("term", "verb"):
            raise ValueError("kind 须为 term 或 verb")
        c.kind = kind
    if "sortOrder" in data and data["sortOrder"] is not None:
        c.sort_order = int(data["sortOrder"])
    if "isEnabled" in data and data["isEnabled"] is not None:
        c.is_enabled = bool(data["isEnabled"])
    db.commit()
    db.refresh(c)
    return _cat_out(c)


def delete_term_category(db: Session, cat_id: str) -> bool:
    c = db.get(ShenlunTermCategory, cat_id)
    if not c:
        return False
    db.delete(c)
    db.commit()
    return True


# ---- skeleton templates ----

def list_skeleton_templates(db: Session, enabled_only: bool = False) -> list[ShenlunSkeletonTemplateOut]:
    ensure_rmrb_meta_defaults(db)
    q = db.query(ShenlunSkeletonTemplate)
    if enabled_only:
        q = q.filter(ShenlunSkeletonTemplate.is_enabled.is_(True))
    rows = q.order_by(ShenlunSkeletonTemplate.sort_order, ShenlunSkeletonTemplate.name).all()
    return [_skel_out(t) for t in rows]


def create_skeleton_template(
    db: Session, body: ShenlunSkeletonTemplateCreate
) -> ShenlunSkeletonTemplateOut:
    name = body.name.strip()
    if not name:
        raise ValueError("模版名称不能为空")
    mode = (body.mode or "linear").strip() or "linear"
    if mode not in ("linear", "points"):
        raise ValueError("mode 仅支持 linear / points")
    structure = body.structure or _default_structure_for_mode(mode)
    structure.mode = mode
    if mode == "linear" and not structure.fields:
        structure = _default_structure_for_mode("linear")
    if mode == "points" and not structure.pointFields:
        structure = _default_structure_for_mode("points")
    t = ShenlunSkeletonTemplate(
        id=gen_id("skt"),
        name=name,
        description=(body.description or "").strip(),
        mode=mode,
        structure_json=_structure_to_json(structure, mode),
        sort_order=body.sortOrder,
        is_enabled=body.isEnabled,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _skel_out(t)


def update_skeleton_template(
    db: Session, tpl_id: str, body: ShenlunSkeletonTemplateUpdate
) -> ShenlunSkeletonTemplateOut | None:
    t = db.get(ShenlunSkeletonTemplate, tpl_id)
    if not t:
        return None
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        name = str(data["name"]).strip()
        if not name:
            raise ValueError("模版名称不能为空")
        t.name = name
    if "description" in data and data["description"] is not None:
        t.description = str(data["description"]).strip()
    if "mode" in data and data["mode"] is not None:
        mode = str(data["mode"]).strip() or "linear"
        if mode not in ("linear", "points"):
            raise ValueError("mode 仅支持 linear / points")
        t.mode = mode
    if "structure" in data and data["structure"] is not None:
        structure = ShenlunSkeletonStructure.model_validate(data["structure"])
        structure.mode = t.mode
        t.structure_json = _structure_to_json(structure, t.mode)
    if "sortOrder" in data and data["sortOrder"] is not None:
        t.sort_order = int(data["sortOrder"])
    if "isEnabled" in data and data["isEnabled"] is not None:
        t.is_enabled = bool(data["isEnabled"])
    db.commit()
    db.refresh(t)
    return _skel_out(t)


def delete_skeleton_template(db: Session, tpl_id: str) -> bool:
    t = db.get(ShenlunSkeletonTemplate, tpl_id)
    if not t:
        return False
    db.delete(t)
    db.commit()
    return True


# ---- sentence types ----

def list_sentence_types(db: Session, enabled_only: bool = False) -> list[ShenlunSentenceTypeOut]:
    ensure_rmrb_meta_defaults(db)
    q = db.query(ShenlunSentenceType)
    if enabled_only:
        q = q.filter(ShenlunSentenceType.is_enabled.is_(True))
    rows = q.order_by(ShenlunSentenceType.sort_order, ShenlunSentenceType.name).all()
    return [_stype_out(t) for t in rows]


def create_sentence_type(db: Session, body: ShenlunSentenceTypeCreate) -> ShenlunSentenceTypeOut:
    code = (body.code or "").strip() or _slug_code(body.name)
    name = body.name.strip()
    if not name:
        raise ValueError("类型名称不能为空")
    exists = db.query(ShenlunSentenceType).filter(ShenlunSentenceType.code == code).first()
    if exists:
        raise ValueError("类型编码已存在")
    t = ShenlunSentenceType(
        id=gen_id("sst"),
        code=code,
        name=name,
        tip=(body.tip or "").strip(),
        sort_order=body.sortOrder,
        is_enabled=body.isEnabled,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _stype_out(t)


def update_sentence_type(
    db: Session, type_id: str, body: ShenlunSentenceTypeUpdate
) -> ShenlunSentenceTypeOut | None:
    t = db.get(ShenlunSentenceType, type_id)
    if not t:
        return None
    data = body.model_dump(exclude_unset=True)
    if "code" in data and data["code"] is not None:
        code = str(data["code"]).strip()
        if not code:
            raise ValueError("编码不能为空")
        other = (
            db.query(ShenlunSentenceType)
            .filter(ShenlunSentenceType.code == code, ShenlunSentenceType.id != type_id)
            .first()
        )
        if other:
            raise ValueError("类型编码已存在")
        t.code = code
    if "name" in data and data["name"] is not None:
        name = str(data["name"]).strip()
        if not name:
            raise ValueError("类型名称不能为空")
        t.name = name
    if "tip" in data and data["tip"] is not None:
        t.tip = str(data["tip"]).strip()
    if "sortOrder" in data and data["sortOrder"] is not None:
        t.sort_order = int(data["sortOrder"])
    if "isEnabled" in data and data["isEnabled"] is not None:
        t.is_enabled = bool(data["isEnabled"])
    db.commit()
    db.refresh(t)
    return _stype_out(t)


def delete_sentence_type(db: Session, type_id: str) -> bool:
    t = db.get(ShenlunSentenceType, type_id)
    if not t:
        return False
    db.delete(t)
    db.commit()
    return True


# ---- argument methods ----

_VALID_SCOPES = {"overview", "point"}


def list_argument_methods(db: Session, enabled_only: bool = False) -> list[ShenlunArgumentMethodOut]:
    ensure_rmrb_meta_defaults(db)
    q = db.query(ShenlunArgumentMethod)
    if enabled_only:
        q = q.filter(ShenlunArgumentMethod.is_enabled.is_(True))
    rows = q.order_by(ShenlunArgumentMethod.sort_order, ShenlunArgumentMethod.name).all()
    return [_amethod_out(m) for m in rows]


def create_argument_method(db: Session, body: ShenlunArgumentMethodCreate) -> ShenlunArgumentMethodOut:
    name = (body.name or "").strip()
    if not name:
        raise ValueError("方法名称不能为空")
    scope = (body.scope or "point").strip() or "point"
    if scope not in _VALID_SCOPES:
        raise ValueError("适用范围须为 overview 或 point")
    exists = db.query(ShenlunArgumentMethod).filter(ShenlunArgumentMethod.name == name).first()
    if exists:
        raise ValueError("方法名称已存在")
    m = ShenlunArgumentMethod(
        id=gen_id("sam"),
        name=name,
        scope=scope,
        note=(body.note or "").strip(),
        template=(body.template or "").strip(),
        sort_order=body.sortOrder,
        is_enabled=body.isEnabled,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _amethod_out(m)


def update_argument_method(
    db: Session, method_id: str, body: ShenlunArgumentMethodUpdate
) -> ShenlunArgumentMethodOut | None:
    m = db.get(ShenlunArgumentMethod, method_id)
    if not m:
        return None
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        name = str(data["name"]).strip()
        if not name:
            raise ValueError("方法名称不能为空")
        other = (
            db.query(ShenlunArgumentMethod)
            .filter(ShenlunArgumentMethod.name == name, ShenlunArgumentMethod.id != method_id)
            .first()
        )
        if other:
            raise ValueError("方法名称已存在")
        m.name = name
    if "scope" in data and data["scope"] is not None:
        scope = str(data["scope"]).strip() or "point"
        if scope not in _VALID_SCOPES:
            raise ValueError("适用范围须为 overview 或 point")
        m.scope = scope
    if "note" in data and data["note"] is not None:
        m.note = str(data["note"]).strip()
    if "template" in data and data["template"] is not None:
        m.template = str(data["template"]).strip()
    if "sortOrder" in data and data["sortOrder"] is not None:
        m.sort_order = int(data["sortOrder"])
    if "isEnabled" in data and data["isEnabled"] is not None:
        m.is_enabled = bool(data["isEnabled"])
    db.commit()
    db.refresh(m)
    return _amethod_out(m)


def delete_argument_method(db: Session, method_id: str) -> bool:
    m = db.get(ShenlunArgumentMethod, method_id)
    if not m:
        return False
    db.delete(m)
    db.commit()
    return True
