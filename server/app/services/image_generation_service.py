"""Image edit adapters. Provider credentials and prompt templates stay server-side."""

from __future__ import annotations

import base64
import io
import re
import time
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.product import ProductContext
from app.services.image_model_service import image_model_secret, resolve_image_model
from app.services.image_style_service import get_image_style_config
from app.upload_paths import DATA_DIR, detect_image_ext

MAX_INPUT_BYTES = 8 * 1024 * 1024
RESULTS_DIR = DATA_DIR / "private" / "image-results"


class ImageProviderHTTPError(Exception):
    """Sanitized provider failure metadata; never includes request or response bodies."""

    def __init__(self, stage: str, status_code: int, provider_code: str = ""):
        self.stage = stage
        self.status_code = status_code
        self.provider_code = provider_code
        suffix = f" ({provider_code})" if provider_code else ""
        super().__init__(f"{stage} HTTP {status_code}{suffix}")


def _raise_for_image_response(response: httpx.Response, stage: str) -> None:
    if response.is_success:
        return
    provider_code = ""
    try:
        payload = response.json()
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        raw_code = error.get("code") if isinstance(error, dict) else ""
        if not raw_code and isinstance(payload, dict):
            raw_code = payload.get("code", "")
        provider_code = re.sub(r"[^A-Za-z0-9_.-]", "", str(raw_code))[:40]
    except (ValueError, TypeError):
        pass
    raise ImageProviderHTTPError(stage, response.status_code, provider_code)


def _style_for_generation(db: Session, style_id: str, product: ProductContext, allow_draft: bool = False) -> dict[str, Any]:
    style = next((item for item in get_image_style_config(db)["items"] if item["id"] == style_id), None)
    allowed_status = {"active", "draft"} if allow_draft else {"active"}
    if not style or style["status"] not in allowed_status or style["productKey"] not in (product.key, "*"):
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
        _raise_for_image_response(response, "DashScope 图片生成接口")
        data = response.json()
        content = data["output"]["choices"][0]["message"]["content"]
        image_url = next((item.get("image") for item in content if item.get("type") == "image" and item.get("image")), None)
        if not image_url:
            raise ValueError("模型返回中没有找到生成图片")
        image_response = client.get(image_url)
        _raise_for_image_response(image_response, "DashScope 结果图片下载")
        return image_response.content


def _image_from_openai_compatible(model: dict[str, Any], api_key: str, raw: bytes, mime: str, prompt: str, negative: str, style: dict[str, Any]) -> bytes:
    url = f"{model['baseUrl'].rstrip('/')}/images/edits"
    full_prompt = prompt + (f"\nNegative prompt: {negative}" if negative else "")
    params = {"model": model["model"], "prompt": full_prompt, **model.get("parameters", {}), **style.get("providerParameters", {}), "n": 1}
    with httpx.Client(timeout=model["timeoutSeconds"]) as client:
        response = client.post(url, data=params, files={"image": (f"input.{mime.split('/')[-1]}", io.BytesIO(raw), mime)}, headers={"Authorization": f"Bearer {api_key}"})
        _raise_for_image_response(response, "图像编辑接口")
        data = response.json()["data"][0]
        if data.get("b64_json"):
            return base64.b64decode(data["b64_json"])
        if data.get("url"):
            result = client.get(data["url"])
            _raise_for_image_response(result, "模型结果图片下载")
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
        _raise_for_image_response(response, "火山方舟图片生成接口")
        data = response.json().get("data", [])
        image_url = next((item.get("url") for item in data if item.get("url")), None)
        if not image_url:
            raise ValueError("模型返回中没有找到生成图片")
        image_response = client.get(image_url)
        _raise_for_image_response(image_response, "火山方舟结果图片下载")
        return image_response.content


def _image_from_gemini(model: dict[str, Any], api_key: str, raw: bytes, mime: str, prompt: str, negative: str, style: dict[str, Any]) -> bytes:
    """Google Gemini native image-edit API."""
    full_prompt = prompt + (f"\n请避免出现：{negative}" if negative else "")
    parameters = {**model.get("parameters", {}), **style.get("providerParameters", {})}
    generation_config = {key: value for key, value in parameters.items() if key in {"responseModalities", "imageConfig", "temperature", "topP", "topK", "candidateCount"}}
    payload = {
        "contents": [{"parts": [
            {"text": full_prompt[:12000]},
            {"inlineData": {"mimeType": mime, "data": base64.b64encode(raw).decode("ascii")}},
        ]}],
        "generationConfig": generation_config,
    }
    url = f"{model['baseUrl'].rstrip('/')}/models/{model['model']}:generateContent"
    with httpx.Client(timeout=model["timeoutSeconds"]) as client:
        response = client.post(url, json=payload, headers={"x-goog-api-key": api_key})
        _raise_for_image_response(response, "Google Gemini 图片生成接口")
        data = response.json()
        candidates = data.get("candidates", [])
        for candidate in candidates:
            parts = candidate.get("content", {}).get("parts", [])
            for part in parts:
                inline_data = part.get("inlineData") or part.get("inline_data") or {}
                encoded = inline_data.get("data")
                if encoded:
                    return base64.b64decode(encoded)
        raise ValueError("Google Gemini 返回中没有找到生成图片")


