"""统一学习入口解析与跨渠道归因事件。"""

from __future__ import annotations

import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ContentPublishPackage, EntryAttributionEvent, gen_id
from app.services.content_ops_service import list_publishable_targets
from app.timezone import now

CHANNEL_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
CAMPAIGN_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{5,63}$")
SCENE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _loads(raw: str) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _append_query(path: str, values: dict[str, str]) -> str:
    if not path:
        return path
    parts = urlsplit(path)
    if parts.fragment and "?" in parts.fragment:
        route, raw_query = parts.fragment.split("?", 1)
        query = dict(parse_qsl(raw_query))
        query.update({key: value for key, value in values.items() if value})
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, f"{route}?{urlencode(query)}"))
    query = dict(parse_qsl(parts.query))
    query.update({key: value for key, value in values.items() if value})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _fallback(product_key: str, code: str, message: str) -> dict:
    root = "/theory/" if product_key == "theory" else "/shenlun/"
    return {
        "valid": False,
        "reasonCode": code,
        "message": message,
        "target": {"h5Path": root, "miniappPath": "pages/today/index"},
        "attribution": {
            "product": product_key, "channel": "direct", "campaign": "",
            "content": "", "entry": "", "section": "", "scene": "",
        },
    }


def _published_packages(db: Session, product_key: str) -> list[ContentPublishPackage]:
    return db.query(ContentPublishPackage).filter(
        ContentPublishPackage.product_key == product_key,
        ContentPublishPackage.status == "published",
    ).order_by(ContentPublishPackage.published_at.desc()).limit(500).all()


def _package_for_scene(db: Session, product_key: str, scene: str) -> ContentPublishPackage | None:
    return next(
        (row for row in _published_packages(db, product_key) if _loads(row.entry_target_json).get("qrScene") == scene),
        None,
    )


def _package_for_campaign(
    db: Session, product_key: str, campaign: str, entry: str, content: str,
) -> ContentPublishPackage | None:
    for row in _published_packages(db, product_key):
        if row.campaign_key != campaign:
            continue
        target = _loads(row.entry_target_json)
        if entry and target.get("entryId") != entry:
            continue
        if content and row.source_id != content:
            continue
        if row.planned_at and row.planned_at > now().replace(tzinfo=None):
            continue
        return row
    return None


def _validate_section(product_key: str, target: dict, section: str) -> tuple[bool, dict[str, str]]:
    if not section:
        return True, {}
    if product_key == "shenlun":
        return (section in {"article", "example", "practice"}, {"section": section})
    if section in {"focus", "full"}:
        return True, {"view": section}
    if section == "all":
        return bool(target.get("collectionEnabled")), {"scope": "all"}
    number = section.removeprefix("part-")
    valid_parts = {str(item.get("number")) for item in target.get("parts", [])}
    return number in valid_parts, {"scope": number}


def resolve_entry(
    db: Session,
    product_key: str,
    *,
    product: str = "",
    entry: str = "",
    section: str = "",
    channel: str = "direct",
    campaign: str = "",
    content: str = "",
    scene: str = "",
) -> dict:
    """解析入口；所有失败均返回同产品安全首页，避免渠道链接串线。"""
    product = product.strip().lower()
    entry, section = entry.strip(), section.strip().lower()
    channel = channel.strip().lower() or "direct"
    campaign, content, scene = campaign.strip(), content.strip(), scene.strip()
    if product and product != product_key:
        return _fallback(product_key, "product_mismatch", "这个入口属于另一学习产品，请从当前首页重新选择内容。")
    if not CHANNEL_PATTERN.fullmatch(channel):
        return _fallback(product_key, "invalid_channel", "渠道参数无法识别，已返回当前产品首页。")
    if campaign and not CAMPAIGN_PATTERN.fullmatch(campaign):
        return _fallback(product_key, "invalid_campaign", "活动入口已失效，已返回当前产品首页。")
    if scene and not SCENE_PATTERN.fullmatch(scene):
        return _fallback(product_key, "invalid_scene", "小程序码参数无法识别，已返回当前产品首页。")

    package = None
    if scene:
        package = _package_for_scene(db, product_key, scene)
        if not package:
            return _fallback(product_key, "scene_unavailable", "这个小程序码对应的内容已下线或尚未发布。")
        package_target = _loads(package.entry_target_json)
        scene_entry = str(package_target.get("entryId") or "")
        if entry and entry != scene_entry:
            return _fallback(product_key, "entry_mismatch", "入口内容不一致，已返回当前产品首页。")
        entry, content, campaign = scene_entry, package.source_id, package.campaign_key
    elif campaign:
        package = _package_for_campaign(db, product_key, campaign, entry, content)
        if not package:
            return _fallback(product_key, "campaign_unavailable", "这项学习活动已结束或尚未发布。")
        package_target = _loads(package.entry_target_json)
        entry = entry or str(package_target.get("entryId") or "")
        content = content or package.source_id

    resolved = next((item for item in list_publishable_targets(db, product_key) if item["entryId"] == entry), None)
    if not resolved:
        return _fallback(product_key, "entry_unavailable", "学习内容已下线、过期或尚未开放。")
    if content and content != resolved["sourceId"]:
        return _fallback(product_key, "content_mismatch", "内容与学习入口不一致，已返回当前产品首页。")
    if package:
        package_target = _loads(package.entry_target_json)
        if package_target.get("topicType") not in resolved.get("topicTypes", []):
            return _fallback(product_key, "topic_unavailable", "当前内容类型已不再开放。")

    section_ok, section_query = _validate_section(product_key, resolved, section)
    if not section_ok:
        return _fallback(product_key, "section_unavailable", "指定的学习分辑或内容区段尚未开放。")
    attribution = {
        "product": product_key, "channel": channel, "campaign": campaign,
        "content": resolved["sourceId"], "entry": resolved["entryId"],
        "section": section, "scene": scene,
    }
    query = {**attribution, **section_query}
    return {
        "valid": True,
        "reasonCode": "ok",
        "message": "入口可用",
        "target": {
            "title": resolved["title"],
            "topicTypes": resolved["topicTypes"],
            "h5Path": _append_query(resolved["h5Path"], query),
            "miniappPath": _append_query(resolved["miniappPath"], query),
        },
        "attribution": attribution,
    }


def record_entry_event(db: Session, product_key: str, body, user_id: str | None = None) -> dict:
    resolved = resolve_entry(
        db, product_key, product=product_key, entry=body.entry, section=body.section,
        channel=body.channel, campaign=body.campaign, content=body.content, scene=body.scene,
    )
    if not resolved["valid"]:
        raise ValueError(resolved["message"])
    attribution = resolved["attribution"]
    row = EntryAttributionEvent(
        id=gen_id("eae"), client_event_id=body.clientEventId, visitor_id=body.visitorId,
        user_id=user_id, product_key=product_key, event_type=body.eventType,
        entry_id=attribution["entry"], content_id=attribution["content"], section=attribution["section"],
        channel=attribution["channel"], campaign_key=attribution["campaign"],
        platform=body.platform, scene=attribution["scene"],
        payload_json=json.dumps(body.payload, ensure_ascii=False, separators=(",", ":")),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(EntryAttributionEvent).filter(
            EntryAttributionEvent.client_event_id == body.clientEventId,
        ).first()
        if existing:
            return {"recorded": False, "duplicate": True, "eventId": existing.id}
        raise
    return {"recorded": True, "duplicate": False, "eventId": row.id}
