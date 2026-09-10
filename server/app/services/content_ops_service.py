"""模板化账号运营：固定栏目、跨平台发布包与双审核状态。"""
import json
import re
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from sqlalchemy.orm import Session
from app.models import (
    Article,
    ContentOperationTemplate,
    ContentPublishPackage,
    ContentReviewRecord,
    RmrbArticle,
    ShenlunTeachingExample,
    gen_id,
)
from app.schemas import ContentPackageGenerateFromArticle, ContentPublishPackageCreate, ContentPublishPackageUpdate
from app.services.shenlun_learning_service import teaching_example_out
from app.services.theory_learning_entry_service import list_public_entries
from app.timezone import now

CHANNELS = ["wechat", "xiaohongshu", "zhihu", "wechat_channels"]
SUPPORTED_CHANNELS = [*CHANNELS, "douyin", "bilibili"]
REFERENCE_LIBRARY_PATH = Path(__file__).resolve().parents[2] / "data" / "content_ops" / "people_daily_library.json"
DEFAULT_TEMPLATES = [
    ("shenlun_three_cut", "shenlun", "三刀拆解", ["标题", "原文", "骨架", "规范表达", "迁移练习"]),
    ("shenlun_expression", "shenlun", "规范表达", ["普通说法", "规范表达", "适用场景", "例句"]),
    ("shenlun_challenge", "shenlun", "找点挑战", ["材料", "任务", "参考要点", "易漏点"]),
    ("shenlun_clinic", "shenlun", "失分诊所", ["问题作答", "失分原因", "修改过程", "改后答案"]),
    ("theory_current", "theory", "时政考点", ["事实", "规范表述", "考法", "原文依据"]),
    ("theory_confusion", "theory", "易混辨析", ["表述A", "表述B", "差异", "依据"]),
    ("theory_option", "theory", "真题选项", ["题干", "选项", "干扰方式", "原文依据"]),
    ("theory_source", "theory", "重要原文怎么考", ["原文", "关键词", "命题角度", "练习题"]),
    ("wechat_daily_pack", "general", "公众号今日学习包", ["导语", "申论学习任务", "时政学习任务", "小程序入口"]),
    ("wechat_weekly_review", "general", "公众号一周学习复盘", ["本周主题", "高频错因", "表达清单", "下周任务"]),
]

TRANSITIONS = {
    "draft": {"teaching_review"},
    "teaching_review": {"ops_review", "rejected"},
    "ops_review": {"ready", "rejected"},
    "ready": {"published", "rejected"},
    "rejected": {"draft"},
    "published": set(),
}

REVIEW_CHECKLISTS = {
    "teaching": [
        {"key": "facts_accurate", "label": "事实、原文、答案、解析和方法准确"},
        {"key": "qualifiers_complete", "label": "主体、范围、程度和条件无遗漏"},
        {"key": "exercise_assessable", "label": "练习具有明确评价标准"},
    ],
    "operations": [
        {"key": "opening_clear", "label": "开头清楚且无夸张承诺"},
        {"key": "platform_fit", "label": "信息密度和节奏适合目标平台"},
        {"key": "visuals_ready", "label": "封面、卡片或镜头素材需求齐全"},
        {"key": "cta_verified", "label": "每个渠道只有一个 CTA 且深链可核验"},
        {"key": "compliance_checked", "label": "敏感、侵权和夸张表达已检查"},
    ],
}


def content_review_config() -> dict:
    return {
        "stages": [
            {"key": "teaching", "label": "教研审核", "checklist": REVIEW_CHECKLISTS["teaching"]},
            {"key": "operations", "label": "运营审核", "checklist": REVIEW_CHECKLISTS["operations"]},
        ]
    }


def content_reference_library() -> dict:
    try:
        return json.loads(REFERENCE_LIBRARY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"人民日报运营参考库不可用: {exc}") from exc


def _loads(raw: str, fallback):
    try:
        return json.loads(raw or "")
    except (json.JSONDecodeError, TypeError):
        return fallback


