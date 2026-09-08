"""关键路径 API 冒烟：注册登录 → 计划/足迹/知识/错题考点 → 模块 stats。

使用独立临时库，避免污染开发库。须在导入 app 之前设置 DATABASE_URL。
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_smoke.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["ALLOW_REGISTER"] = "true"
os.environ["SECRET_KEY"] = "smoke-test-secret"

from app.config import get_settings

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def _ok(res):
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("code") == 0, body
    return body.get("data")


def test_api_smoke_critical_path():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json().get("status") == "ok"

        cfg = _ok(client.get("/api/config"))
        assert "allowRegister" in cfg
        assert cfg["product"]["key"] == "general"
        assert cfg["product"]["homeMode"] == "dashboard"

        shenlun_cfg = _ok(client.get("/api/config", headers={"X-Product-Key": "shenlun"}))
        assert shenlun_cfg["product"]["key"] == "shenlun"
        assert shenlun_cfg["product"]["homeMode"] == "daily_training"
        assert [tab["title"] for tab in shenlun_cfg["product"]["tabs"]] == [
            "今日",
            "精读",
            "训练",
            "我的",
        ]

        theory_cfg = _ok(client.get("/api/config", headers={"X-Product-Key": "theory"}))
        assert theory_cfg["product"]["key"] == "theory"
        assert theory_cfg["product"]["dailyTargetMin"] == 15
        assert theory_cfg["product"]["tabs"][0]["route"] == "/pages/theory/index"

        unknown = client.get("/api/config", headers={"X-Product-Key": "unknown"})
        assert unknown.status_code == 400

        username = f"smoke_{uuid.uuid4().hex[:8]}"
        password = "SmokeTest1!"
        auth = _ok(
            client.post(
                "/api/auth/register",
                json={
                    "username": username,
                    "password": password,
                    "passwordConfirm": password,
                },
            )
        )
        token = auth["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = _ok(client.get("/api/user/me", headers=headers))
        assert me["username"] == username

        login = _ok(
            client.post(
                "/api/auth/login",
                json={"username": username, "password": password},
            )
        )
        assert login["access_token"]

        # 计划 / 足迹
        plan = _ok(client.get("/api/plan/today", headers=headers))
        assert plan is not None

        growth = _ok(client.get("/api/growth/overview", headers=headers))
        assert "weekBars" in growth and "domains" in growth

        # 知识：列表始终可用；sync 在无目录时返回业务错误（非 5xx）
        trees = _ok(client.get("/api/knowledge/trees", headers=headers))
        assert isinstance(trees, list)
        sync_res = client.post("/api/knowledge/sync", headers=headers)
        assert sync_res.status_code == 200
        sync_body = sync_res.json()
        assert sync_body.get("code") in (0, 400)
        status = _ok(client.get("/api/knowledge/status", headers=headers))
        assert status is not None

        # 行测错题 + 考点字段
        wrong = _ok(
            client.post(
                "/api/manual-wrong",
                headers=headers,
                json={
                    "subject": "行测",
                    "questionType": "判断推理",
                    "stem": "冒烟测试题干",
                    "myAnswer": "A",
                    "correctAnswer": "B",
                    "knowledgeNodeId": "node-smoke",
                    "knowledgeTreeKey": "xingce",
                    "knowledgePath": "判断推理/冒烟",
                    "images": [],
                },
            )
        )
        assert wrong["knowledgeNodeId"] == "node-smoke"
        assert wrong["knowledgePath"] == "判断推理/冒烟"

        listed = _ok(client.get("/api/manual-wrong", headers=headers))
        assert any(w.get("id") == wrong["id"] for w in listed)

        # 模块探针
        _ok(client.get("/api/rmrb/stats", headers=headers))
        _ok(client.get("/api/articles/daily"))


def teardown_module(_mod=None):
    if _DB.exists():
        try:
            _DB.unlink()
        except OSError:
            pass
