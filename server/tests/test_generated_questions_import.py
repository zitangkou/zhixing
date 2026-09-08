"""生成题入库 + 审核→发布闭环测试。

使用独立临时库。须在导入 app 之前设置 DATABASE_URL。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

_TEST_DB = Path(__file__).resolve().parent / "_gen_import_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["SECRET_KEY"] = "gen-test-secret"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    QuestionItem,
    QuestionVersion,
)
from scripts.import_generated_questions import run_import  # noqa: E402


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def first_import():
    return run_import()


@pytest.fixture(scope="module")
def second_import():
    return run_import()


@pytest.fixture(scope="module")
def admin_client():
    """已登录的管理端 TestClient。"""
    client = TestClient(app)
    # 触发 seed 创建默认管理员
    with client:
        resp = client.post("/admin/auth/login", json={"username": "admin", "password": "admin123"})
        if resp.status_code == 200:
            token = resp.json()["data"]["access_token"]
            client.headers.update({"Authorization": f"Bearer {token}"})
        return client


# ═══════════════════════════════════════════════════════
#  1. 导入测试
# ═══════════════════════════════════════════════════════


class TestGeneratedImport:
    def test_total_137_questions(self, db_session, first_import):
        count = db_session.query(QuestionItem).filter(QuestionItem.origin_type == "generated").count()
        assert count == 137, f"生成题应为 137 道，实际 {count}"

    def test_all_pending_review(self, db_session, first_import):
        pending = (
            db_session.query(QuestionItem)
            .filter(QuestionItem.origin_type == "generated", QuestionItem.lifecycle_status == "pending_review")
            .count()
        )
        assert pending == 137, f"所有生成题应为 pending_review，实际 {pending}"

    @pytest.mark.parametrize("engine,expected", [
        ("qa_data_analysis_v2", 32),
        ("qa_quantity_v1", 10),
        ("qa_verbal_v2", 40),
        ("qa_judgment_v1", 35),
        ("qa_theory_v1", 20),
    ])
    def test_per_engine_distribution(self, db_session, first_import, engine, expected):
        """通过 version.tag 字段统计各引擎题量。"""
        count = (
            db_session.query(QuestionItem)
            .join(QuestionVersion, QuestionVersion.question_id == QuestionItem.id)
            .filter(QuestionItem.origin_type == "generated", QuestionVersion.tag == engine)
            .distinct()
            .count()
        )
        assert count == expected, f"{engine} 应有 {expected} 题，实际 {count}"

    def test_all_have_versions(self, db_session, first_import):
        items = db_session.query(QuestionItem).filter(QuestionItem.origin_type == "generated").all()
        for item in items:
            version = db_session.query(QuestionVersion).filter(QuestionVersion.question_id == item.id).first()
            assert version is not None, f"题目 {item.id} 没有版本"
            assert version.correct_answer_json is not None, f"题目 {item.id} 没有答案"
            assert version.options_json is not None, f"题目 {item.id} 没有选项"

    def test_all_have_explanations(self, db_session, first_import):
        items = db_session.query(QuestionItem).filter(QuestionItem.origin_type == "generated").all()
        missing = 0
        for item in items:
            version = db_session.query(QuestionVersion).filter(QuestionVersion.question_id == item.id).first()
            if not version or not version.explanation:
                missing += 1
        assert missing == 0, f"有 {missing} 道生成题缺少解析"

    def test_analysis_payload_contains_engine(self, db_session, first_import):
        """analysis_payload_json 应包含 _engine 字段。"""
        version = db_session.query(QuestionVersion).first()
        assert version is not None
        payload = version.analysis_payload_json or {}
        assert "_engine" in payload, "analysis_payload 应包含 _engine"

    def test_question_id_matches_source(self, db_session, first_import):
        """使用生成题的 question_id 作为数据库主键。"""
        item = db_session.query(QuestionItem).filter(QuestionItem.origin_type == "generated").first()
        assert item is not None
        # ID 应该是生成题的原始 ID（如 Q2-DA-BASE-001），不是 qi 开头的 UUID
        assert not item.id.startswith("qi"), f"生成题 ID 应为原始 question_id，实际 {item.id}"


# ═══════════════════════════════════════════════════════
#  2. 幂等性测试
# ═══════════════════════════════════════════════════════


class TestGeneratedIdempotency:
    def test_second_run_zero_new(self, first_import, second_import):
        assert second_import.new_questions == 0, "第二次导入不应新建题目"

    def test_second_run_zero_updated(self, first_import, second_import):
        assert second_import.updated_questions == 0, "第二次导入不应更新题目"

    def test_second_run_all_reused(self, first_import, second_import):
        assert second_import.reused_questions == 137, "第二次导入应复用全部 137 题"

    def test_total_unchanged(self, db_session, first_import, second_import):
        count = db_session.query(QuestionItem).filter(QuestionItem.origin_type == "generated").count()
        assert count == 137, "重跑后题量不变"


# ═══════════════════════════════════════════════════════
#  3. 审核→发布闭环测试
# ═══════════════════════════════════════════════════════


class TestReviewPublishWorkflow:
    def _get_generated_question_id(self, db_session, engine: str | None = None) -> str:
        """获取一道生成题的 ID。"""
        query = db_session.query(QuestionItem).filter(QuestionItem.origin_type == "generated")
        if engine:
            query = query.join(QuestionVersion, QuestionVersion.question_id == QuestionItem.id).filter(
                QuestionVersion.tag == engine
            )
        item = query.first()
        assert item is not None
        return item.id

    def test_approve_then_publish(self, db_session, admin_client, first_import):
        """流程：pending_review → approve → approved → publish → active"""
        qid = self._get_generated_question_id(db_session, "qa_data_analysis_v2")

        # 初始状态
        item = db_session.query(QuestionItem).filter(QuestionItem.id == qid).first()
        assert item.lifecycle_status == "pending_review"

        # approve
        resp = admin_client.post(f"/admin/generation/questions/{qid}/review", json={
            "action": "approve",
            "comment": "测试通过",
            "reviewer": "test_admin",
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] == 0, body
        assert body["data"]["lifecycle_status"] == "approved", f"approve 后应为 approved，实际 {body['data']['lifecycle_status']}"

        # publish（应通过门禁）
        resp2 = admin_client.post(f"/admin/question-bank/questions/{qid}/publish")
        assert resp2.status_code == 200, resp2.text
        body2 = resp2.json()
        assert body2["code"] == 0, body2
        assert body2["data"]["lifecycle_status"] == "active"
        assert body2["data"]["published"] is True

    def test_publish_blocked_when_pending_review(self, db_session, admin_client, first_import):
        """pending_review 状态直接 publish 应被门禁拒绝（400）。"""
        qid = self._get_generated_question_id(db_session, "qa_quantity_v1")

        # 确认是 pending_review
        item = db_session.query(QuestionItem).filter(QuestionItem.id == qid).first()
        assert item.lifecycle_status == "pending_review"

        # 直接 publish 应失败
        resp = admin_client.post(f"/admin/question-bank/questions/{qid}/publish")
        assert resp.status_code == 200  # API 层返回 200 但 code != 0
        body = resp.json()
        assert body["code"] != 0, f"pending_review 状态发布应被拒绝，实际 code={body['code']}"

    def test_reject_then_publish_blocked(self, db_session, admin_client, first_import):
        """流程：pending_review → reject → disputed → publish 应被拒绝（400）。"""
        qid = self._get_generated_question_id(db_session, "qa_verbal_v2")

        # reject
        resp = admin_client.post(f"/admin/generation/questions/{qid}/review", json={
            "action": "reject",
            "comment": "测试驳回",
            "reviewer": "test_admin",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["lifecycle_status"] == "disputed"

        # publish 应被门禁拒绝
        resp2 = admin_client.post(f"/admin/question-bank/questions/{qid}/publish")
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["code"] != 0, "disputed 状态发布应被拒绝"

    def test_publish_with_missing_explanation_warns(self, db_session, admin_client, first_import):
        """缺解析的题：approve（直接设DB状态）→ publish → active + 警告。"""
        # 创建一道缺解析的测试题（不修改源文件）
        item = QuestionItem(
            id="TEST-NO-EXP-001",
            origin_type="generated",
            subject="行测",
            module="常识判断",
            subtype="测试题",
            response_type="single",
            canonical_hash="test_no_explanation_hash_001",
            difficulty=1,
            lifecycle_status="approved",  # 直接设为已审核
        )
        db_session.add(item)
        db_session.flush()
        version = QuestionVersion(
            question_id=item.id,
            version_no=1,
            stem="测试题干：以下说法正确的是？",
            options_json={"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
            correct_answer_json="A",
            explanation="",  # 缺解析
            content_hash="test_no_exp_content_hash_001",
            change_summary="test import",
            tag="qa_test",
        )
        db_session.add(version)
        db_session.flush()
        item.current_version_id = version.id
        db_session.commit()

        qid = item.id

        # publish（应成功但带警告）
        resp2 = admin_client.post(f"/admin/question-bank/questions/{qid}/publish")
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["code"] == 0, f"缺解析应警告但可发布，实际 {body2}"
        assert body2["data"]["published"] is True
        assert body2["data"]["lifecycle_status"] == "active"
        assert len(body2["data"]["warnings"]) > 0, "缺解析应有警告"
        assert "解析" in body2["data"]["warnings"][0]

    def test_publish_blocked_when_missing_answer(self, db_session, admin_client, first_import):
        """缺答案的题：approved → publish 应被拒绝（400）。"""
        item = QuestionItem(
            id="TEST-NO-ANS-001",
            origin_type="generated",
            subject="行测",
            module="常识判断",
            subtype="测试题",
            response_type="single",
            canonical_hash="test_no_answer_hash_001",
            difficulty=1,
            lifecycle_status="approved",  # 直接设为已审核
        )
        db_session.add(item)
        db_session.flush()
        version = QuestionVersion(
            question_id=item.id,
            version_no=1,
            stem="测试题干：缺答案题？",
            options_json={"A": "A", "B": "B", "C": "C", "D": "D"},
            correct_answer_json=None,  # 缺答案
            explanation="有解析",
            content_hash="test_no_ans_content_hash_001",
            change_summary="test import",
            tag="qa_test",
        )
        db_session.add(version)
        db_session.flush()
        item.current_version_id = version.id
        db_session.commit()

        qid = item.id

        # publish 应被拒绝
        resp2 = admin_client.post(f"/admin/question-bank/questions/{qid}/publish")
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["code"] != 0, "缺答案发布应被拒绝"

    def test_unpublish(self, db_session, admin_client, first_import):
        """下线：active → retired"""
        qid = self._get_generated_question_id(db_session, "qa_judgment_v1")

        # 先 approve + publish
        admin_client.post(f"/admin/generation/questions/{qid}/review", json={
            "action": "approve", "comment": "test", "reviewer": "test",
        })
        admin_client.post(f"/admin/question-bank/questions/{qid}/publish")

        # unpublish
        resp = admin_client.post(f"/admin/question-bank/questions/{qid}/unpublish")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["lifecycle_status"] == "retired"


# ═══════════════════════════════════════════════════════
#  4. 生成工作台 API 测试
# ═══════════════════════════════════════════════════════


class TestGenerationWorkbench:
    def test_list_batches_5_engines(self, admin_client):
        resp = admin_client.get("/admin/generation/batches")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        # API 返回分页结构 {items, total, page, page_size}
        batches = data.get("items", data) if isinstance(data, dict) else data
        assert len(batches) == 5, f"应有 5 个引擎批次，实际 {len(batches)}"

    def test_batch_detail_questions(self, admin_client):
        resp = admin_client.get("/admin/generation/batches/batch-qa-data-analysis-v2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["total_questions"] == 32
        assert len(body["data"]["questions"]) == 32

    def test_review_tasks_list(self, admin_client, first_import):
        resp = admin_client.get("/admin/generation/review-tasks")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["total"] == 137

    def test_stats(self, admin_client, first_import):
        resp = admin_client.get("/admin/generation/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["total_generated"] == 137
        # pending_review 可能因前面测试的 approve/reject 而减少，但应 > 0
        assert body["data"]["pending_review"] > 0
        assert body["data"]["batch_count"] == 5
