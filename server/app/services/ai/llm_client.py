"""DeepSeek / OpenAI 兼容 LLM 客户端；用量日志只存调用元数据。"""
from __future__ import annotations
import json
from time import perf_counter
from typing import Any
import httpx
from app.config import get_settings
from app.services.ai.llm_usage_service import record_usage

class LlmError(Exception):
    pass

def chat_json(system: str, user: str, *, purpose: str = 'general') -> dict[str, Any]:
    settings = get_settings()
    model=settings.llm_model
    started=perf_counter(); usage={}; recorded=False
    def log(status, code=''):
        nonlocal recorded
        if recorded:return
        record_usage(purpose=purpose,model=model,status=status,usage=usage,
                     duration_ms=(perf_counter()-started)*1000,error_code=code)
        recorded=True
    try:
        if not settings.llm_enabled:
            log('failed','disabled')
            raise LlmError('AI 出题未启用，请在 server/.env 设置 LLM_ENABLED=true')
        if not settings.llm_api_key:
            log('failed','missing_api_key')
            raise LlmError('未配置 LLM_API_KEY')
        url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"}, "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as e:
            log('failed','timeout'); raise LlmError('LLM 请求超时') from e
        except httpx.HTTPError as e:
            log('failed','network_error'); raise LlmError(f'LLM 网络错误: {e}') from e
        try:
            data=resp.json()
            if isinstance(data,dict) and isinstance(data.get('usage'),dict):usage=data['usage']
        except ValueError:
            data={}
        if resp.status_code >= 400:
            log('failed',f'http_{resp.status_code}')
            raise LlmError(f'LLM 返回 {resp.status_code}: {resp.text[:500]}')
        try:
            content=data['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError) as e:
            log('failed','response_format')
            raise LlmError('LLM 响应格式异常') from e
        try:
            result=json.loads(content)
        except (json.JSONDecodeError,TypeError) as e:
            log('failed','invalid_json')
            raise LlmError('LLM 返回非 JSON') from e
        if not isinstance(result,dict):
            log('failed','json_not_object')
            raise LlmError('LLM 返回的 JSON 顶层必须为对象')
        log('success')
        return result
    except LlmError:
        if not recorded:log('failed','llm_error')
        raise
    except Exception as e:
        if not recorded:log('failed','unexpected_error')
        raise
