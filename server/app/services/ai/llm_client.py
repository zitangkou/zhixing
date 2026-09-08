"""DeepSeek / OpenAI 兼容 LLM 客户端"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import get_settings


class LlmError(Exception):
    pass


def chat_json(system: str, user: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.llm_enabled:
        raise LlmError("AI 出题未启用，请在 server/.env 设置 LLM_ENABLED=true")
    if not settings.llm_api_key:
        raise LlmError("未配置 LLM_API_KEY")

    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            resp = client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as e:
        raise LlmError("LLM 请求超时") from e
    except httpx.HTTPError as e:
        raise LlmError(f"LLM 网络错误: {e}") from e

    if resp.status_code >= 400:
        raise LlmError(f"LLM 返回 {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LlmError(f"LLM 响应格式异常: {data}") from e

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise LlmError(f"LLM 返回非 JSON: {content[:500]}") from e
