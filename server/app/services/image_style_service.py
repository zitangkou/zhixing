"""Versioned image style presets stored in the shared system settings table."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import SystemSetting
from app.schemas.image_style import ImageStylePreset

SETTING_KEY = "image_style_presets"
SETTING_DESC = "AI 图片处理风格预设（JSON 配置，由图片风格管理维护）"
CONFIG_SCHEMA_VERSION = 1

TRAVEL_WATERCOLOR_STYLE: dict[str, Any] = {
    "id": "travel-journal-watercolor",
    "slug": "travel-journal-watercolor",
    "name": "旅行手账·清透淡彩",
    "category": "image-to-image",
    "productKey": "general",
    "description": "将旅行与日常风景照片转为轻盈、低饱和的水彩手账插画，保留原图主要场景与构图。",
    "status": "active",
    "version": "1.0.0",
    "sortOrder": 10,
    "promptTemplate": "将输入照片转绘为清透、克制的旅行手账淡彩插画。把原图作为场景蓝图，保留主要主体的身份、数量、形状、相对位置、比例、视角和原始画幅；不新增、删除、替换或移动主要物体。根据原图内容使用少量细淡的灰色铅笔或钢笔线勾勒关键轮廓，背景和次要细节概括为松散的色块，不逐一描画窗格、砖纹或细小栏杆。使用大面积轻薄透明的水彩晕染，保留充足纸白和柔和边缘。颜色跟随原图的自然冷暖关系，不统一套暖黄或复古滤镜；整体低饱和、低反差。场景重点：{{scene_description}}。画面安静、轻盈，像旅行手账中的淡彩写生。",
    "negativePrompt": "不要改变原图主要主体、构图、视角和画幅；不要新增、删除、替换、复制或移动人物、建筑、交通工具、动物、标识等主体；不要添加文字、标题、标签、水印、签名、边框、贴纸或装饰；避免照片写实、动漫漫画、矢量硬边、浓重油画、密集排线、黑色粗轮廓、过度描绘窗格砖纹、强纸纹、强暗角、高饱和、整体泛黄或过强对比。",
    "rules": {
      "subjectPreservation": {
        "priority": "strict",
        "mustPreserve": ["主体身份与数量", "主体轮廓", "相对位置与比例", "视角与地平线", "原图画幅与主要构图"],
        "allowSimplification": ["远景建筑细节", "窗格与砖纹", "细小栏杆", "树叶与石块纹理"],
        "noInventedObjects": True,
      },
      "rendering": {
        "medium": "透明水彩淡彩写生",
        "linework": "少量、细淡的灰色铅笔或钢笔关键轮廓",
        "detailLevel": "低；次要细节概括为松散色块",
        "wash": "轻薄、透明、柔和晕染",
        "paper": "纸白充足，纸纹极轻，不画纸边框",
      },
      "color": {
        "policy": "跟随原图自然冷暖，不统一色偏",
        "saturation": "低",
        "contrast": "低",
        "preserveSceneLight": True,
        "avoidGlobalSepia": True,
      },
      "composition": {"preserveAspectRatio": True, "crop": "none", "edgeTreatment": "柔和淡出但不添加画框"},
      "prohibitedAdditions": ["新主体", "文字与水印", "边框与贴纸", "与原图无关的装饰"],
    },
    "controls": {
      "subjectPreservation": "strict",
      "compositionPreservation": "high",
      "styleIntensity": "low-to-medium",
      "detailSimplification": "high",
      "linework": "minimal",
      "watercolorWash": "light",
      "paperTexture": "subtle",
      "colorTreatment": "source-adaptive",
      "contrast": "low",
      "aspectRatio": "source",
    },
    "providerParameters": {},
    "maintainerNotes": "基于 4 张风景照片的多轮视觉测试整理。风格强度与规则为跨模型语义控制；providerParameters 留空，待确定实际图像模型后填写该服务支持的数值参数。生成模型仍可能偏离主体保留要求，发布前需用代表性样图复核。",
}


def _default_config() -> dict[str, Any]:
    return {"schemaVersion": CONFIG_SCHEMA_VERSION, "items": [TRAVEL_WATERCOLOR_STYLE.copy()]}


def ensure_image_style_setting(db: Session) -> SystemSetting:
    row = db.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY).first()
    if row is None:
        row = SystemSetting(
            key=SETTING_KEY,
            value=json.dumps(_default_config(), ensure_ascii=False),
            description=SETTING_DESC,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_image_style_config(db: Session) -> dict[str, Any]:
    row = ensure_image_style_setting(db)
    try:
        data = json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        data = _default_config()
    if not isinstance(data, dict):
        data = _default_config()
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    valid_items: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            valid_items.append(ImageStylePreset.model_validate(item).model_dump())
        except Exception:
            continue
    return {"schemaVersion": CONFIG_SCHEMA_VERSION, "items": valid_items}


def save_image_style_config(db: Session, items: list[dict[str, Any]]) -> dict[str, Any]:
    row = ensure_image_style_setting(db)
    normalized = [ImageStylePreset.model_validate(item).model_dump() for item in items]
    from app.services.image_model_service import get_image_model_config

    model_config = get_image_model_config(db)
    models = {item["id"]: item for item in model_config["items"]}
    for style in normalized:
        if style["modelId"]:
            model = models.get(style["modelId"])
            if not model:
                raise ValueError(f"风格 {style['name']} 指定的模型不存在")
            if style["status"] == "active" and (not model["enabled"] or not model["credentialConfigured"]):
                raise ValueError(f"启用风格 {style['name']} 前，请先启用其指定模型并配置服务器凭据")
    row.value = json.dumps({"schemaVersion": CONFIG_SCHEMA_VERSION, "items": normalized}, ensure_ascii=False)
    row.description = SETTING_DESC
    db.commit()
    return {"schemaVersion": CONFIG_SCHEMA_VERSION, "items": normalized}


def parse_image_style_markdown(markdown: str) -> dict[str, Any]:
    """Read the machine-readable JSON fence from a human-authored Markdown file."""
    lines = markdown.lstrip("\ufeff").splitlines()
    payload_lines: list[str] = []
    in_block = False
    found = False
    closed = False
    for line in lines:
        stripped = line.strip()
        if not in_block and re.fullmatch(r"```image-style-json\s*", stripped):
            if found:
                raise ValueError("Markdown 中只能包含一个 image-style-json 配置块")
            in_block = True
            found = True
            continue
        if in_block and stripped == "```":
            in_block = False
            closed = True
            continue
        if in_block:
            payload_lines.append(line)
    if not found or in_block or not closed:
        raise ValueError("未找到完整的 ```image-style-json 配置块，请按导入模板整理 Markdown")
    try:
        data = json.loads("\n".join(payload_lines))
    except json.JSONDecodeError as exc:
        raise ValueError(f"配置 JSON 格式错误：第 {exc.lineno} 行，第 {exc.colno} 列") from exc
    if not isinstance(data, dict):
        raise ValueError("配置数据必须是 JSON 对象")
    try:
        return ImageStylePreset.model_validate(data).model_dump()
    except Exception as exc:
        errors = getattr(exc, "errors", lambda: [])()
        details = "；".join(
            f"{'.'.join(str(part) for part in error.get('loc', [])) or '配置'}：{error.get('msg', '格式无效')}"
            for error in errors
        )
        raise ValueError(details or "风格配置字段校验失败") from exc


def image_style_conflict(items: list[dict[str, Any]], style: dict[str, Any]) -> str:
    for item in items:
        if item["id"] == style["id"]:
            return f"风格 ID {style['id']} 已存在"
        if item["slug"] == style["slug"]:
            return f"风格标识 {style['slug']} 已存在"
    return ""


def list_public_image_styles(db: Session, product_key: str) -> list[dict[str, Any]]:
    items = get_image_style_config(db)["items"]
    from app.services.image_model_service import get_image_model_config

    model_config = get_image_model_config(db)
    available_models = {item["id"] for item in model_config["items"] if item["enabled"] and item["credentialConfigured"]}
    return sorted(
        [
            item for item in items
            if item["status"] == "active"
            and item["productKey"] in (product_key, "*")
            and (item.get("modelId") or model_config["defaultModelId"]) in available_models
        ],
        key=lambda item: (item["sortOrder"], item["name"]),
    )
