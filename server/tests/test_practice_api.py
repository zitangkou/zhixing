"""Q7 资料分析最小学习闭环 API 测试。

覆盖：6 技能生成、提交判定、错因映射、复习卡汇总、确定性生成。
使用独立临时库，避免污染开发库。
"""
from __future__ import annotations

import os
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_smoke.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["ALLOW_REGISTER"] = "true"
os.environ["SECRET_KEY"] = "practice-test-secret"

from app.config import get_settings

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

SKILLS = ["base_period", "growth_rate", "proportion", "average", "multiple", "mixed_growth"]
DATE = "2026-09-03"


def _ok(res):
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("code") == 0, body
    return body.get("data")


def _collect_question_ids(pkg):
    ids = []
    if pkg.get("method_example"):
        ids.append(pkg["method_example"]["question_id"])
    ids.extend(q["question_id"] for q in pkg.get("progressive", []))
    ids.extend(q["question_id"] for q in pkg.get("material_set", []))
    return ids


def _collect_all_questions(pkg):
    qs = []
    if pkg.get("method_example"):
        qs.append(pkg["method_example"])
    qs.extend(pkg.get("progressive", []))
    qs.extend(pkg.get("material_set", []))
    return qs


class TestPracticeSkills:
    def test_list_skills(self):
        with TestClient(app) as client:
            data = _ok(client.get("/api/practice/skills"))
            assert len(data) == 6
            skill_keys = {s["skill"] for s in data}
            assert skill_keys == set(SKILLS)

    def test_invalid_skill(self):
        with TestClient(app) as client:
            res = client.get("/api/practice/daily", params={"skill": "invalid", "date": DATE})
            assert res.status_code == 200
            body = res.json()
            assert body["code"] != 0


class TestDailyPackage:
    def test_all_skills_generate(self):
        with TestClient(app) as client:
            for skill in SKILLS:
                pkg = _ok(client.get("/api/practice/daily", params={"skill": skill, "date": DATE}))
                assert pkg["skill"] == skill
                assert pkg["daily_id"] == f"practice-{skill}-{DATE}"
                assert pkg["total_questions"] == 9
                assert pkg["method_example"] is not None
                assert len(pkg["progressive"]) == 3
                assert len(pkg["material_set"]) == 5
                # 材料题组共享同一 material_id
                mids = {q["material"]["material_id"] for q in pkg["material_set"]}
                assert len(mids) == 1

    def test_deterministic_generation(self):
        """同一天同一技能，两次请求结果一致。"""
        with TestClient(app) as client:
            pkg1 = _ok(client.get("/api/practice/daily", params={"skill": "base_period", "date": DATE}))
            pkg2 = _ok(client.get("/api/practice/daily", params={"skill": "base_period", "date": DATE}))
            assert _collect_question_ids(pkg1) == _collect_question_ids(pkg2)

    def test_different_date_different_package(self):
        with TestClient(app) as client:
            pkg1 = _ok(client.get("/api/practice/daily", params={"skill": "base_period", "date": "2026-09-03"}))
            pkg2 = _ok(client.get("/api/practice/daily", params={"skill": "base_period", "date": "2026-09-04"}))
            # 不同日期可能题目不同（至少 daily_id 不同）
            assert pkg1["daily_id"] != pkg2["daily_id"]

    def test_progressive_difficulty_labels(self):
        with TestClient(app) as client:
            pkg = _ok(client.get("/api/practice/daily", params={"skill": "base_period", "date": DATE}))
            for q in pkg["progressive"]:
                assert q["difficulty_label"] in ("简单", "中等", "较难")

    def test_question_fields_complete(self):
        with TestClient(app) as client:
            pkg = _ok(client.get("/api/practice/daily", params={"skill": "proportion", "date": DATE}))
            for q in _collect_all_questions(pkg):
                assert "question_id" in q
                assert "stem" in q
                assert "options" in q
                assert "answer" in q
                assert "explanation" in q
                assert "distractors" in q
                assert "calc_tree" in q