def ensure_content_ops_defaults(db: Session) -> None:
    for order, (code, product, name, slots) in enumerate(DEFAULT_TEMPLATES):
        existing = db.query(ContentOperationTemplate).filter(ContentOperationTemplate.code == code).first()
        if existing:
            if code == "wechat_daily_pack":
                for package in db.query(ContentPublishPackage).filter(ContentPublishPackage.template_id == existing.id).all():
                    values = _loads(package.slot_values_json, {})
                    if "政治理论任务" in values and "时政学习任务" not in values:
                        values["时政学习任务"] = values.pop("政治理论任务")
                        package.slot_values_json = json.dumps(values, ensure_ascii=False)
            existing.name = name
            existing.slots_json = json.dumps(slots, ensure_ascii=False)
            existing.channels_json = json.dumps(CHANNELS, ensure_ascii=False)
            existing.sort_order = order
            continue
        db.add(ContentOperationTemplate(
            id=gen_id("cot"), code=code, product_key=product, name=name,
            description="由审核后的教学母资产派生，发布前需完成教研与运营双审核",
            slots_json=json.dumps(slots, ensure_ascii=False),
            channels_json=json.dumps(CHANNELS, ensure_ascii=False), sort_order=order,
        ))
    db.commit()


def template_out(row: ContentOperationTemplate) -> dict:
    return {"id": row.id, "code": row.code, "productKey": row.product_key, "name": row.name,
            "description": row.description, "slots": _loads(row.slots_json, []),
            "channels": _loads(row.channels_json, []), "sortOrder": row.sort_order, "status": row.status}


def review_record_out(row: ContentReviewRecord) -> dict:
    return {
        "id": row.id,
        "stage": row.stage,
        "decision": row.decision,
        "checklist": _loads(row.checklist_json, {}),
        "note": row.note,
        "reviewerId": row.reviewer_id,
        "reviewerUsername": row.reviewer_username,
        "reviewerName": row.reviewer_name,
        "createdAt": row.created_at,
    }


def package_out(row: ContentPublishPackage) -> dict:
    return {"id": row.id, "productKey": row.product_key, "templateId": row.template_id,
            "sourceType": row.source_type, "sourceId": row.source_id, "sourceTitle": row.source_title,
            "campaignKey": row.campaign_key, "deepLink": row.deep_link,
            "entryTarget": _loads(row.entry_target_json, {}),
            "slotValues": _loads(row.slot_values_json, {}),
            "variants": _loads(row.variants_json, {}), "reviewNote": row.review_note,
            "reviewHistory": [review_record_out(item) for item in row.review_records], "status": row.status,
            "plannedAt": row.planned_at, "publishedAt": row.published_at,
            "createdAt": row.created_at, "updatedAt": row.updated_at}


def create_package(db: Session, body: ContentPublishPackageCreate) -> dict:
    template = db.get(ContentOperationTemplate, body.templateId)
    if not template or template.status != "enabled":
        raise ValueError("运营模板不存在或未启用")
    if template.product_key not in (body.productKey, "general"):
        raise ValueError("模板与产品不匹配")
    unknown = set(body.variants) - set(_loads(template.channels_json, []))
    if unknown:
        raise ValueError(f"模板不支持渠道: {', '.join(sorted(unknown))}")
    unknown_slots = set(body.slotValues) - set(_loads(template.slots_json, []))
    if unknown_slots:
        raise ValueError(f"模板不存在槽位: {', '.join(sorted(unknown_slots))}")
    target = body.entryTarget.model_dump()
    variants = _with_tracked_links(body.variants, target, body.campaignKey, body.sourceId, body.productKey)
    row = ContentPublishPackage(
        id=gen_id("cpp"), product_key=body.productKey, template_id=template.id,
        source_type=body.sourceType, source_id=body.sourceId, source_title=body.sourceTitle,
        campaign_key=body.campaignKey, deep_link=body.deepLink,
        entry_target_json=json.dumps(body.entryTarget.model_dump(), ensure_ascii=False),
        slot_values_json=json.dumps(body.slotValues, ensure_ascii=False),
        variants_json=json.dumps(variants, ensure_ascii=False), planned_at=body.plannedAt,
    )
    db.add(row); db.commit(); db.refresh(row)
    return package_out(row)


