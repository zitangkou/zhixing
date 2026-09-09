from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.wechat_official_service import clear_dedup_cache, parse_message


TOKEN = "WechatTestToken2026"


@pytest.fixture(autouse=True)
def _reset_cached_settings():
    get_settings.cache_clear()
    clear_dedup_cache()
    yield
    get_settings.cache_clear()
    clear_dedup_cache()


def _signature(timestamp: str, nonce: str) -> str:
    return hashlib.sha1("".join(sorted((TOKEN, timestamp, nonce))).encode()).hexdigest()


def _query(timestamp: str = "1788796800", nonce: str = "nonce-1") -> str:
    return f"signature={_signature(timestamp, nonce)}&timestamp={timestamp}&nonce={nonce}"


def _xml(*, msg_type: str = "text", content: str = "菜单", event: str = "", msg_id: str = "10001") -> bytes:
    return f"""<xml>
<ToUserName><![CDATA[gh_duhengge]]></ToUserName>
<FromUserName><![CDATA[user_openid]]></FromUserName>
<CreateTime>1788796800</CreateTime>
<MsgType><![CDATA[{msg_type}]]></MsgType>
<Content><![CDATA[{content}]]></Content>
<Event><![CDATA[{event}]]></Event>
<MsgId>{msg_id}</MsgId>
</xml>""".encode()


def _enable(monkeypatch, base_url: str = "http://203.0.113.10") -> None:
    monkeypatch.setenv("WECHAT_OFFICIAL_ENABLED", "true")
    monkeypatch.setenv("WECHAT_OFFICIAL_TOKEN", TOKEN)
    monkeypatch.setenv("WECHAT_OFFICIAL_PUBLIC_BASE_URL", base_url)
    get_settings.cache_clear()
    clear_dedup_cache()


def test_callback_is_disabled_by_default(monkeypatch):
    monkeypatch.setenv("WECHAT_OFFICIAL_ENABLED", "false")
    monkeypatch.setenv("WECHAT_OFFICIAL_TOKEN", TOKEN)
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get(f"/api/wechat/callback?{_query()}&echostr=hello")
    assert response.status_code == 503


def test_callback_rejects_token_longer_than_wechat_limit(monkeypatch):
    monkeypatch.setenv("WECHAT_OFFICIAL_ENABLED", "true")
    monkeypatch.setenv("WECHAT_OFFICIAL_TOKEN", "a" * 48)
    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get(f"/api/wechat/callback?{_query()}&echostr=hello")
    assert response.status_code == 503


def test_callback_url_verification(monkeypatch):
    _enable(monkeypatch)
    with TestClient(app) as client:
        response = client.get(f"/api/wechat/callback?{_query()}&echostr=verified")
        invalid = client.get(
            "/api/wechat/callback?signature=invalid&timestamp=1788796800&nonce=nonce-1&echostr=bad"
        )
    assert response.status_code == 200
    assert response.text == "verified"
    assert invalid.status_code == 403


def test_text_and_subscribe_replies(monkeypatch):
    _enable(monkeypatch)
    with TestClient(app) as client:
        theory = client.post(f"/api/wechat/callback?{_query()}", content=_xml(content="时政"))
        subscribe = client.post(
            f"/api/wechat/callback?{_query(nonce='nonce-2')}",
            content=_xml(msg_type="event", content="", event="subscribe", msg_id="10002"),
        )
    assert theory.status_code == 200
    parsed = parse_message(theory.content)
    assert parsed.to_user == "user_openid"
    assert parsed.from_user == "gh_duhengge"
    assert "杜衡阁｜时政阅读" in parsed.content
    assert "http://203.0.113.10/#/pages/question/article-pick" in parsed.content
    assert "欢迎来到「杜衡阁」" in parse_message(subscribe.content).content


def test_numeric_menu_and_navigation(monkeypatch):
    _enable(monkeypatch)
    with TestClient(app) as client:
        menu = client.post(f"/api/wechat/callback?{_query(nonce='numeric-0')}", content=_xml(content="0"))
        today = client.post(
            f"/api/wechat/callback?{_query(nonce='numeric-1')}",
            content=_xml(content="1", msg_id="10011"),
        )
        theory = client.post(
            f"/api/wechat/callback?{_query(nonce='numeric-2')}",
            content=_xml(content="2", msg_id="10012"),
        )
        shenlun = client.post(
            f"/api/wechat/callback?{_query(nonce='numeric-3')}",
            content=_xml(content="3", msg_id="10013"),
        )

    menu_text = parse_message(menu.content).content
    assert "杜衡阁｜学习导航" in menu_text
    assert "1  今日学习" in menu_text
    assert "2  时政阅读" in menu_text
    assert "3  时评精拆" in menu_text
    assert "/#/pages/index/index" in parse_message(today.content).content
    assert "/#/pages/question/article-pick" in parse_message(theory.content).content
    assert "/#/pages/rmrb/article-list" in parse_message(shenlun.content).content
    assert "三刀解剖" in parse_message(shenlun.content).content


def test_fallback_unsupported_and_unsubscribe(monkeypatch):
    _enable(monkeypatch, base_url="invalid-url")
    with TestClient(app) as client:
        fallback = client.post(f"/api/wechat/callback?{_query()}", content=_xml(content="不知道"))
        image = client.post(
            f"/api/wechat/callback?{_query(nonce='nonce-3')}",
            content=_xml(msg_type="image", content="", msg_id="10003"),
        )
        unsubscribe = client.post(
            f"/api/wechat/callback?{_query(nonce='nonce-4')}",
            content=_xml(msg_type="event", content="", event="unsubscribe", msg_id="10004"),
        )
    assert "回复 0 查看学习导航" in parse_message(fallback.content).content
    assert "只能识别文字" in parse_message(image.content).content
    assert unsubscribe.text == "success"


def test_rejects_bad_signature_xml_and_aes_mode(monkeypatch):
    _enable(monkeypatch)
    with TestClient(app) as client:
        bad_signature = client.post(
            "/api/wechat/callback?signature=no&timestamp=1&nonce=2", content=_xml()
        )
        bad_xml = client.post(f"/api/wechat/callback?{_query()}", content=b"<!DOCTYPE xml><xml></xml>")
        aes = client.post(f"/api/wechat/callback?{_query()}&encrypt_type=aes", content=_xml())
    assert bad_signature.status_code == 403
    assert bad_xml.status_code == 400
    assert aes.status_code == 501
