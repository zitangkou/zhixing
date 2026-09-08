"""杜衡阁微信公众号服务器回调。"""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.services.wechat_official_service import (
    build_text_reply,
    decide_reply_once,
    parse_message,
    verify_signature,
)

router = APIRouter(prefix="/wechat", tags=["公众号回调"])


def _require_config():
    settings = get_settings()
    if not settings.wechat_official_enabled:
        raise HTTPException(status_code=503, detail="公众号回调未启用")
    if not re.fullmatch(r"[A-Za-z0-9]{16,32}", settings.wechat_official_token):
        raise HTTPException(status_code=503, detail="公众号回调配置不完整")
    return settings


def _verify(token: str, signature: str, timestamp: str, nonce: str) -> None:
    if not verify_signature(token, signature, timestamp, nonce):
        raise HTTPException(status_code=403, detail="签名无效")


@router.get("/callback", response_class=PlainTextResponse)
def verify_callback(
    signature: str = Query(min_length=1, max_length=128),
    timestamp: str = Query(min_length=1, max_length=32),
    nonce: str = Query(min_length=1, max_length=128),
    echostr: str = Query(min_length=1, max_length=512),
):
    settings = _require_config()
    _verify(settings.wechat_official_token, signature, timestamp, nonce)
    return echostr


@router.post("/callback")
async def receive_callback(
    request: Request,
    signature: str = Query(min_length=1, max_length=128),
    timestamp: str = Query(min_length=1, max_length=32),
    nonce: str = Query(min_length=1, max_length=128),
    encrypt_type: str | None = Query(default=None, max_length=16),
):
    settings = _require_config()
    _verify(settings.wechat_official_token, signature, timestamp, nonce)
    if encrypt_type and encrypt_type.lower() == "aes":
        raise HTTPException(status_code=501, detail="公众号安全模式将在后续单元启用")
    try:
        message = parse_message(await request.body())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    decision = decide_reply_once(message, settings.wechat_official_public_base_url)
    if decision.text is None:
        return PlainTextResponse("success")
    payload = build_text_reply(message, decision.text)
    return Response(content=payload, media_type="application/xml")