def _image_from_tokenhub(model: dict[str, Any], api_key: str, raw: bytes, mime: str, prompt: str, negative: str, style: dict[str, Any]) -> bytes:
    """Tencent TokenHub Hy image editing API."""
    full_prompt = prompt + (f"\n请避免出现：{negative}" if negative else "")
    parameters = {**model.get("parameters", {}), **style.get("providerParameters", {})}
    payload = {
        "model": model["model"],
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": full_prompt[:12000]},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"}},
        ]}],
        **parameters,
    }
    with httpx.Client(timeout=model["timeoutSeconds"]) as client:
        response = client.post(model["baseUrl"], json=payload, headers={"Authorization": f"Bearer {api_key}"})
        _raise_for_image_response(response, "腾讯云 TokenHub 图片生成接口")
        data = response.json()
        image_url = (((data.get("choices") or [{}])[0].get("delta") or {}).get("image") or {}).get("url")
        if not image_url:
            raise ValueError("腾讯云 TokenHub 返回中没有找到生成图片")
        image_response = client.get(image_url)
        _raise_for_image_response(image_response, "腾讯云 TokenHub 结果图片下载")
        return image_response.content


def _image_from_bfl(model: dict[str, Any], api_key: str, raw: bytes, mime: str, prompt: str, negative: str, style: dict[str, Any]) -> bytes:
    """Black Forest Labs FLUX.2 async generation/edit API."""
    full_prompt = prompt + (f"\nAvoid: {negative}" if negative else "")
    parameters = {**model.get("parameters", {}), **style.get("providerParameters", {})}
    payload = {
        "prompt": full_prompt[:12000],
        "input_image": base64.b64encode(raw).decode("ascii"),
        **parameters,
    }
    base_url = model["baseUrl"].rstrip("/")
    with httpx.Client(timeout=model["timeoutSeconds"]) as client:
        response = client.post(f"{base_url}/v1/{model['model']}", json=payload, headers={"x-key": api_key})
        _raise_for_image_response(response, "Black Forest Labs FLUX 图片生成接口")
        task = response.json()
        task_id = task.get("id")
        polling_url = task.get("polling_url") or (f"{base_url}/v1/get_result?id={task_id}" if task_id else "")
        parsed_poll = urlparse(polling_url)
        if not task_id or parsed_poll.scheme != "https" or parsed_poll.hostname != urlparse(base_url).hostname:
            raise ValueError("FLUX 服务未返回有效的任务查询地址")

        deadline = time.monotonic() + model["timeoutSeconds"]
        while time.monotonic() < deadline:
            poll_response = client.get(polling_url, headers={"x-key": api_key, "accept": "application/json"})
            _raise_for_image_response(poll_response, "Black Forest Labs FLUX 任务查询")
            result = poll_response.json()
            status = result.get("status")
            if status == "Ready":
                image_url = (result.get("result") or {}).get("sample")
                if not image_url:
                    raise ValueError("FLUX 任务完成，但没有返回生成图片地址")
                image_response = client.get(image_url)
                _raise_for_image_response(image_response, "Black Forest Labs FLUX 结果图片下载")
                return image_response.content
            if status in {"Error", "Request Moderated", "Content Moderated", "Task not found"}:
                safe_status = re.sub(r"[^A-Za-z0-9 _-]", "", str(status))[:40]
                raise ValueError(f"FLUX 任务未成功：{safe_status or '服务商处理失败'}")
            time.sleep(1)
        raise TimeoutError("FLUX 图片生成超时，请在服务商任务状态中确认结果")


def generate_style_image(
    db: Session,
    product: ProductContext,
    style_id: str,
    raw: bytes,
    mime: str,
    owner_id: str,
    allow_draft: bool = False,
) -> str:
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("图片不能超过 8 MB")
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError("仅支持 JPG、PNG、WEBP 图片")
    style = _style_for_generation(db, style_id, product, allow_draft=allow_draft)
    model = resolve_image_model(db, style.get("modelId", ""))
    if not model.get("supportsImageEdit"):
        raise ValueError("所选模型不支持图片编辑")
    api_key = image_model_secret(model)
    prompt = _build_prompt(style)
    if model["provider"] == "dashscope":
        result = _image_from_dashscope(model, api_key, raw, mime, prompt, style.get("negativePrompt", ""), style)
    elif model["provider"] == "volcengine":
        result = _image_from_volcengine(model, api_key, raw, mime, prompt, style.get("negativePrompt", ""), style)
    elif model["provider"] == "gemini":
        result = _image_from_gemini(model, api_key, raw, mime, prompt, style.get("negativePrompt", ""), style)
    elif model["provider"] == "tokenhub":
        result = _image_from_tokenhub(model, api_key, raw, mime, prompt, style.get("negativePrompt", ""), style)
    elif model["provider"] == "bfl":
        result = _image_from_bfl(model, api_key, raw, mime, prompt, style.get("negativePrompt", ""), style)
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