def _plain_text(value: str, limit: int) -> str:
    text = re.sub(r"[#>*_`\[\]()]", " ", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _article_slot_values(article: Article | RmrbArticle, slots: list[str]) -> dict[str, str]:
    summary = _plain_text(article.summary or article.content, 360)
    excerpt = _plain_text(article.content or article.summary, 1200)
    evidence = " · ".join(part for part in (article.source, article.publish_date, article.title) if part)
    deterministic = {
        "标题": article.title,
        "原文": excerpt,
        "材料": excerpt,
        "短材料": excerpt,
        "事实": summary,
        "事件": summary,
        "日期": article.publish_date,
        "主体": article.source,
        "规范表述": summary,
        "原文依据": evidence,
        "依据": evidence,
        "导语": summary,
        "本周主题": article.title,
        "关键词": "、".join(_loads(article.tags, [])[:6]),
        "骨架": "背景与问题 → 原因或影响 → 对策与落实 → 价值升华（规则草稿，需教研结合原文核对）",
        "规范表达": summary,
        "迁移练习": "请用不超过120字概括材料反映的核心问题与主要解决思路。",
        "普通说法": "事情要做好、问题要解决",
        "适用场景": "归纳概括、提出对策和文章写作中的措施表达",
        "例句": summary,
        "任务": "圈出不同主体及其关键动作，合并同类要点后分层作答。",
        "参考要点": summary,
        "易漏点": "主体、限定条件、因果关系与并列层次（需教研核对）",
        "问题作答": summary,
        "失分原因": "对象不清、要点遗漏、层次混乱或表述不规范",
        "修改过程": "补对象 → 找动作 → 合并同类项 → 改写为规范短句",
        "改后答案": summary,
        "考法": "重点辨析主体、范围、程度和因果关系，可改写为判断或单选题。",
        "命题角度": "关键词原义、主体边界、程度变化与因果倒置",
        "练习题": f"判断：材料关于“{article.title}”的表述可以脱离原文限定条件理解。",
        "表述A": summary,
        "表述B": f"对“{article.title}”作扩大范围或改变程度的表述",
        "差异": "核对主体、范围、程度和条件是否与原文一致。",
        "题干": f"下列关于“{article.title}”的表述，符合原文的是：",
        "选项": "依据原文设计一个正确项和三个主体/范围/程度干扰项（需教研补齐）",
        "干扰方式": "主体偷换、范围扩大、程度变化、因果倒置",
    }
    return {slot: deterministic.get(slot, "") for slot in slots}


def _tracked_link(base: str, channel: str, tracking: dict[str, str] | None = None) -> str:
    if not base:
        return base
    parts = urlsplit(base)
    if parts.fragment and "?" in parts.fragment:
        route, fragment_query = parts.fragment.split("?", 1)
        additions = {"channel": channel, **(tracking or {})}
        query = [(key, value) for key, value in parse_qsl(fragment_query) if key not in additions]
        query.extend(additions.items())
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, f"{route}?{urlencode(query)}"))
    additions = {"channel": channel, **(tracking or {})}
    query = [(key, value) for key, value in parse_qsl(parts.query) if key not in additions]
    query.extend(additions.items())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _with_tracked_links(variants: dict, target: dict, campaign: str, source_id: str, product: str) -> dict:
    tracking = {"campaign": campaign, "content": source_id, "product": product, "entry": str(target.get("entryId") or "")}
    tracking = {key: value for key, value in tracking.items() if value}
    base = str(target.get("h5Path") or "")
    return {
        channel: {**content, "ctaLink": _tracked_link(base, channel, tracking) if base else content.get("ctaLink", "")}
        for channel, content in variants.items()
    }


def _article_variants(article: Article | RmrbArticle, template: ContentOperationTemplate, slots: dict[str, str], deep_link: str, tracking: dict[str, str]) -> dict:
    filled = [f"{name}：{value}" for name, value in slots.items() if value]
    missing = [name for name, value in slots.items() if not value]
    core = "\n\n".join(filled)
    missing_note = f"\n\n待教研补充：{'、'.join(missing)}" if missing else ""
    titles = {
        "xiaohongshu": f"{template.name}｜{article.title}",
        "douyin": f"{article.title}，考试会怎么考？",
        "bilibili": f"{template.name}：{article.title}",
        "wechat": f"今日学习｜{article.title}",
        "zhihu": f"如何系统学习《{article.title}》？",
        "wechat_channels": f"一分钟学习｜{article.title}",
    }
    prefixes = {
        "xiaohongshu": "先收藏，再用一个考点框架读懂这篇材料。",
        "douyin": "这条内容用一分钟讲清一个可迁移的考试知识点。",
        "bilibili": "本期从原文、考点和迁移练习三个层次展开。",
        "wechat": "今天用一篇已审核文章完成一次结构化学习。",
        "zhihu": "这篇内容从原文依据、常见误区和迁移练习三个层次展开。",
        "wechat_channels": "用一个问题讲清这篇文章最值得掌握的知识点。",
    }
    return {
        channel: {
            "title": titles[channel][:80],
            "body": f"{prefixes[channel]}\n\n{core}{missing_note}",
            "ctaLink": _tracked_link(deep_link, channel, tracking),
            "generatedDraft": True,
        }
        for channel in _loads(template.channels_json, [])
    }


