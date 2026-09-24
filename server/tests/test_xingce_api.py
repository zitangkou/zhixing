"""行测公开目录与管理端导入。空库返回空结构，不 404。"""
from __future__ import annotations

import os
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_xingce_api.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["ALLOW_REGISTER"] = "true"
os.environ["SECRET_KEY"] = "xingce-api-test-secret"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

SAMPLE = {
    "exam_year": 2025,
    "exam_name": "2025年国家公务员考试《行测》省级样题",
    "paper_type": "省级",
    "schema_version": "2",
    "total_questions": 1,
    "sections": [
        {
            "name": "政治理论",
            "questions": [
                {
                    "number": 1,
                    "stem": "样题：下列哪一项是中国共产党的根本宗旨？",
                    "options": {
                        "A": "全心全意为人民服务",
                        "B": "选项B",
                        "C": "选项C",
                        "D": "选项D",
                    },
                    "answer": "A",
                    "explanation": "示例解析。",
                }
            ],
        }
    ],
}


def _ok(res):
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("code") == 0, body
    return body.get("data")


def test_catalog_empty_is_not_404():
    with TestClient(app) as client:
        res = client.get("/api/xingce/catalog")
        data = _ok(res)
        assert data["papers"] == []
        assert data["years"] == []
        names = [item["name"] for item in data["modules"]]
        assert "政治理论" in names
        assert all(item["count"] == 0 for item in data["modules"] if item["name"] == "政治理论")


def test_admin_import_then_catalog_quiz_and_answer():
    with TestClient(app) as client:
        admin = _ok(client.post("/admin/auth/login", json={"username": "admin", "password": "admin123"}))
        headers = {"Authorization": f"Bearer {admin['access_token']}"}
        imported = _ok(
            client.post(
                "/admin/xingce/import",
                headers=headers,
                files={"file": ("sample.json", __import__("json").dumps(SAMPLE).encode(), "application/json")},
            )
        )
        assert imported["newQuestions"] == 1
        assert imported["newPositions"] == 1

        overview = _ok(client.get("/admin/xingce/overview", headers=headers))
        assert overview["positionTotal"] >= 1
        assert overview["papers"][0]["paperType"] == "省级"
        assert overview["papers"][0]["visibleOnHub"] is True

        catalog = _ok(client.get("/api/xingce/catalog"))
        assert catalog["papers"]
        assert catalog["papers"][0]["year"] == 2025
        assert catalog["papers"][0]["count"] == 1

        quiz = _ok(client.get("/api/xingce/quiz", params={"module": "政治理论", "count": 5}))
        assert quiz[0]["stem"].startswith("样题")
        question_id = quiz[0]["id"]
        graded = _ok(client.post("/api/xingce/answer", json={"questionId": question_id, "answer": quiz[0]["correctAnswer"]}))
        assert graded["correct"] is True

        again = _ok(
            client.post(
                "/admin/xingce/import",
                headers=headers,
                files={"file": ("sample.json", __import__("json").dumps(SAMPLE).encode(), "application/json")},
            )
        )
        assert again["newQuestions"] == 0
        assert again["newPositions"] == 0
