"""生成工作台 API 测试：批次列表/详情、模板、校验、审核流程。

使用独立临时库，须在导入 app 之前设置 DATABASE_URL。
注意：全量测试时其他用例可能删除 admin 用户，故用 fixture 动态建管理员并取 token。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_TEST_DB = Path(__file__).resolve().parent / "_generation_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["SECRET_KEY"] = "gen-test-secret"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import AdminUser, Role  # noqa: E402

# 建表
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def _ensure_admin() -> None:
    """确保 super_admin 角色和 admin 用户存在（其他用例可能删除）。"""
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.code == "super_admin").first()
        if not role:
            from app.core.permissions import ROLE_PERMISSIONS
            perms = ROLE_PERMISSIONS.get("super_admin", [])
            role = Role(code="super_admin", name="超级管理员", permissions=json.dumps(perms))
            db.add(role)
            db.flush()
        admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if not admin:
            db.add(AdminUser(
                username="admin",
                password_hash=hash_password("admin123"),
                nickname="系统管理员",
                role_id=role.id,
            ))
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def auth_headers():
    """每个用例前确保 admin 存在并获取新鲜 token。"""
    _ensure_admin()
    res = client.post("/admin/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, res.text
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _ok(res):
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("code") == 0, body
    return body.get("data")


# ═══════════════════════════════════════════════════════
#  1. 统计
# ═══════════════════════════════════════════════════════

class TestStats:
    def test_stats_returns_summary(self, auth_headers):
        data = _ok(client.get("/admin/generation/stats", headers=auth_headers))
        assert data["total_generated"] == 137  # 32+10+40+35+20
        assert data["batch_count"] == 5
        assert "auto_pass_rate" in data
        assert "pending_review" in data
        assert "by_engine" in data
        assert "qa_data_analysis" in data["by_engine"]
        assert "qa_quantity" in data["by_engine"]


# ═══════════════════════════════════════════════════════
#  2. 批次列表 / 详情
# ═══════════════════════════════════════════════════════

class TestBatches:
    def test_batch_list(self, auth_headers):
        data = _ok(client.get("/admin/generation/batches", headers=auth_headers))
        assert data["total"] == 5
        assert len(data["items"]) == 5
        b = data["items"][0]
        assert "batch_id" in b
        assert "engine_type" in b
        assert "template_version" in b
        assert "total_questions" in b
        assert "passed_count" in b
        assert "failed_count" in b
        assert "pass_rate" in b
        assert "created_at" in b
        assert "status" in b

    def test_batch_list_filter_by_engine(self, auth_headers):
        data = _ok(client.get("/admin/generation/batches?engine_type=qa_quantity", headers=auth_headers))
        assert data["total"] == 1
        assert data["items"][0]["engine_type"] == "qa_quantity"

    def test_batch_detail_data_analysis(self, auth_headers):
        data = _ok(client.get("/admin/generation/batches/batch-qa-data-analysis-v2", headers=auth_headers))
        assert data["batch_id"] == "batch-qa-data-analysis-v2"
        assert data["engine_type"] == "qa_data_analysis"
        assert data["total_questions"] == 32
        assert len(data["questions"]) == 32
        q = data["questions"][0]
        assert "question_id" in q
        assert "subtype" in q
        assert "difficulty" in q
        assert "answer" in q
        assert "dual_solve_match" in q
        assert "distractor_count" in q
        assert "review_status" in q

    def test_batch_detail_quantity(self, auth_headers):
        data = _ok(client.get("/admin/generation/batches/batch-qa-quantity-v1", headers=auth_headers))
        assert data["total_questions"] == 10
        assert len(data["questions"]) == 10

    def test_batch_detail_not_found(self, auth_headers):
        res = client.get("/admin/generation/batches/nonexistent", headers=auth_headers)
        assert res.status_code == 404

    def test_batch_run_creates_pending(self, auth_headers):
        data = _ok(client.post("/admin/generation/batches/run", headers=auth_headers,
                                json={"engine_type": "qa_quantity", "count": 5, "seed": 99}))
        assert data["status"] == "pending"
        assert "batch_id" in data


# ═══════════════════════════════════════════════════════
#  3. 模板
# ═══════════════════════════════════════════════════════

class TestTemplates:
    def test_template_list(self, auth_headers):
        data = _ok(client.get("/admin/generation/templates", headers=auth_headers))
        assert len(data) >= 2
        t = data[0]
        assert "template_id" in t
        assert "engine_type" in t
        assert "version" in t
        assert "param_schema" in t

    def test_template_history(self, auth_headers):
        data = _ok(client.get("/admin/generation/templates/tpl-qa-data-analysis-v2/history", headers=auth_headers))
        assert len(data) >= 1
        assert "version" in data[0]

    def test_template_history_not_found(self, auth_headers):
        res = client.get("/admin/generation/templates/nonexistent/history", headers=auth_headers)
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════
#  4. 自动校验
# ═══════════════════════════════════════════════════════

class TestValidation:
    def test_validation_report(self, auth_headers):
        data = _ok(client.get("/admin/generation/batches/batch-qa-data-analysis-v2/validation", headers=auth_headers))
        assert data["batch_id"] == "batch-qa-data-analysis-v2"
        assert data["total"] == 32
        assert "passed" in data
        assert "failed" in data
        assert "pass_rate" in data
        assert "failure_distribution" in data
        assert "per_question" in data
        assert len(data["per_question"]) == 32
        vq = data["per_question"][0]
        assert "checks" in vq
        assert "dual_solve_match" in vq["checks"]
        assert "options_distinct" in vq["checks"]
        assert "answer_unique" in vq["checks"]
        assert "data_consistent" in vq["checks"]
        assert "distractors_traced" in vq["checks"]
        assert "all_passed" in vq

    def test_validation_report_not_found(self, auth_headers):
        res = client.get("/admin/generation/batches/nonexistent/validation", headers=auth_headers)
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════
#  5. 题目详情
# ═══════════════════════════════════════════════════════

class TestQuestionDetail:
    def test_question_detail(self, auth_headers):
        data = _ok(client.get("/admin/generation/questions/Q2-DA-BASE-001", headers=auth_headers))
        assert data["question_id"] == "Q2-DA-BASE-001"
        assert data["origin_type"] == "generated"
        assert "stem" in data
        assert "options" in data
        assert "answer" in data
        assert "calc_tree" in data
        assert "distractors" in data
        assert "dual_solve" in data
        assert "generation_meta" in data
        assert "validation" in data
        assert "review" in data

    def test_question_detail_not_found(self, auth_headers):
        res = client.get("/admin/generation/questions/NOPE", headers=auth_headers)
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════
#  6. 审核流程
# ═══════════════════════════════════════════════════════

class TestReview:
    def test_review_tasks_initial_pending(self, auth_headers):
        data = _ok(client.get("/admin/generation/review-tasks", headers=auth_headers))
        assert data["stats"]["total"] == 137

    def test_review_tasks_filter_pending(self, auth_headers):
        data = _ok(client.get("/admin/generation/review-tasks?status=pending", headers=auth_headers))
        assert data["total"] >= 0

    def test_approve_question(self, auth_headers):
        data = _ok(client.post("/admin/generation/questions/Q2-DA-BASE-001/review", headers=auth_headers,
                                json={"action": "approve", "comment": "题目质量合格", "reviewer": "tester"}))
        assert data["action"] == "approve"
        assert data["question_id"] == "Q2-DA-BASE-001"

    def test_reject_question(self, auth_headers):
        data = _ok(client.post("/admin/generation/questions/Q4-QTY-WORK-001/review", headers=auth_headers,
                                json={"action": "reject", "comment": "选项有歧义", "reviewer": "tester"}))
        assert data["action"] == "reject"

    def test_review_tasks_after_review(self, auth_headers):
        # 先审核两题
        client.post("/admin/generation/questions/Q2-DA-BASE-001/review", headers=auth_headers,
                    json={"action": "approve", "comment": "ok", "reviewer": "tester"})
        client.post("/admin/generation/questions/Q4-QTY-WORK-001/review", headers=auth_headers,
                    json={"action": "reject", "comment": "bad", "reviewer": "tester"})
        data = _ok(client.get("/admin/generation/review-tasks", headers=auth_headers))
        assert data["stats"]["approved"] >= 1
        assert data["stats"]["rejected"] >= 1

    def test_review_tasks_filter_approved(self, auth_headers):
        client.post("/admin/generation/questions/Q2-DA-BASE-002/review", headers=auth_headers,
                    json={"action": "approve", "comment": "ok", "reviewer": "tester"})
        data = _ok(client.get("/admin/generation/review-tasks?status=approve", headers=auth_headers))
        assert data["total"] >= 1

    def test_question_detail_shows_review(self, auth_headers):
        client.post("/admin/generation/questions/Q2-DA-BASE-003/review", headers=auth_headers,
                    json={"action": "approve", "comment": "审核通过", "reviewer": "tester"})
        data = _ok(client.get("/admin/generation/questions/Q2-DA-BASE-003", headers=auth_headers))
        assert data["review"]["status"] == "approve"
        assert data["review"]["comment"] == "审核通过"

    def test_batch_review(self, auth_headers):
        ids = ["Q2-DA-BASE-004", "Q2-DA-BASE-005"]
        data = _ok(client.post("/admin/generation/questions/batch-review", headers=auth_headers,
                                json={"action": "approve", "comment": "批量通过", "reviewer": "tester",
                                      "question_ids": ids}))
        assert data["processed"] == 2

    def test_invalid_action_rejected(self, auth_headers):
        res = client.post("/admin/generation/questions/Q2-DA-BASE-001/review", headers=auth_headers,
                           json={"action": "invalid", "comment": ""})
        assert res.status_code == 400

    def test_review_nonexistent_question(self, auth_headers):
        res = client.post("/admin/generation/questions/NOPE/review", headers=auth_headers,
                           json={"action": "approve", "comment": ""})
        assert res.status_code == 404

    def test_unauthorized(self):
        res = client.get("/admin/generation/batches")
        assert res.status_code == 401