def generate_package_from_article(db: Session, body: ContentPackageGenerateFromArticle) -> dict:
    article: Article | RmrbArticle | None = None
    source_type = "article"
    if body.productKey == "shenlun":
        article = db.get(RmrbArticle, body.articleId)
        source_type = "rmrb_article"
    if not article:
        article = db.get(Article, body.articleId)
        source_type = "article"
    published = bool(article and article.is_published and (not isinstance(article, Article) or article.status == "published"))
    if not published:
        raise ValueError("只有已发布文章可以生成运营发布包")
    template = db.get(ContentOperationTemplate, body.templateId)
    if not template or template.status != "enabled":
        raise ValueError("运营模板不存在或未启用")
    if template.product_key not in (body.productKey, "general"):
        raise ValueError("模板与产品不匹配")
    # Daily production can legitimately reuse an approved teaching asset on a
    # later day.  The campaign key identifies that daily run, so only block an
    # exact same-source, same-template, same-campaign retry.
    duplicate_query = db.query(ContentPublishPackage).filter(
        ContentPublishPackage.source_id == article.id,
        ContentPublishPackage.template_id == template.id,
        ContentPublishPackage.status != "rejected",
    )
    if body.campaignKey:
        duplicate_query = duplicate_query.filter(ContentPublishPackage.campaign_key == body.campaignKey)
    else:
        duplicate_query = duplicate_query.filter(ContentPublishPackage.campaign_key == "")
    duplicate = duplicate_query.first()
    if duplicate:
        raise ValueError("该文章已用此模板生成发布包，请直接编辑已有草稿")
    slots = _article_slot_values(article, _loads(template.slots_json, []))
    target = body.entryTarget.model_dump()
    deep_link = target.get("h5Path") or body.deepLink
    tracking = {"campaign": body.campaignKey, "content": article.id, "product": body.productKey, "entry": target.get("entryId", "")}
    tracking = {key: value for key, value in tracking.items() if value}
    variants = _article_variants(article, template, slots, deep_link, tracking)
    return create_package(db, ContentPublishPackageCreate(
        productKey=body.productKey,
        templateId=template.id,
        sourceType=source_type,
        sourceId=article.id,
        sourceTitle=article.title,
        campaignKey=body.campaignKey,
        deepLink=deep_link,
        entryTarget=body.entryTarget,
        slotValues=slots,
        variants=variants,
        plannedAt=body.plannedAt,
    ))


def list_publishable_targets(db: Session, product_key: str) -> list[dict]:
    """只返回当前真正可访问的学习入口，供运营绑定而非手写路径。"""
    if product_key not in ("general", "theory", "shenlun"):
        raise ValueError("产品不存在")
    output: list[dict] = []
    if product_key in ("theory", "general"):
        for entry in list_public_entries(db):
            article_id = entry["articleId"]
            output.append({
                "entryId": article_id,
                "sourceId": article_id,
                "sourceType": "article",
                "title": entry["title"],
                "publishDate": entry["publishDate"],
                "topicTypes": [item for item, field in (("daily", "isDaily"), ("evergreen", "isEvergreen")) if entry[field]],
                "h5Path": f"/#/pages/article/detail?id={article_id}",
                "miniappPath": f"pages/article/detail?id={article_id}",
                "officialAccountKeyword": "时政",
            })
    if product_key in ("shenlun", "general"):
        rows = db.query(ShenlunTeachingExample, RmrbArticle).join(
            RmrbArticle, RmrbArticle.id == ShenlunTeachingExample.article_id,
        ).filter(
            ShenlunTeachingExample.status == "published",
            RmrbArticle.is_published.is_(True),
        ).order_by(RmrbArticle.sort_order.desc(), RmrbArticle.publish_date.desc()).all()
        seen = set()
        for example, article in rows:
            if article.id in seen or not teaching_example_out(example):
                continue
            seen.add(article.id)
            output.append({
                "entryId": article.id,
                "sourceId": article.id,
                "sourceType": "rmrb_article",
                "title": article.title,
                "publishDate": article.publish_date,
                "topicTypes": ["daily", "review"],
                "h5Path": f"/#/pages/rmrb/article-detail?id={article.id}",
                "miniappPath": f"pages/rmrb/article-detail?id={article.id}",
                "officialAccountKeyword": "时评",
            })
    return output