class TestSubmitAnswers:
    def test_all_correct(self):
        with TestClient(app) as client:
            pkg = _ok(client.get("/api/practice/daily", params={"skill": "base_period", "date": DATE}))
            daily_id = pkg["daily_id"]
            all_qs = _collect_all_questions(pkg)
            answers = [{"question_id": q["question_id"], "user_answer": q["answer"]} for q in all_qs]
            result = _ok(client.post(f"/api/practice/{daily_id}/submit", json={"answers": answers}))
            assert result["total"] == 9
            assert result["correct_count"] == 9
            assert result["wrong_count"] == 0
            for r in result["results"]:
                assert r["is_correct"] is True
                assert r["error_path"] is None

    def test_all_wrong_with_distractor_mapping(self):
        with TestClient(app) as client:
            pkg = _ok(client.get("/api/practice/daily", params={"skill": "growth_rate", "date": DATE}))
            daily_id = pkg["daily_id"]
            all_qs = _collect_all_questions(pkg)
            # 每道题选第一个干扰项（非正确答案）
            answers = []
            for q in all_qs:
                opts = list(q["options"].keys())
                wrong = [o for o in opts if o != q["answer"]][0]
                answers.append({"question_id": q["question_id"], "user_answer": wrong})
            result = _ok(client.post(f"/api/practice/{daily_id}/submit", json={"answers": answers}))
            assert result["correct_count"] == 0
            assert result["wrong_count"] == 9
            for r in result["results"]:
                assert r["is_correct"] is False
                assert r["error_path"] is not None
                assert r["error_path"]["type"]  # 有错误路径名称
                assert r["error_path"]["correct_formula"]  # 有正确公式提醒

    def test_error_path_matches_distractor(self):
        """错题的错误路径 type 必须与题目 distractors 中对应选项的 type 一致。"""
        with TestClient(app) as client:
            pkg = _ok(client.get("/api/practice/daily", params={"skill": "multiple", "date": DATE}))
            daily_id = pkg["daily_id"]
            all_qs = _collect_all_questions(pkg)
            q_map = {q["question_id"]: q for q in all_qs}
            # 选有干扰项定义的错误选项
            answers = []
            for q in all_qs:
                distractors = q.get("distractors", {})
                wrong_opts = [o for o in distractors.keys() if o != q["answer"]]
                if wrong_opts:
                    answers.append({"question_id": q["question_id"], "user_answer": wrong_opts[0]})
            result = _ok(client.post(f"/api/practice/{daily_id}/submit", json={"answers": answers}))
            for r in result["results"]:
                if not r["is_correct"] and r["error_path"]:
                    q = q_map[r["question_id"]]
                    dist = q["distractors"].get(r["user_answer"])
                    if dist:
                        assert r["error_path"]["type"] == dist["type"]

    def test_submit_nonexistent_daily(self):
        with TestClient(app) as client:
            res = client.post("/api/practice/nonexistent-id/submit", json={"answers": []})
            assert res.status_code == 200
            body = res.json()
            assert body["code"] != 0

    def test_mixed_answers_count(self):
        with TestClient(app) as client:
            pkg = _ok(client.get("/api/practice/daily", params={"skill": "average", "date": DATE}))
            daily_id = pkg["daily_id"]
            all_qs = _collect_all_questions(pkg)
            # 前 4 题正确，后 5 题错误
            answers = []
            for i, q in enumerate(all_qs):
                if i < 4:
                    ua = q["answer"]
                else:
                    opts = list(q["options"].keys())
                    ua = [o for o in opts if o != q["answer"]][0]
                answers.append({"question_id": q["question_id"], "user_answer": ua})
            result = _ok(client.post(f"/api/practice/{daily_id}/submit", json={"answers": answers}))
            assert result["correct_count"] == 4
            assert result["wrong_count"] == 5
            assert result["total"] == 9


class TestReviewCard:
    def test_review_after_submit(self):
        with TestClient(app) as client:
            pkg = _ok(client.get("/api/practice/daily", params={"skill": "mixed_growth", "date": DATE}))
            daily_id = pkg["daily_id"]
            all_qs = _collect_all_questions(pkg)
            # 部分错题
            answers = []
            for i, q in enumerate(all_qs):
                if i % 2 == 0:
                    ua = q["answer"]
                else:
                    opts = list(q["options"].keys())
                    ua = [o for o in opts if o != q["answer"]][0]
                answers.append({"question_id": q["question_id"], "user_answer": ua})
            _ok(client.post(f"/api/practice/{daily_id}/submit", json={"answers": answers}))
            review = _ok(client.get(f"/api/practice/{daily_id}/review"))
            assert review["daily_id"] == daily_id
            assert len(review["review_questions"]) == review["wrong_count"]
            # 错误路径汇总次数之和 = 错题数
            total_ep_count = sum(ep["count"] for ep in review["error_paths"])
            assert total_ep_count == review["wrong_count"]
            # 每个错误路径有正确公式
            for ep in review["error_paths"]:
                assert ep["correct_formula"]

    def test_review_all_correct(self):
        with TestClient(app) as client:
            pkg = _ok(client.get("/api/practice/daily", params={"skill": "proportion", "date": "2026-09-10"}))
            daily_id = pkg["daily_id"]
            all_qs = _collect_all_questions(pkg)
            answers = [{"question_id": q["question_id"], "user_answer": q["answer"]} for q in all_qs]
            _ok(client.post(f"/api/practice/{daily_id}/submit", json={"answers": answers}))
            review = _ok(client.get(f"/api/practice/{daily_id}/review"))
            assert review["wrong_count"] == 0
            assert len(review["error_paths"]) == 0
            assert len(review["review_questions"]) == 0

    def test_review_without_submit(self):
        with TestClient(app) as client:
            res = client.get("/api/practice/practice-base_period-2099-01-01/review")
            assert res.status_code == 200
            body = res.json()
            assert body["code"] != 0
