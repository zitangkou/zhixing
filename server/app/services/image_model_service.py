"""Configurable image-model registry; credentials stay in server environment."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import SystemSetting
from app.schemas.image_style import ImageModelConfig, ImageModelConfigOut
from app.config import get_settings

SETTING_KEY = "image_model_registry"
SETTING_DESC = "图片模型配置（密钥通过服务器环境变量注入）"


def _read_raw(db: Session) -> dict[str, Any]:
    row = db.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY).first()
    if not row:
        return {"schemaVersion": 1, "defaultModelId": "", "items": []}
    try:
        value = json.loads(row.value)
    except (TypeError, json.JSONDecodeError):
        return {"schemaVersion": 1, "defaultModelId": "", "items": []}
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        return {"schemaVersion": 1, "defaultModelId": "", "items": []}
    return value


def _credential_configured(item: dict[str, Any]) -> bool:
    name = str(item.get("credentialEnv") or "").strip()
    key_field = {"DASHSCOPE_API_KEY": "dashscope_api_key", "ARK_API_KEY": "ark_api_key", "OPENAI_IMAGE_API_KEY": "openai_image_api_key", "GEMINI_API_KEY": "gemini_api_key", "TENCENT_TOKENHUB_API_KEY": "tencent_tokenhub_api_key", "BFL_API_KEY": "bfl_api_key"}.get(name)
    return bool(key_field and getattr(get_settings(), key_field, "").strip())


def get_image_model_config(db: Session) -> dict[str, Any]:
    raw = _read_raw(db)
    items: list[dict[str, Any]] = []
    for item in raw["items"]:
        try:
            normalized = ImageModelConfig.model_validate(item).model_dump()
        except Exception:
            continue
        normalized["credentialConfigured"] = _credential_configured(normalized)
        items.append(normalized)
    default_id = str(raw.get("defaultModelId") or "")
    if not any(x["id"] == default_id and x["enabled"] and x["credentialConfigured"] for x in items):
        default_id = ""
    for item in items:
        item["isDefault"] = item["id"] == default_id
    return {"schemaVersion": 1, "defaultModelId": default_id, "items": items}


def save_image_model_config(db: Session, items: list[ImageModelConfig]) -> dict[str, Any]:
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("模型 ID 不能重复")
    defaults = [item for item in items if item.isDefault]
    if len(defaults) > 1:
        raise ValueError("只能设置一个默认模型")
    for item in items:
        expected_env = {"dashscope": "DASHSCOPE_API_KEY", "volcengine": "ARK_API_KEY", "gemini": "GEMINI_API_KEY", "tokenhub": "TENCENT_TOKENHUB_API_KEY", "bfl": "BFL_API_KEY", "openai-compatible": "OPENAI_IMAGE_API_KEY"}[item.provider]
        if item.credentialEnv != expected_env:
            raise ValueError(f"{item.provider} 服务商必须使用凭据环境变量 {expected_env}")
        parsed = urlparse(item.baseUrl)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"模型 {item.name} 的 API 地址必须使用 HTTPS")
        if item.isDefault and not item.enabled:
            raise ValueError("默认模型必须处于启用状态")
        if item.enabled and not _credential_configured(item.model_dump()):
            raise ValueError(f"启用模型 {item.name} 前，请先在服务器环境中配置 {item.credentialEnv or '模型凭据环境变量'}")
    default_id = defaults[0].id if defaults else ""
    row = db.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY).first()
    value = {"schemaVersion": 1, "defaultModelId": default_id, "items": [x.model_dump(exclude={"credentialConfigured"}) for x in items]}
    if row is None:
        row = SystemSetting(key=SETTING_KEY, value=json.dumps(value, ensure_ascii=False), description=SETTING_DESC)
        db.add(row)
    else:
        row.value = json.dumps(value, ensure_ascii=False)
        row.description = SETTING_DESC
    db.commit()
    return get_image_model_config(db)


def resolve_image_model(db: Session, model_id: str = "") -> dict[str, Any]:
    config = get_image_model_config(db)
    selected_id = model_id or config["defaultModelId"]
    selected = next((x for x in config["items"] if x["id"] == selected_id), None)
    if not selected:
        raise ValueError("未配置默认图片模型，请先在后台启用并设置默认模型")
    if not selected["enabled"]:
        raise ValueError("所选图片模型已停用")
    if not selected["credentialConfigured"]:
        raise ValueError(f"模型凭据未配置：请在服务器环境中设置 {selected['credentialEnv']}")
    return selected


def image_model_secret(model: dict[str, Any]) -> str:
    field = {"DASHSCOPE_API_KEY": "dashscope_api_key", "ARK_API_KEY": "ark_api_key", "OPENAI_IMAGE_API_KEY": "openai_image_api_key", "GEMINI_API_KEY": "gemini_api_key", "TENCENT_TOKENHUB_API_KEY": "tencent_tokenhub_api_key", "BFL_API_KEY": "bfl_api_key"}.get(model.get("credentialEnv", ""))
    return str(getattr(get_settings(), field, "") or "") if field else ""