def _preflight_item(key: str, label: str, passed: bool, message: str, level: str = "error") -> dict:
    return {"key": key, "label": label, "passed": passed, "level": level, "message": message}


def package_preflight(db: Session, row: ContentPublishPackage) -> dict:
    """发布前确定性校验；失败项会阻止待发布和导出。"""
    target = _loads(row.entry_target_json, {})
    variants = _loads(row.variants_json, {})
    checks = []
    campaign_ok = bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{5,63}", row.campaign_key or ""))
    checks.append(_preflight_item("campaign", "活动标识", campaign_ok, "使用 6～64 位小写字母、数字和连字符"))
    planned_ok = row.planned_at is not None
    checks.append(_preflight_item("schedule", "发布时间", planned_ok, "设置计划发布时间，便于逐平台排期"))

    target_id = str(target.get("entryId") or "").strip()
    eligible = {item["entryId"]: item for item in list_publishable_targets(db, row.product_key)}
    entry_ok = target_id in eligible
    checks.append(_preflight_item("entry", "学习入口", entry_ok, "选择当前已审核并公开可用的同产品学习入口"))
    resolved = eligible.get(target_id)
    source_ok = bool(resolved and resolved["sourceId"] == row.source_id and resolved["sourceType"] == row.source_type)
    checks.append(_preflight_item("source", "母内容一致", source_ok, "发布包母内容必须与学习入口使用同一已审核资产"))

    expected_h5 = resolved["h5Path"] if resolved else ""
    expected_miniapp = resolved["miniappPath"] if resolved else ""
    h5_ok = bool(expected_h5 and target.get("h5Path") == expected_h5)
    miniapp_ok = bool(expected_miniapp and target.get("miniappPath") == expected_miniapp)
    checks.append(_preflight_item("h5_path", "H5 入口", h5_ok, "使用系统生成的对应内容 H5 路径"))
    checks.append(_preflight_item("miniapp_path", "小程序入口", miniapp_ok, "使用系统生成的对应内容小程序路径"))
    qr_scene = str(target.get("qrScene") or "").strip()
    checks.append(_preflight_item("qr_scene", "小程序码场景", bool(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", qr_scene)), "填写只含字母、数字、下划线或连字符的场景值"))
    keyword = str(target.get("officialAccountKeyword") or "").strip()
    checks.append(_preflight_item("keyword", "公众号承接词", keyword in ("今日", "时政", "时评", "申论"), "使用今日、时政、时评或申论"))

    channels_ok = bool(variants)
    checks.append(_preflight_item("channels", "渠道内容", channels_ok, "至少选择一个渠道"))
    incomplete = []
    bad_copy = []
    forbidden = ("待审核", "待教研补充", "TODO", "保证上岸", "100%命中", "政治理论")
    for channel, content in variants.items():
        if channel not in SUPPORTED_CHANNELS or not str(content.get("title") or "").strip() or not str(content.get("body") or "").strip():
            incomplete.append(channel)
        copy = f"{content.get('title', '')}\n{content.get('body', '')}"
        if any(term in copy for term in forbidden):
            bad_copy.append(channel)
    checks.append(_preflight_item("variant_complete", "标题与正文", not incomplete, f"补齐渠道标题和正文：{', '.join(incomplete)}" if incomplete else "各渠道标题和正文完整"))
    checks.append(_preflight_item("copy_compliance", "运营表述", not bad_copy, f"清理待办、夸大或不必要敏感称呼：{', '.join(bad_copy)}" if bad_copy else "未发现首发阻断词"))

    cta_bad = []
    for channel, content in variants.items():
        expected = _tracked_link(expected_h5, channel, {
            "campaign": row.campaign_key,
            "content": row.source_id,
            "product": row.product_key,
            "entry": target_id,
        }) if expected_h5 else ""
        if content.get("ctaLink") != expected:
            cta_bad.append(channel)
    checks.append(_preflight_item("cta", "唯一可追踪入口", not cta_bad and bool(variants), f"重新生成渠道入口：{', '.join(cta_bad)}" if cta_bad else "每个渠道使用唯一且可归因的同主题入口"))

    topic_ok = target.get("topicType") in ((resolved or {}).get("topicTypes") or [])
    checks.append(_preflight_item("topic_type", "内容时效类型", topic_ok, "内容类型必须与入口的今日／长期重点／复习属性一致"))
    errors = [item for item in checks if not item["passed"] and item["level"] == "error"]
    return {"passed": not errors, "checks": checks, "errorCount": len(errors), "warningCount": 0, "resolvedEntry": resolved}


def get_package_preflight(db: Session, package_id: str) -> dict:
    row = db.get(ContentPublishPackage, package_id)
    if not row:
        raise ValueError("发布包不存在")
    return package_preflight(db, row)


def _require_preflight(db: Session, row: ContentPublishPackage) -> dict:
    result = package_preflight(db, row)
    if not result["passed"]:
        labels = "、".join(item["label"] for item in result["checks"] if not item["passed"])
        raise ValueError(f"发布前检查未通过: {labels}")
    return result


def _validate_review_checklist(stage: str, checklist: dict[str, bool]) -> None:
    required = {item["key"] for item in REVIEW_CHECKLISTS[stage]}
    missing = sorted(key for key in required if checklist.get(key) is not True)
    if missing:
        labels = {item["key"]: item["label"] for item in REVIEW_CHECKLISTS[stage]}
        raise ValueError(f"请完成{('教研' if stage == 'teaching' else '运营')}审核清单: {', '.join(labels[key] for key in missing)}")


def _record_review(db: Session, row: ContentPublishPackage, stage: str, decision: str, checklist: dict[str, bool], note: str, reviewer) -> None:
    db.add(ContentReviewRecord(
        id=gen_id("crr"), package_id=row.id, stage=stage, decision=decision,
        checklist_json=json.dumps(checklist, ensure_ascii=False), note=note,
        reviewer_id=getattr(reviewer, "id", None),
        reviewer_username=getattr(reviewer, "username", ""),
        reviewer_name=getattr(reviewer, "nickname", "") or getattr(reviewer, "username", ""),
    ))


def transition_package(db: Session, package_id: str, target: str, note: str = "", checklist: dict[str, bool] | None = None, reviewer=None) -> dict:
    row = db.get(ContentPublishPackage, package_id)
    if not row:
        raise ValueError("发布包不存在")
    if target not in TRANSITIONS.get(row.status, set()):
        raise ValueError(f"发布包状态 {row.status} 不能变更为 {target}")
    if target == "teaching_review":
        template = db.get(ContentOperationTemplate, row.template_id)
        values = _loads(row.slot_values_json, {})
        missing = [slot for slot in _loads(template.slots_json, []) if not str(values.get(slot, "")).strip()]
        if missing:
            raise ValueError(f"请先补齐模板槽位: {', '.join(missing)}")
    checklist = checklist or {}
    clean_note = note.strip()
    if row.status == "teaching_review" and target == "ops_review":
        if not clean_note:
            raise ValueError("教研审核意见不能为空")
        _validate_review_checklist("teaching", checklist)
        _record_review(db, row, "teaching", "approved", checklist, clean_note, reviewer)
    elif row.status == "ops_review" and target == "ready":
        if not clean_note:
            raise ValueError("运营审核意见不能为空")
        _validate_review_checklist("operations", checklist)
        _require_preflight(db, row)
        _record_review(db, row, "operations", "approved", checklist, clean_note, reviewer)
    elif target == "rejected":
        if not clean_note:
            raise ValueError("驳回原因不能为空")
        stage = "teaching" if row.status == "teaching_review" else "operations"
        _record_review(db, row, stage, "rejected", checklist, clean_note, reviewer)
    elif target == "published":
        _require_preflight(db, row)
    row.status = target; row.review_note = clean_note
    if target == "published": row.published_at = now()
    db.commit(); db.refresh(row)
    return package_out(row)


def update_package(db: Session, package_id: str, body: ContentPublishPackageUpdate) -> dict:
    row = db.get(ContentPublishPackage, package_id)
    if not row:
        raise ValueError("发布包不存在")
    if row.status not in ("draft", "rejected"):
        raise ValueError("只有草稿或已驳回发布包可以编辑")
    data = body.model_dump(exclude_unset=True)
    mapping = {"sourceTitle": "source_title", "campaignKey": "campaign_key", "deepLink": "deep_link", "plannedAt": "planned_at"}
    if "slotValues" in data:
        template = db.get(ContentOperationTemplate, row.template_id)
        slot_values = data.pop("slotValues") or {}
        unknown = set(slot_values) - set(_loads(template.slots_json, []))
        if unknown: raise ValueError(f"模板不存在槽位: {', '.join(sorted(unknown))}")
        row.slot_values_json = json.dumps(slot_values, ensure_ascii=False)
    if "variants" in data:
        template = db.get(ContentOperationTemplate, row.template_id)
        unknown = set(data.pop("variants") or {}) - set(SUPPORTED_CHANNELS)
        if unknown: raise ValueError(f"模板不支持渠道: {', '.join(sorted(unknown))}")
        row.variants_json = json.dumps(body.variants or {}, ensure_ascii=False)
    if "entryTarget" in data:
        data.pop("entryTarget")
        row.entry_target_json = json.dumps(body.entryTarget.model_dump() if body.entryTarget else {}, ensure_ascii=False)
    for key, value in data.items(): setattr(row, mapping.get(key, key), value)
    variants = _loads(row.variants_json, {})
    target = _loads(row.entry_target_json, {})
    row.variants_json = json.dumps(_with_tracked_links(variants, target, row.campaign_key, row.source_id, row.product_key), ensure_ascii=False)
    db.commit(); db.refresh(row)
    return package_out(row)


def export_package(db: Session, package_id: str) -> dict:
    row = db.get(ContentPublishPackage, package_id)
    if not row:
        raise ValueError("发布包不存在")
    if row.status not in ("ready", "published"):
        raise ValueError("只有待发布或已发布的发布包可以导出")
    preflight = _require_preflight(db, row)
    template = db.get(ContentOperationTemplate, row.template_id)
    variants = _loads(row.variants_json, {})
    return {
        "schemaVersion": "content-publish-package/v2",
        "generatedAt": now(),
        "template": template_out(template),
        "package": package_out(row),
        "entryTarget": _loads(row.entry_target_json, {}),
        "preflight": preflight,
        "channels": [
            {
                "channel": channel,
                "content": content,
                "deepLink": content.get("ctaLink") or row.deep_link,
                "plannedAt": row.planned_at,
                "manualPublishRequired": True,
            }
            for channel, content in variants.items()
        ],
        "checklist": ["核对标题与正文", "核对事实和原文依据", "核对 H5 与小程序路径", "核对小程序码场景值", "人工发布后回填已发布状态"],
    }


def content_ops_overview(db: Session, days: int = 7) -> dict:
    current = now().replace(tzinfo=None)
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=days)
    rows = db.query(ContentPublishPackage).all()
    scheduled = [row for row in rows if row.planned_at and start <= row.planned_at < end]
    status_counts = {status: 0 for status in TRANSITIONS}
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
    product_mix = {
        product: sum(1 for row in scheduled if row.product_key == product)
        for product in ("shenlun", "theory")
    }
    unplanned_drafts = sum(1 for row in rows if row.status in ("draft", "rejected") and not row.planned_at)
    review_backlog = status_counts.get("teaching_review", 0) + status_counts.get("ops_review", 0)
    ready_inventory = status_counts.get("ready", 0)
    alerts = []
    missing_products = [label for product, label in (("shenlun", "申论学习"), ("theory", "时政学习")) if product_mix[product] == 0]
    if missing_products:
        alerts.append({"level": "warning", "code": "product_mix_empty", "message": f"未来{days}天未安排{'、'.join(missing_products)}内容"})
    if ready_inventory == 0:
        alerts.append({"level": "warning", "code": "ready_empty", "message": "暂无待发布库存，请优先完成审核"})
    if unplanned_drafts:
        alerts.append({"level": "info", "code": "draft_unplanned", "message": f"{unplanned_drafts} 个草稿尚未排期"})
    if review_backlog >= 10:
        alerts.append({"level": "warning", "code": "review_backlog", "message": f"{review_backlog} 个发布包正在等待审核"})
    return {
        "windowDays": days,
        "windowStart": start,
        "windowEnd": end,
        "scheduledCount": len(scheduled),
        "readyInventory": ready_inventory,
        "reviewBacklog": review_backlog,
        "unplannedDrafts": unplanned_drafts,
        "productMix": product_mix,
        "statusCounts": status_counts,
        "alerts": alerts,
        "healthy": not any(item["level"] == "warning" for item in alerts),
    }
