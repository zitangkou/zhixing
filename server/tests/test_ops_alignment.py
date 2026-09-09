"""运营物料对齐：v2.18 三刀示范导入、T0c 纲要专项 20 题。"""

from __future__ import annotations

import json
import os
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_ops_alignment.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SECRET_KEY"] = "ops-alignment-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin123"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MD = (FIXTURES / "v218_three_knife.md").read_text(encoding="utf-8")
HTML = (FIXTURES / "v218_wechat.html").read_text(encoding="utf-8")
T0C = json.loads((FIXTURES / "t0c_pack02_20.json").read_text(encoding="utf-8"))


def _ok(res):
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("code") == 0, body
    return body.get("data")


def test_v218_import_and_public_detail():
    with TestClient(app) as client:
        _ok(client.post(
            "/api/auth/register",
            json={"username": "ops_u1", "password": "Passw0rd!", "passwordConfirm": "Passw0rd!"},
        ))
        login = client.post("/admin/auth/login", json={"username": "admin", "password": "admin123"})
        token = _ok(login)["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        preview = _ok(client.post(
            "/admin/rmrb/preview-three-knife",
            json={"markdown": MD},
            headers=headers,
        ))
        assert preview["summary"]["articleTitle"] == "把书读薄，把自己读厚"
        assert preview["summary"]["incompleteReasons"] == []
        assert preview["parsed"]["examAnchor"]["theme"]
        assert preview["parsed"]["transferGuide"]["imitateDemo"]

        missing = client.post(
            "/admin/rmrb/import-three-knife",
            json={"markdown": MD, "displayHtml": HTML},
            headers=headers,
        )
        assert missing.json().get("code") != 0

        created = _ok(client.post(
            "/admin/rmrb/article",
            json={
                "title": "把书读薄，把自己读厚",
                "source": "人民时评",
                "content": "原文占位",
                "isPublished": True,
            },
            headers=headers,
        ))
        article_id = created["id"]

        imported = _ok(client.post(
            "/admin/rmrb/import-three-knife",
            json={
                "markdown": MD,
                "displayHtml": HTML,
                "articleId": article_id,
                "sourceUrl": "http://paper.people.com.cn/example",
            },
            headers=headers,
        ))
        assert imported["articleId"] == article_id
        assert imported["example"]["examAnchor"]["stancePath"]
        assert imported["example"]["transferGuide"]["examFit"]
        assert "<div" in imported["example"]["displayHtml"]
        assert "<table" in imported["example"]["displayHtml"]
        assert "考题定位" in imported["example"]["displayHtml"]
        assert "<script" not in imported["example"]["displayHtml"].lower()
        assert "<style" in imported["example"]["displayHtml"].lower()

        guest_list = _ok(client.get("/api/rmrb/articles"))
        assert any(a["id"] == article_id for a in guest_list)
        detail = _ok(client.get(f"/api/rmrb/articles/{article_id}"))
        assert detail["teachingExample"]["argument"]["openingPattern"]
        assert detail["teachingExample"]["quotes"]
        assert "规范词" in detail["teachingExample"]["displayHtml"]
        assert "文化·读书修身" in (detail.get("tags") or [])
        assert "文化·读书修身" in (detail["teachingExample"].get("examAnchor") or {}).get("theme", "")
        _ok(client.delete(f"/admin/rmrb/article/{article_id}", headers=headers))
        gone = client.get(f"/api/rmrb/articles/{article_id}")
        assert gone.status_code == 200
        assert gone.json().get("code") == 404


def test_t0c_pack_import_and_parts():
    with TestClient(app) as client:
        login = client.post("/admin/auth/login", json={"username": "admin", "password": "admin123"})
        token = _ok(login)["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        data = _ok(client.post(
            "/admin/theory-learning/import-t0c",
            json={"payload": T0C, "pending": False},
            headers=headers,
        ))
        assert data["questionCount"] == 20
        article_id = data["articleId"]
        assert len(data["entry"]["parts"]) == 4
        assert all(len(p["questionIds"]) == 5 for p in data["entry"]["parts"])

        packs = _ok(client.get("/api/theory/packs"))
        assert any(p["articleId"] == article_id for p in packs)

        questions = _ok(client.get(f"/api/questions?articleId={article_id}"))
        assert len(questions) == 20
        assert questions[0]["sourceSentence"]
        assert "【干扰项】" in questions[0]["analysis"]
        assert questions[0]["stem"].startswith("【")
