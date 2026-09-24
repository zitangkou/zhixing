"""小程序微信一键登录：mock jscode2session，不访问微信网络。"""
from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.public.auth_user import router as auth_router
from app.config import get_settings
from app.database import get_db
from app.models import AppUser, Base

SECRET = "wx-test-secret-do-not-leak"
APP_ID = "wx-test-appid"
OPENID = "o-wechat-login-test"


class FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls: list[tuple[str, dict | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None):
        self.calls.append((url, dict(params or {})))
        return self.response


@pytest.fixture
def db_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def client(db_session_factory):
    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(auth_router, prefix="/api")
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("MINIPROGRAM_APP_ID", APP_ID)
    monkeypatch.setenv("MINIPROGRAM_APP_SECRET", SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def patch_wechat(monkeypatch, response: FakeResponse) -> FakeClient:
    fake = FakeClient(response)
    monkeypatch.setattr(
        "app.services.wechat_miniprogram_service.httpx.Client",
        lambda *args, **kwargs: fake,
    )
    return fake


def _assert_no_secret(text: str) -> None:
    assert SECRET not in text
    assert "session-key-secret" not in text


def test_unconfigured_returns_503(monkeypatch, client):
    monkeypatch.setenv("MINIPROGRAM_APP_ID", "")
    monkeypatch.setenv("MINIPROGRAM_APP_SECRET", "")
    get_settings.cache_clear()
    res = client.post("/api/auth/wechat/login", json={"code": "abc"})
    assert res.status_code == 503
    assert res.json()["message"] == "微信登录未配置"
    _assert_no_secret(res.text)


def test_create_user_then_reuse_openid(monkeypatch, configured, client, db_session_factory):
    fake = patch_wechat(
        monkeypatch,
        FakeResponse(200, {"openid": OPENID, "session_key": "session-key-secret"}),
    )
    first = client.post("/api/auth/wechat/login", json={"code": "code-1"})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["code"] == 0
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["access_token"]
    user = body["data"]["user"]
    assert user["nickname"] == "知行学员"
    assert user["username"] is None
    _assert_no_secret(first.text)
    assert fake.calls[0][0] == "https://api.weixin.qq.com/sns/jscode2session"
    assert fake.calls[0][1]["appid"] == APP_ID
    assert fake.calls[0][1]["secret"] == SECRET
    assert fake.calls[0][1]["js_code"] == "code-1"
    assert fake.calls[0][1]["grant_type"] == "authorization_code"

    me = client.get(
        "/api/user/me",
        headers={"Authorization": f"Bearer {body['data']['access_token']}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["code"] == 0
    assert me.json()["data"]["id"] == user["id"]

    second = client.post("/api/auth/wechat/login", json={"code": "code-2"})
    assert second.status_code == 200, second.text
    assert second.json()["data"]["user"]["id"] == user["id"]
    _assert_no_secret(second.text)

    with db_session_factory() as db:
        rows = db.query(AppUser).filter(AppUser.openid == OPENID).all()
        assert len(rows) == 1
        assert rows[0].username is None
        assert rows[0].password_hash is None
        assert rows[0].nickname == "知行学员"


def test_invalid_code_does_not_leak_secret(monkeypatch, configured, client, caplog):
    caplog.set_level("WARNING")
    patch_wechat(monkeypatch, FakeResponse(200, {"errcode": 40029, "errmsg": "invalid code"}))
    res = client.post("/api/auth/wechat/login", json={"code": "bad-code"})
    assert res.status_code == 400
    assert res.json()["message"] == "微信登录码无效或已过期"
    _assert_no_secret(res.text)
    _assert_no_secret(caplog.text)
    assert "40029" in caplog.text


def test_wechat_http_failure(monkeypatch, configured, client, caplog):
    caplog.set_level("WARNING")
    patch_wechat(monkeypatch, FakeResponse(500, {"errcode": -1, "errmsg": SECRET}))
    res = client.post("/api/auth/wechat/login", json={"code": "abc"})
    assert res.status_code == 502
    assert res.json()["message"] == "微信登录暂时不可用"
    _assert_no_secret(res.text)
    _assert_no_secret(caplog.text)


def test_transport_error_does_not_leak_secret(monkeypatch, configured, client, caplog):
    caplog.set_level("WARNING")

    class BoomClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, params=None):
            raise httpx.ConnectError(f"network down secret={SECRET}")

    monkeypatch.setattr(
        "app.services.wechat_miniprogram_service.httpx.Client",
        lambda *args, **kwargs: BoomClient(),
    )
    res = client.post("/api/auth/wechat/login", json={"code": "abc"})
    assert res.status_code == 502
    assert res.json()["message"] == "微信登录暂时不可用"
    _assert_no_secret(res.text)
    _assert_no_secret(caplog.text)


def test_disabled_openid_user(monkeypatch, configured, client, db_session_factory):
    patch_wechat(
        monkeypatch,
        FakeResponse(200, {"openid": OPENID, "session_key": "session-key-secret"}),
    )
    first = client.post("/api/auth/wechat/login", json={"code": "code-1"})
    user_id = first.json()["data"]["user"]["id"]
    with db_session_factory() as db:
        user = db.get(AppUser, user_id)
        assert user is not None
        user.is_active = False
        db.commit()

    second = client.post("/api/auth/wechat/login", json={"code": "code-2"})
    assert second.status_code == 403
    assert second.json()["message"] == "账号已被禁用"
    _assert_no_secret(second.text)


def test_password_login_still_works(monkeypatch, client):
    monkeypatch.setenv("ALLOW_REGISTER", "true")
    get_settings.cache_clear()
    username = "wxpwduser"
    password = "Passw0rd!"
    reg = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "passwordConfirm": password},
    )
    assert reg.status_code == 200, reg.text
    assert reg.json()["code"] == 0
    login = client.post("/api/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["code"] == 0
    assert body["data"]["access_token"]
    assert body["data"]["user"]["username"] == username
    get_settings.cache_clear()
