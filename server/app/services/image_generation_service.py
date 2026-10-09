"""Image edit adapters. Provider credentials and prompt templates stay server-side."""

from __future__ import annotations

import base64
import io
import re
import time
import uuid
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.product import ProductContext
from app.services.image_model_service import image_model_secret, resolve_image_model
from app.services.image_style_service import get_image_style_config
from app.upload_paths import DATA_DIR, detect_image_ext

MAX_INPUT_BYTES = 8 * 1024 * 1024
RESULTS_DIR = DATA_DIR / "private" / "image-results"


def _style_for_generation(db: Session, style_id: str, product: ProductContext) -> dict[str, Any]:
    style = next((item for item in get_image_style_config(db)["items"] if item["id"] == style_id), None)
    if not style or style["status"] != "active" or style["productKey"] not in (product.key, "*"):
        raise ValueError("该图片风格当前不可用")
    return style


def _build_prompt(style: dict[str, Any], scene_description: str = "以原图中的实际场景为准") -> str:
    prompt = style.get("promptTemplate", "").replace("{{scene_description}}", scene_description)
    rules = style.get("rules") or {}
    preservation = rules.get("subjectPreservation", {}) if isinstance(rules, dict) else {}
    if preservation.get("priority") == "strict" and "保留原图" not in prompt:
        prompt += "严格保留原图的主要主体、数量和相对构图，不增删主体。"
    return prompt.strip()


def _image_from_dashscope(model: dict[str, Any], api_key: str, raw: bytes, mime: str, prompt: str, negative: str, style: dict[str, Any]) -> bytes:
    url = f"{model['baseUrl'].rstrip('/')}/services/aigc/multimodal-generation/generation"
    parameters = {"enable_interleave": False, "size": "1K", **model.get("parameters", {}), **style.get("providerParameters", {}), "n": 1}
    if negative:
        parameters["negative_prompt"] = negative[:500]
    payload = {
        "model": model["model"],
        "input": {"messages": [{"role": "user", "content": [
            {"text": prompt[:2000]},
            {"image": f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"},
        ]}]},
        "parameters": parameters,
    }
    with httpx.Client(timeout=model["timeoutSeconds"]) as client:
        response = client.post(url, json=payload, headers={"Authorization": f"Bearer {api_key}"})
        response.raise_for_status()
        data = response.json()
        content = data["output"]["choices"][0]["message"]["content"]
        image_url = next((item.get("image") for item in content if item.get("type") == "image" and item.get("image")), None)
        if not image_url:
            raise ValueError("模型返回中没有找到生成图片")
        image_response = client.get(image_url)
        image_response.raise_for_status()
        return image_response.content


def _image_from_openai_compatible(model: dict[str, Any], api_key: str, raw: bytes, mime: str, prompt: str, negative: str, style: dict[str, Any]) -> bytes:
    url = f"{model['baseUrl'].rstrip('/')}/images/edits"
    full_prompt = prompt + (f"\nNegative prompt: {negative}" if negative else "")
    params = {"model": model["model"], "prompt": full_prompt, **model.get("parameters", {}), **style.get("providerParameters", {}), "n": 1}
    with httpx.Client(timeout=model["timeoutSeconds"]) as client:
        response = client.post(url, data=params, files={"image": (f"input.{mime.split('/')[-1]}", io.BytesIO(raw), mime)}, headers={"Authorization": f"Bearer {api_key}"})
        response.raise_for_status()
        data = response.json()["data"][0]
        if data.get("b64_json"):
            return base64.b64decode(data["b64_json"])
        if data.get("url"):
            result = client.get(data["url"])
            result.raise_for_status()
            return result.content
        raise ValueError("模型返回中没有找到生成图片")


def _image_from_volcengine(model: dict[str, Any], api_key: str, raw: bytes, mime: str, prompt: str, negative: str, style: dict[str, Any]) -> bytes:
    """Volcengine Ark Seedream image generation/edit API."""
    full_prompt = prompt + (f"\n请避免出现：{negative}" if negative else "")
    payload = {
        "model": model["model"],
        "prompt": full_prompt[:12000],
        "image": f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}",
        "response_format": "url",
        **model.get("parameters", {}),
        **style.get("providerParameters", {}),
    }
    with httpx.Client(timeout=model["timeoutSeconds"]) as client:
        response = client.post(
            f"{model['baseUrl'].rstrip('/')}/images/generations",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        image_url = next((item.get("url") for item in data if item.get("url")), None)
        if not image_url:
            raise ValueError("模型返回中没有找到生成图片")
        image_response = client.get(image_url)
        image_response.raise_for_status()
        return image_response.content


def generate_style_image(db: Session, product: ProductContext, style_id: str, raw: bytes, mime: str, owner_id: str) -> str:
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("图片不能超过 8 MB")
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError("仅支持 JPG、PNG、WEBP 图片")
    style = _style_for_generation(db, style_id, product)
    model = resolve_image_model(db, style.get("modelId", ""))
    if not model.get("supportsImageEdit"):
        raise ValueError("所选模型不支持图片编辑")
    api_key = image_model_secret(model)
    prompt = _build_prompt(style)
    if model["provider"] == "dashscope":
        result = _image_from_dashscope(model, api_key, raw, mime, prompt, style.get("negativePrompt", ""), style)
    elif model["provider"] == "volcengine":
        result = _image_from_volcengine(model, api_key, raw, mime, prompt, style.get("negativePrompt", ""), style)
    elif model["provider"] == "openai-compatible":
        result = _image_from_openai_compatible(model, api_key, raw, mime, prompt, style.get("negativePrompt", ""), style)
    else:
        raise ValueError("当前服务商适配器尚未实现")
    if not result or len(result) > 20 * 1024 * 1024:
        raise ValueError("模型生成结果为空或超过 20 MB")
    result_id = uuid.uuid4().hex
    safe_owner = re.sub(r"[^A-Za-z0-9_-]", "_", owner_id)[:80]
    owner_dir = RESULTS_DIR / safe_owner
    owner_dir.mkdir(parents=True, exist_ok=True)
    for old_file in owner_dir.iterdir():
        try:
            if old_file.is_file() and old_file.stat().st_mtime < time.time() - 24 * 60 * 60:
                old_file.unlink(missing_ok=True)
        except OSError:
            pass
    ext = detect_image_ext("", "", result)
    if ext not in {".png", ".jpg", ".webp"}:
        raise ValueError("模型生成了不支持的图片格式")
    result_path = owner_dir / f"{result_id}{ext}"
    result_path.write_bytes(result)
    result_path.chmod(0o600)
    return result_id


def cleanup_expired_image_results() -> None:
    if not RESULTS_DIR.exists():
        return
    cutoff = time.time() - 24 * 60 * 60
    for owner_dir in RESULTS_DIR.iterdir():
        if not owner_dir.is_dir():
            continue
        for path in owner_dir.iterdir():
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                continue
        try:
            owner_dir.rmdir()
        except OSError:
            pass
