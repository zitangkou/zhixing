"""微信公众号回复配置草稿、校验、发布版本与运行时读取。"""

from __future__ import annotations

import json
import re
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import WechatReplyConfiguration, WechatReplyRelease
from app.models.base import gen_id, utcnow
from app.schemas.wechat_reply import WechatReplyConfig
from app.services.wechat_official_service import (
    InboundMessage,
    decide_reply,
    default_reply_config,
    normalise_text,
)

CONFIG_ID = "default"
ALLOWED_TEMPLATE_TOKENS = {"today_url", "theory_url", "rmrb_url"}
TEMPLATE_TOKEN_RE = re.compile(r"\{\{([^{}]+)}}")


def _dump(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load(value: str | None, fallback: dict | None = None) -> dict:
    try:
        loaded = json.loads(value or "")
        if isinstance(loaded, dict):
            return loaded
    except (json.JSONDecodeError, TypeError):
        pass
    return fallback if fallback is not None else default_reply_config()


def validate_reply_config(config: dict) -> dict:
    """返回草稿发布前的结构问题和可读性提示。"""
    errors: list[str] = []
    warnings: list[str] = []
    for field, label in (
        ("welcomeReply", "关注回复"),
        ("fallbackReply", "兜底回复"),
        ("unsupportedMessageReply", "非文字消息回复"),
        ("unsupportedEventReply", "未支持事件回复"),
    ):
        if not str(config.get(field, "")).strip():
            errors.append(f"{label}不能为空")

    rules = config.get("keywordRules")
    if not isinstance(rules, list):
        return {"valid": False, "errors": errors + ["关键词规则格式无效"], "warnings": warnings}

    seen_ids: set[str] = set()
    seen_keywords: dict[str, tuple[str, str]] = {}
    for index, rule in enumerate(rules, start=1):
        rule_id = str(rule.get("id", "")).strip()
        rule_name = str(rule.get("name", "")).strip() or f"第{index}条规则"
        if not rule_id:
            errors.append(f"{rule_name}缺少规则 ID")
        elif rule_id in seen_ids:
            errors.append(f"规则 ID 重复：{rule_id}")
        seen_ids.add(rule_id)
        if not rule.get("enabled", True):
            continue
        keywords = rule.get("keywords") or []
        normalized_keywords = [normalise_text(str(item)) for item in keywords]
        normalized_keywords = [item for item in normalized_keywords if item]
        if not normalized_keywords:
            errors.append(f"启用中的规则“{rule_name}”至少需要一个关键词")
        if not str(rule.get("responseText", "")).strip():
            errors.append(f"启用中的规则“{rule_name}”回复内容不能为空")
        for keyword in set(normalized_keywords):
            previous = seen_keywords.get(keyword)
            if previous and previous[0] != rule_id:
                errors.append(
                    f"关键词“{keyword}”同时配置在“{previous[1]}”和“{rule_name}”中"
                )
            else:
                seen_keywords[keyword] = (rule_id, rule_name)
        if rule.get("matchType") == "contains":
            for keyword in normalized_keywords:
                for other, (other_id, other_name) in seen_keywords.items():
                    if other_id != rule_id and other != keyword and (keyword in other or other in keyword):
                        warnings.append(
                            f"包含匹配“{rule_name}”的关键词“{keyword}”与“{other_name}”的“{other}”有重叠；将按优先级和词长决定"
                        )

    template_texts = [
        str(config.get("welcomeReply", "")),
        str(config.get("fallbackReply", "")),
        str(config.get("unsupportedMessageReply", "")),
        str(config.get("unsupportedEventReply", "")),
        *(str(rule.get("responseText", "")) for rule in rules),
    ]
    for text in template_texts:
        for token in TEMPLATE_TOKEN_RE.findall(text):
            if token not in ALLOWED_TEMPLATE_TOKENS:
                errors.append(f"回复中使用了不支持的变量：{{{{{token}}}}}")
    if len(set(errors)) != len(errors):
        errors = list(dict.fromkeys(errors))
    if not rules:
        warnings.append("当前没有关键词规则，所有文字消息都会进入兜底回复")
    return {"valid": not errors, "errors": errors, "warnings": list(dict.fromkeys(warnings))}


def _new_release(
    db: Session,
    snapshot: dict,
    version: int,
    admin_id: int | None,
    admin_name: str,
    rollback_from_version: int | None = None,
) -> WechatReplyRelease:
    release = WechatReplyRelease(
        id=gen_id("wrr"),
        version=version,
        snapshot_json=_dump(snapshot),
        published_by_id=admin_id,
        published_by_name=admin_name or "",
        rollback_from_version=rollback_from_version,
        published_at=utcnow(),
    )
    db.add(release)
    db.flush()
    return release


def ensure_default_reply_configuration(db: Session) -> None:
    """首次启动时把历史固定回复迁成 v1；后续只补齐缺失的活动版本。"""
    state = db.get(WechatReplyConfiguration, CONFIG_ID)
    if state is None:
        defaults = default_reply_config()
        state = WechatReplyConfiguration(id=CONFIG_ID, draft_json=_dump(defaults))
        db.add(state)
        db.flush()

    if state.published_release_id and db.get(WechatReplyRelease, state.published_release_id):
        return

    snapshot = _load(state.draft_json, default_reply_config())
    latest_version = db.query(func.max(WechatReplyRelease.version)).scalar() or 0
    release = _new_release(db, snapshot, latest_version + 1, None, "系统默认")
    state.published_release_id = release.id
    if not state.draft_json:
        state.draft_json = _dump(snapshot)
    db.commit()


def _state_or_seed(db: Session) -> WechatReplyConfiguration:
    ensure_default_reply_configuration(db)
    state = db.get(WechatReplyConfiguration, CONFIG_ID)
    if state is None:
        raise RuntimeError("公众号回复配置初始化失败")
    return state


def _release_out(release: WechatReplyRelease, current_id: str | None) -> dict:
    return {
        "id": release.id,
        "version": release.version,
        "publishedByName": release.published_by_name,
        "rollbackFromVersion": release.rollback_from_version,
        "publishedAt": release.published_at,
        "isCurrent": release.id == current_id,
    }


def get_admin_reply_state(db: Session) -> dict:
    state = _state_or_seed(db)
    current = db.get(WechatReplyRelease, state.published_release_id) if state.published_release_id else None
    releases = db.query(WechatReplyRelease).order_by(WechatReplyRelease.version.desc()).limit(100).all()
    return {
        "draft": _load(state.draft_json, default_reply_config()),
        "active": _load(current.snapshot_json, default_reply_config()) if current else default_reply_config(),
        "activeReleaseId": current.id if current else None,
        "activeVersion": current.version if current else None,
        "updatedByName": state.updated_by_name,
        "updatedAt": state.updated_at,
        "releases": [_release_out(row, current.id if current else None) for row in releases],
    }


def save_reply_draft(db: Session, config: dict, admin_id: int | None, admin_name: str) -> dict:
    state = _state_or_seed(db)
    state.draft_json = _dump(config)
    state.updated_by_id = admin_id
    state.updated_by_name = admin_name
    state.updated_at = utcnow()
    db.commit()
    return get_admin_reply_state(db)


def publish_reply_draft(db: Session, admin_id: int | None, admin_name: str) -> dict:
    state = _state_or_seed(db)
    snapshot = _load(state.draft_json, default_reply_config())
    validation = validate_reply_config(snapshot)
    if not validation["valid"]:
        raise ValueError("；".join(validation["errors"]))
    latest_version = db.query(func.max(WechatReplyRelease.version)).scalar() or 0
    release = _new_release(db, snapshot, latest_version + 1, admin_id, admin_name)
    state.published_release_id = release.id
    state.updated_by_id = admin_id
    state.updated_by_name = admin_name
    state.updated_at = utcnow()
    db.commit()
    return get_admin_reply_state(db)


def rollback_reply_release(
    db: Session,
    release_id: str,
    admin_id: int | None,
    admin_name: str,
) -> dict:
    target = db.get(WechatReplyRelease, release_id)
    if target is None:
        raise ValueError("找不到要回退的发布版本")
    snapshot = _load(target.snapshot_json, default_reply_config())
    validation = validate_reply_config(snapshot)
    if not validation["valid"]:
        raise ValueError("目标版本无法发布：" + "；".join(validation["errors"]))
    state = _state_or_seed(db)
    latest_version = db.query(func.max(WechatReplyRelease.version)).scalar() or 0
    release = _new_release(
        db,
        snapshot,
        latest_version + 1,
        admin_id,
        admin_name,
        rollback_from_version=target.version,
    )
    state.published_release_id = release.id
    state.updated_by_id = admin_id
    state.updated_by_name = admin_name
    state.updated_at = utcnow()
    db.commit()
    return get_admin_reply_state(db)


def load_active_reply_config(db: Session) -> tuple[dict, str]:
    state = db.get(WechatReplyConfiguration, CONFIG_ID)
    if state is None or not state.published_release_id:
        return default_reply_config(), "default"
    release = db.get(WechatReplyRelease, state.published_release_id)
    if release is None:
        return default_reply_config(), "default"
    return _load(release.snapshot_json, default_reply_config()), release.id


def preview_reply(config: dict, message: str, msg_type: str, event: str, public_base_url: str) -> dict:
    inbound = InboundMessage(
        to_user="preview",
        from_user="preview",
        create_time=datetime.now().isoformat(),
        msg_type=msg_type,
        content=message,
        event=event,
    )
    decision = decide_reply(inbound, public_base_url, config)
    return {
        "intent": decision.intent,
        "reply": decision.text,
        "matchedRuleId": decision.matched_rule_id,
    }
