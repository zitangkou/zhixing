"""微信小程序 jscode2session 登录。

使用对应小程序的服务端凭据，与公众号回调配置无关。
日志与返回文案不得包含 AppSecret、session_key 或微信原始响应。
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AppUser, gen_id

logger = logging.getLogger(__name__)

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
_INVALID_CODE_ERRCODES = {40029, 40163}
_REQUEST_TIMEOUT_SECONDS = 8.0


class WechatLoginError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def _exchange_code(code: str, product_key: str = "general", app_key: str = "") -> str:
    settings = get_settings()
    app_id, app_secret = settings.miniprogram_credentials(product_key, app_key)
    if not app_id or not app_secret:
        raise WechatLoginError(503, "微信登录未配置")

    js_code = code.strip()
    if not js_code:
        raise WechatLoginError(400, "微信登录码无效或已过期")

    params = {
        "appid": app_id,
        "secret": app_secret,
        "js_code": js_code,
        "grant_type": "authorization_code",
    }
    try:
        with httpx.Client(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            resp = client.get(JSCODE2SESSION_URL, params=params)
    except httpx.HTTPError:
        logger.warning("miniprogram jscode2session transport error")
        raise WechatLoginError(502, "微信登录暂时不可用") from None

    if resp.status_code >= 400:
        logger.warning("miniprogram jscode2session http status=%s", resp.status_code)
        raise WechatLoginError(502, "微信登录暂时不可用")

    try:
        data = resp.json()
    except ValueError:
        logger.warning("miniprogram jscode2session returned non-json")
        raise WechatLoginError(502, "微信登录暂时不可用") from None

    if not isinstance(data, dict):
        logger.warning("miniprogram jscode2session returned unexpected payload")
        raise WechatLoginError(502, "微信登录暂时不可用")

    try:
        errcode = int(data.get("errcode") or 0)
    except (TypeError, ValueError):
        errcode = -1
    if errcode:
        logger.warning("miniprogram jscode2session rejected errcode=%s", errcode)
        if errcode in _INVALID_CODE_ERRCODES:
            raise WechatLoginError(400, "微信登录码无效或已过期")
        raise WechatLoginError(502, "微信登录暂时不可用")

    openid = data.get("openid")
    if not isinstance(openid, str):
        logger.warning("miniprogram jscode2session missing openid")
        raise WechatLoginError(502, "微信登录暂时不可用")
    openid = openid.strip()
    if not openid or len(openid) > 64:
        logger.warning("miniprogram jscode2session openid length invalid")
        raise WechatLoginError(502, "微信登录暂时不可用")
    return openid


def login_with_wechat_code(
    db: Session, code: str, product_key: str = "general", app_key: str = ""
) -> tuple[AppUser | None, WechatLoginError | None]:
    try:
        openid = _exchange_code(code, product_key, app_key)
    except WechatLoginError as exc:
        return None, exc

    user = db.query(AppUser).filter(AppUser.openid == openid).first()
    if user:
        if not user.is_active:
            return None, WechatLoginError(403, "账号已被禁用")
        return user, None

    user = AppUser(
        id=gen_id("u"),
        username=None,
        password_hash=None,
        openid=openid,
        nickname=(
            "言遇英语用户" if app_key == "yanyu_english" else
            "光线练习簿用户" if app_key == "sheying" else
            "AI 百宝箱用户" if app_key == "baibaoxiang" else
            "知库用户" if product_key == "zhiku" else "杜衡阁学员"
        ),
        points=0,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        user = db.query(AppUser).filter(AppUser.openid == openid).first()
        if not user:
            logger.warning("miniprogram login failed to persist openid user")
            return None, WechatLoginError(502, "微信登录暂时不可用")
        if not user.is_active:
            return None, WechatLoginError(403, "账号已被禁用")
        return user, None

    db.refresh(user)
    return user, None
