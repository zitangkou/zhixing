"""人民日报模块 · 开采本 / 规范词库 / 阶梯训练"""
from __future__ import annotations

import json
import re
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import AppUser, ShenlunDrillLog, ShenlunMineLog, ShenlunNormTerm, ShenlunTermCategory, gen_id
from app.services.activity_service import record_event
from app.schemas import (
    ShenlunArgumentFieldValue,
    ShenlunArgumentPoint,
    ShenlunArgumentSkeleton,
    ShenlunDrillCreate,
    ShenlunDrillLogOut,
    ShenlunMineLogOut,
    ShenlunMineLogUpdate,
    ShenlunMineLogUpsert,
    ShenlunMineTermItem,
    ShenlunNormTermAdd,
    ShenlunNormTermOut,
    ShenlunNormTermUpdate,
    ShenlunQuoteItem,
    ShenlunStatsOut,
    ShenlunTemplateItem,
    ShenlunVerbItem,
)
from app.timezone import now, today as today_str

TEMPLATE_TYPE_LABELS = {
    "dialectic": "对比转折型",
    "direction": "排比递进型",
    "solution": "条件递进型",
    "quote": "金句型",
}

_TERM_SPLIT_RE = re.compile(r"[、,，;；/｜|\n]+")


def _loads(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _allowed_term_categories(db: Session | None) -> set[str] | None:
    """None 表示不限制（无 db 时）；否则返回库中启用的规范词分类名。"""
    if db is None:
        return None
    rows = (
        db.query(ShenlunTermCategory)
        .filter(
            ShenlunTermCategory.is_enabled.is_(True),
            ShenlunTermCategory.kind.in_(["term", ""]),
        )
        .all()
    )
    names = {c.name for c in rows if (getattr(c, "kind", None) or "term") == "term"}
    # 兼容旧行 kind 为空
    if not names:
        names = {c.name for c in db.query(ShenlunTermCategory).filter(ShenlunTermCategory.is_enabled.is_(True)).all()}
    return names or None


def _normalize_term_items(terms, db: Session | None = None) -> list[ShenlunMineTermItem]:
    """支持顿号/逗号一次录入多个词；分类以库内为准，未知分类保留原名。"""
    out: list[ShenlunMineTermItem] = []
    seen: set[str] = set()
    allowed = _allowed_term_categories(db)
    for item in terms or []:
        if isinstance(item, str):
            raw_term, cat, plain = item.strip(), "其他", ""
        elif isinstance(item, dict):
            raw_term = str(item.get("term") or "").strip()
            cat = str(item.get("category") or "其他").strip() or "其他"
            plain = str(item.get("plainWord") or "").strip()
        else:
            raw_term = str(getattr(item, "term", "") or "").strip()
            cat = str(getattr(item, "category", "其他") or "其他").strip() or "其他"
            plain = str(getattr(item, "plainWord", "") or "").strip()
        if not raw_term:
            continue
        if allowed is not None and cat not in allowed:
            # 不强制改成「其他」，方便用户新建分类后立即使用；仅当分类名为空时兜底
            cat = cat or "其他"
        parts = [p.strip() for p in _TERM_SPLIT_RE.split(raw_term) if p.strip()]
        if not parts:
            parts = [raw_term]
        for term in parts:
            if term in seen:
                continue
            seen.add(term)
            out.append(ShenlunMineTermItem(term=term, category=cat, plainWord=plain))
            if len(out) >= 60:
                return out
    return out


def _parse_terms(raw: str | None, db: Session | None = None) -> list[ShenlunMineTermItem]:
    data = _loads(raw, [])
    if not isinstance(data, list):
        return []
    return _normalize_term_items(data, db)


def _normalize_quotes(items) -> list[ShenlunQuoteItem]:
    out: list[ShenlunQuoteItem] = []
    for item in items or []:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            source = str(item.get("source") or "").strip()
            meaning = str(item.get("meaning") or "").strip()
        else:
            text = str(getattr(item, "text", "") or "").strip()
            source = str(getattr(item, "source", "") or "").strip()
            meaning = str(getattr(item, "meaning", "") or "").strip()
        if not text:
            continue
        out.append(ShenlunQuoteItem(text=text, source=source, meaning=meaning))
        if len(out) >= 20:
            break
    return out


def _parse_quotes(raw: str | None) -> list[ShenlunQuoteItem]:
    data = _loads(raw, [])
    if not isinstance(data, list):
        return []
    return _normalize_quotes(data)


def _normalize_verbs(items) -> list[ShenlunVerbItem]:
    out: list[ShenlunVerbItem] = []
    seen: set[str] = set()
    for item in items or []:
        if isinstance(item, dict):
            raw_verb = str(item.get("verb") or "").strip()
            usage = str(item.get("usage") or "").strip()
            cat = str(item.get("category") or "动词其他").strip() or "动词其他"
        else:
            raw_verb = str(getattr(item, "verb", "") or "").strip()
            usage = str(getattr(item, "usage", "") or "").strip()
            cat = str(getattr(item, "category", "动词其他") or "动词其他").strip() or "动词其他"
        if not raw_verb:
            continue
        parts = [p.strip() for p in _TERM_SPLIT_RE.split(raw_verb) if p.strip()]
        for verb in parts or [raw_verb]:
            if verb in seen:
                continue
            seen.add(verb)
            out.append(ShenlunVerbItem(verb=verb, usage=usage, category=cat))
            if len(out) >= 40:
                return out
    return out


def _parse_verbs(raw: str | None) -> list[ShenlunVerbItem]:
    data = _loads(raw, [])
    if not isinstance(data, list):
        return []
    return _normalize_verbs(data)


def _parse_argument(raw: str | None, fallback_chain: str = "") -> ShenlunArgumentSkeleton:
    data = _loads(raw, {})
    if not isinstance(data, dict):
        return ShenlunArgumentSkeleton(overview=fallback_chain or "", points=[])

    points = []
    for p in data.get("points") or []:
        if not isinstance(p, dict):
            continue
        points.append(
            ShenlunArgumentPoint(
                title=str(p.get("title") or ""),
                claim=str(p.get("claim") or ""),
                evidence=str(p.get("evidence") or ""),
                summary=str(p.get("summary") or ""),
                method=str(p.get("method") or ""),
                methodNote=str(p.get("methodNote") or ""),
                template=str(p.get("template") or ""),
            )
        )
    fields = []
    for f in data.get("fields") or []:
        if not isinstance(f, dict):
            continue
        fields.append(
            ShenlunArgumentFieldValue(
                key=str(f.get("key") or ""),
                label=str(f.get("label") or ""),
                content=str(f.get("content") or ""),
            )
        )
    overview = str(data.get("overview") or "") or (fallback_chain or "")
    return ShenlunArgumentSkeleton(
        templateId=str(data.get("templateId") or ""),
        templateName=str(data.get("templateName") or ""),
        mode=str(data.get("mode") or ("linear" if fields and not points else "points")),
        overview=overview,
        conclusion=str(data.get("conclusion") or ""),
        overviewMethod=str(data.get("overviewMethod") or ""),
        overviewTemplate=str(data.get("overviewTemplate") or ""),
        fields=fields,
        points=points,
    )


def _parse_templates(raw: str | None, fallback_sentence: str = "") -> list[ShenlunTemplateItem]:
    data = _loads(raw, [])
    out: list[ShenlunTemplateItem] = []
    if isinstance(data, list):
        for t in data:
            if isinstance(t, dict):
                out.append(
                    ShenlunTemplateItem(
                        type=str(t.get("type") or "dialectic"),
                        typeName=str(t.get("typeName") or ""),
                        original=str(t.get("original") or ""),
                        template=str(t.get("template") or ""),
                        imitate=str(t.get("imitate") or ""),
                    )
                )
            elif isinstance(t, str) and t.strip():
                out.append(ShenlunTemplateItem(type="dialectic", original=t.strip()))
    if not out and fallback_sentence.strip():
        out.append(ShenlunTemplateItem(type="dialectic", original=fallback_sentence.strip()))
    return out[:5]


def _argument_summary(arg: ShenlunArgumentSkeleton) -> str:
    if arg.templateName.strip() and arg.overview.strip():
        base = f"[{arg.templateName}] {arg.overview.strip()}"
        if arg.conclusion.strip():
            base = f"{base} → {arg.conclusion.strip()}"
        return base[:500]
    if arg.overview.strip():
        return arg.overview.strip()[:500]
    if arg.fields:
        parts = [f"{f.label or f.key}：{(f.content or '')[:40]}" for f in arg.fields if f.content.strip()]
        if parts:
            return " → ".join(parts)[:500]
    titles = [p.title.strip() for p in arg.points if p.title.strip()]
    if titles:
        prefix = f"[{arg.templateName}] " if arg.templateName.strip() else ""
        tail = f" → {arg.conclusion.strip()}" if arg.conclusion.strip() else ""
        return (prefix + " → ".join(titles) + tail)[:500]
    return arg.templateName.strip()[:500]


def _templates_summary(templates: list[ShenlunTemplateItem]) -> str:
    for t in templates:
        if t.original.strip():
            return t.original.strip()[:500]
        if t.template.strip():
            return t.template.strip()[:500]
    return ""


def _mine_to_out(m: ShenlunMineLog) -> ShenlunMineLogOut:
    terms = _parse_terms(m.terms_json)
    argument = _parse_argument(getattr(m, "argument_json", None), m.argument_chain or "")
    templates = _parse_templates(getattr(m, "templates_json", None), m.template_sentence or "")
    quotes = _parse_quotes(getattr(m, "quotes_json", None))
    verbs = _parse_verbs(getattr(m, "verbs_json", None))
    return ShenlunMineLogOut(
        id=m.id,
        mineDate=m.mine_date,
        articleId=m.article_id,
        articleTitle=m.article_title or "",
        sourceExcerpt=m.source_excerpt or "",
        argumentChain=m.argument_chain or argument.overview,
        templateSentence=m.template_sentence or _templates_summary(templates),
        terms=terms,
        quotes=quotes,
        verbs=verbs,
        argument=argument,
        templates=templates,
        createdAt=m.created_at,
        updatedAt=m.updated_at,
    )


def _term_to_out(t: ShenlunNormTerm) -> ShenlunNormTermOut:
    return ShenlunNormTermOut(
        id=t.id,
        term=t.term,
        category=getattr(t, "category", None) or "其他",
        usageNote=t.usage_note or "",
        sourceTitle=t.source_title or "",
        exampleSentence=t.example_sentence or "",
        articleId=t.article_id,
        familiarity=t.familiarity or 1,
        mastered=bool(t.mastered),
        createdAt=t.created_at,
    )


def _sync_terms_from_mine(
    db: Session, user: AppUser, m: ShenlunMineLog, terms: list[ShenlunMineTermItem]
) -> None:
    title = m.article_title or ""
    for item in terms:
        existing = (
            db.query(ShenlunNormTerm)
            .filter(ShenlunNormTerm.user_id == user.id, ShenlunNormTerm.term == item.term)
            .first()
        )
        if existing:
            if title and not existing.source_title:
                existing.source_title = title
            if m.article_id and not existing.article_id:
                existing.article_id = m.article_id
            if item.category and (not getattr(existing, "category", None) or existing.category == "其他"):
                existing.category = item.category
            if item.plainWord:
                existing.usage_note = item.plainWord
            continue
        db.add(
            ShenlunNormTerm(
                id=gen_id("snt"),
                user_id=user.id,
                term=item.term,
                category=item.category or "其他",
                usage_note=item.plainWord or "",
                source_title=title,
                article_id=m.article_id,
            )
        )


def list_mines(db: Session, user: AppUser) -> list[ShenlunMineLogOut]:
    rows = (
        db.query(ShenlunMineLog)
        .filter(ShenlunMineLog.user_id == user.id)
        .order_by(ShenlunMineLog.mine_date.desc(), ShenlunMineLog.id.desc())
        .all()
    )
    return [_mine_to_out(r) for r in rows]


def get_mine(db: Session, user: AppUser, mine_id: str) -> ShenlunMineLogOut | None:
    m = db.get(ShenlunMineLog, mine_id)
    if not m or m.user_id != user.id:
        return None
    return _mine_to_out(m)


def get_mine_by_date(db: Session, user: AppUser, mine_date: str) -> ShenlunMineLogOut | None:
    m = (
        db.query(ShenlunMineLog)
        .filter(ShenlunMineLog.user_id == user.id, ShenlunMineLog.mine_date == mine_date)
        .first()
    )
    return _mine_to_out(m) if m else None


def upsert_mine(db: Session, user: AppUser, body: ShenlunMineLogUpsert) -> ShenlunMineLogOut:
    mine_date = (body.mineDate or today_str()).strip()
    terms = _normalize_term_items(body.terms, db)
    quotes = _normalize_quotes(body.quotes)
    verbs = _normalize_verbs(body.verbs)
    argument = body.argument or ShenlunArgumentSkeleton(overview=body.argumentChain or "", points=[])
    if not argument.overview and body.argumentChain:
        argument.overview = body.argumentChain
    templates = list(body.templates or [])
    if not templates and body.templateSentence.strip():
        templates = [ShenlunTemplateItem(type="dialectic", original=body.templateSentence.strip())]

    m = (
        db.query(ShenlunMineLog)
        .filter(ShenlunMineLog.user_id == user.id, ShenlunMineLog.mine_date == mine_date)
        .first()
    )
    payload = {
        "article_id": body.articleId,
        "article_title": (body.articleTitle or "").strip(),
        "source_excerpt": body.sourceExcerpt or "",
        "argument_chain": _argument_summary(argument),
        "template_sentence": _templates_summary(templates),
        "terms_json": json.dumps([t.model_dump() for t in terms], ensure_ascii=False),
        "argument_json": json.dumps(argument.model_dump(), ensure_ascii=False),
        "templates_json": json.dumps([t.model_dump() for t in templates], ensure_ascii=False),
        "quotes_json": json.dumps([q.model_dump() for q in quotes], ensure_ascii=False),
        "verbs_json": json.dumps([v.model_dump() for v in verbs], ensure_ascii=False),
    }
    if m:
        for k, v in payload.items():
            setattr(m, k, v)
    else:
        m = ShenlunMineLog(id=gen_id("sml"), user_id=user.id, mine_date=mine_date, **payload)
        db.add(m)
    _sync_terms_from_mine(db, user, m, terms)
    db.commit()
    db.refresh(m)
    record_event(
        db,
        user.id,
        "shenlun_mined",
        {"mineDate": mine_date, "articleId": body.articleId, "articleTitle": (body.articleTitle or "").strip()},
    )
    return _mine_to_out(m)


def update_mine(
    db: Session, user: AppUser, mine_id: str, body: ShenlunMineLogUpdate
) -> ShenlunMineLogOut | None:
    m = db.get(ShenlunMineLog, mine_id)
    if not m or m.user_id != user.id:
        return None
    data = body.model_dump(exclude_unset=True)
    if "terms" in data:
        terms = _normalize_term_items(data.pop("terms"), db)
        m.terms_json = json.dumps([t.model_dump() for t in terms], ensure_ascii=False)
        _sync_terms_from_mine(db, user, m, terms)
    if "quotes" in data and data["quotes"] is not None:
        quotes = _normalize_quotes(data.pop("quotes"))
        m.quotes_json = json.dumps([q.model_dump() for q in quotes], ensure_ascii=False)
    if "verbs" in data and data["verbs"] is not None:
        verbs = _normalize_verbs(data.pop("verbs"))
        m.verbs_json = json.dumps([v.model_dump() for v in verbs], ensure_ascii=False)
    if "argument" in data and data["argument"] is not None:
        arg = ShenlunArgumentSkeleton.model_validate(data.pop("argument"))
        m.argument_json = json.dumps(arg.model_dump(), ensure_ascii=False)
        m.argument_chain = _argument_summary(arg)
    if "templates" in data and data["templates"] is not None:
        templates = [ShenlunTemplateItem.model_validate(t) for t in data.pop("templates")]
        m.templates_json = json.dumps([t.model_dump() for t in templates], ensure_ascii=False)
        m.template_sentence = _templates_summary(templates)
    mapping = {
        "articleId": "article_id",
        "articleTitle": "article_title",
        "sourceExcerpt": "source_excerpt",
        "argumentChain": "argument_chain",
        "templateSentence": "template_sentence",
    }
    for k, v in data.items():
        setattr(m, mapping.get(k, k), v if v is not None else getattr(m, mapping.get(k, k)))
    db.commit()
    db.refresh(m)
    return _mine_to_out(m)


def delete_mine(db: Session, user: AppUser, mine_id: str) -> bool:
    m = db.get(ShenlunMineLog, mine_id)
    if not m or m.user_id != user.id:
        return False
    db.delete(m)
    db.commit()
    return True


def list_terms(
    db: Session, user: AppUser, status: str | None = None, category: str | None = None
) -> list[ShenlunNormTermOut]:
    q = db.query(ShenlunNormTerm).filter(ShenlunNormTerm.user_id == user.id)
    if status == "learning":
        q = q.filter(ShenlunNormTerm.mastered.is_(False))
    elif status == "mastered":
        q = q.filter(ShenlunNormTerm.mastered.is_(True))
    if category:
        q = q.filter(ShenlunNormTerm.category == category)
    rows = q.order_by(ShenlunNormTerm.mastered, ShenlunNormTerm.category, ShenlunNormTerm.created_at.desc()).all()
    return [_term_to_out(r) for r in rows]


def add_term(db: Session, user: AppUser, body: ShenlunNormTermAdd) -> ShenlunNormTermOut:
    raw = (body.term or "").strip()
    if not raw:
        raise ValueError("规范词不能为空")
    cat = (body.category or "其他").strip() or "其他"
    parts = [p.strip() for p in _TERM_SPLIT_RE.split(raw) if p.strip()] or [raw]
    last: ShenlunNormTerm | None = None
    for term in parts:
        existing = (
            db.query(ShenlunNormTerm)
            .filter(ShenlunNormTerm.user_id == user.id, ShenlunNormTerm.term == term)
            .first()
        )
        if existing:
            if body.usageNote:
                existing.usage_note = body.usageNote
            if body.exampleSentence:
                existing.example_sentence = body.exampleSentence
            if body.sourceTitle and not existing.source_title:
                existing.source_title = body.sourceTitle
            if body.articleId and not existing.article_id:
                existing.article_id = body.articleId
            existing.category = cat
            last = existing
            continue
        t = ShenlunNormTerm(
            id=gen_id("snt"),
            user_id=user.id,
            term=term,
            category=cat,
            usage_note=body.usageNote or "",
            source_title=body.sourceTitle or "",
            example_sentence=body.exampleSentence or "",
            article_id=body.articleId,
        )
        db.add(t)
        last = t
    db.commit()
    if last:
        db.refresh(last)
        return _term_to_out(last)
    raise ValueError("规范词不能为空")


def update_term(
    db: Session, user: AppUser, term_id: str, body: ShenlunNormTermUpdate
) -> ShenlunNormTermOut | None:
    t = db.get(ShenlunNormTerm, term_id)
    if not t or t.user_id != user.id:
        return None
    data = body.model_dump(exclude_unset=True)
    mapping = {
        "usageNote": "usage_note",
        "exampleSentence": "example_sentence",
        "sourceTitle": "source_title",
    }
    for k, v in data.items():
        if k == "category" and v:
            t.category = str(v).strip() or "其他"
            continue
        setattr(t, mapping.get(k, k), v)
    if "familiarity" in data and data["familiarity"] is not None:
        t.familiarity = max(1, min(5, int(data["familiarity"])))
    db.commit()
    db.refresh(t)
    return _term_to_out(t)


def delete_term(db: Session, user: AppUser, term_id: str) -> bool:
    t = db.get(ShenlunNormTerm, term_id)
    if not t or t.user_id != user.id:
        return False
    db.delete(t)
    db.commit()
    return True


def _drill_to_out(d: ShenlunDrillLog) -> ShenlunDrillLogOut:
    ids = _loads(d.ref_term_ids, [])
    if not isinstance(ids, list):
        ids = []
    return ShenlunDrillLogOut(
        id=d.id,
        drillType=d.drill_type,
        content=d.content or "",
        prompt=d.prompt or "",
        refMineId=d.ref_mine_id,
        refTermIds=[str(x) for x in ids],
        createdAt=d.created_at,
    )


def list_drills(db: Session, user: AppUser, drill_type: str | None = None) -> list[ShenlunDrillLogOut]:
    q = db.query(ShenlunDrillLog).filter(ShenlunDrillLog.user_id == user.id)
    if drill_type:
        q = q.filter(ShenlunDrillLog.drill_type == drill_type)
    rows = q.order_by(ShenlunDrillLog.created_at.desc()).limit(50).all()
    return [_drill_to_out(r) for r in rows]


def add_drill(db: Session, user: AppUser, body: ShenlunDrillCreate) -> ShenlunDrillLogOut:
    dtype = (body.drillType or "").strip()
    if dtype not in ("sentence", "imitate", "oral"):
        raise ValueError("drillType 必须是 sentence / imitate / oral")
    content = (body.content or "").strip()
    if len(content) < 10:
        raise ValueError("请至少写满约 10 个字（口述可写要点）")
    d = ShenlunDrillLog(
        id=gen_id("sdl"),
        user_id=user.id,
        drill_type=dtype,
        content=content,
        prompt=(body.prompt or "").strip(),
        ref_mine_id=body.refMineId,
        ref_term_ids=json.dumps(body.refTermIds or [], ensure_ascii=False),
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return _drill_to_out(d)


def get_stats(db: Session, user: AppUser) -> ShenlunStatsOut:
    today = today_str()
    d = now().date()
    monday = d - timedelta(days=d.weekday())
    week_start = monday.strftime("%Y-%m-%d")
    week_end = (monday + timedelta(days=6)).strftime("%Y-%m-%d")
    week_days = (
        db.query(ShenlunMineLog.mine_date)
        .filter(
            ShenlunMineLog.user_id == user.id,
            ShenlunMineLog.mine_date >= week_start,
            ShenlunMineLog.mine_date <= week_end,
        )
        .distinct()
        .count()
    )
    term_count = db.query(ShenlunNormTerm).filter(ShenlunNormTerm.user_id == user.id).count()
    learning = (
        db.query(ShenlunNormTerm)
        .filter(ShenlunNormTerm.user_id == user.id, ShenlunNormTerm.mastered.is_(False))
        .count()
    )
    today_mined = (
        db.query(ShenlunMineLog)
        .filter(ShenlunMineLog.user_id == user.id, ShenlunMineLog.mine_date == today)
        .first()
        is not None
    )
    week_start_dt = now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=d.weekday())
    if week_start_dt.tzinfo is not None:
        week_start_dt = week_start_dt.replace(tzinfo=None)
    week_drill = (
        db.query(ShenlunDrillLog)
        .filter(ShenlunDrillLog.user_id == user.id, ShenlunDrillLog.created_at >= week_start_dt)
        .count()
    )
    return ShenlunStatsOut(
        weekMineDays=week_days,
        weekMineTarget=7,
        termCount=term_count,
        learningTermCount=learning,
        todayMined=today_mined,
        weekDrillCount=week_drill,
    )
