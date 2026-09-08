"""核心业务闭环测试：答题→错题→SRS 复习、套卷交卷、签到积分、管理端 RBAC、资料练习。

使用独立临时库，避免污染开发库。须在导入 app 之前设置 DATABASE_URL。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import timedelta
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_core_loops.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["ALLOW_REGISTER"] = "true"
os.environ["SECRET_KEY"] = "core-loops-test-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin123"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    AdminUser,
    AppUser,
    Article,
    Base,
    ContentPublishPackage,
    DailyLearningTask,
    ExamPaper,
    ExamQuestion,
    Question,
    RmrbArticle,
    Role,
    ShenlunTeachingExample,
    UserDailyTaskProgress,
    WrongAnswer,
)
from app.timezone import now, today  # noqa: E402

# 本文件会在进入 TestClient 生命周期前直接写入测试数据，先显式建表，
# 保证单独运行该测试文件时不依赖其他测试留下的数据库结构。
Base.metadata.create_all(bind=engine)


def _ok(res):
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("code") == 0, body
    return body.get("data")


def _register(client: TestClient) -> dict:
    username = f"u_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    auth = _ok(
        client.post(
            "/api/auth/register",
            json={"username": username, "password": password, "passwordConfirm": password},
        )
    )
    return {
        "username": username,
        "headers": {"Authorization": f"Bearer {auth['access_token']}"},
    }


def _user_id(username: str) -> str:
    with SessionLocal() as db:
        user = db.query(AppUser).filter(AppUser.username == username).first()
        assert user is not None
        return user.id


def _insert_article_with_question(article_id: str, question_id: str) -> None:
    with SessionLocal() as db:
        db.add(
            Article(
                id=article_id,
                title="测试文章",
                source="测试",
                publish_date="2026-08-14",
                summary="摘要",
                content="内容",
                sections="[]",
                tags="[]",
                status="published",
                allow_quiz=True,
                is_published=True,
            )
        )
        db.add(
            Question(
                id=question_id,
                article_id=article_id,
                type="single",
                stem="1+1=?",
                options=json.dumps(["1", "2", "3", "4"]),
                correct_answer="2",
                analysis="解析",
                status="approved",
                origin="manual",
                is_active=True,
            )
        )
        db.commit()


def _force_due(user_id: str, question_id: str) -> None:
    with SessionLocal() as db:
        row = (
            db.query(WrongAnswer)
            .filter(WrongAnswer.user_id == user_id, WrongAnswer.question_id == question_id)
            .first()
        )
        assert row is not None, "错题记录不存在，无法推进复习"
        row.next_review_at = now() - timedelta(days=1)
        db.commit()


def test_quiz_wrong_review_srs_loop():
    """答题 → 错题 → 艾宾浩斯复习推进 → 掌握移除。"""
    _insert_article_with_question("art-loop-1", "q-loop-1")
    with TestClient(app) as client:
        user = _register(client)
        headers = user["headers"]

        questions = _ok(
            client.get("/api/questions", params={"articleId": "art-loop-1"}, headers=headers)
        )
        assert len(questions) == 1
        qid = questions[0]["id"]

        # 答错：进错题本，第 0 档
        wrong = _ok(client.post("/api/answer", json={"questionId": qid, "answer": "1"}, headers=headers))
        assert wrong["correct"] is False and wrong["pointsEarned"] == 0
        wrongs = _ok(client.get("/api/wrong", params={"status": "all"}, headers=headers))
        row = next(w for w in wrongs if w["question"]["id"] == qid)
        assert row["reviewStage"] == 0 and row["wrongCount"] == 1

        # 首次答对：推进一档 + 复习积分
        redo = _ok(client.post("/api/wrong/redo", json={"questionId": qid, "answer": "2"}, headers=headers))
        assert redo["correct"] is True and redo["pointsEarned"] == 3
        wrongs = _ok(client.get("/api/wrong", params={"status": "all"}, headers=headers))
        assert next(w for w in wrongs if w["question"]["id"] == qid)["reviewStage"] == 1

        # 逐档答对直至掌握（第 6 档移除）
        uid = _user_id(user["username"])
        for _ in range(8):
            with SessionLocal() as db:
                exists = (
                    db.query(WrongAnswer)
                    .filter(WrongAnswer.user_id == uid, WrongAnswer.question_id == qid)
                    .first()
                )
                if exists is None:
                    break
                exists.next_review_at = now() - timedelta(days=1)
                db.commit()
            redo = _ok(client.post("/api/wrong/redo", json={"questionId": qid, "answer": "2"}, headers=headers))
            assert redo["correct"] is True

        wrongs = _ok(client.get("/api/wrong", params={"status": "all"}, headers=headers))
        assert all(w["question"]["id"] != qid for w in wrongs), "掌握后错题应被移除"

        # 积分流水含复习记录
        log = _ok(client.get("/api/points/log", headers=headers))
        assert any(item["source"] == "复习" for item in log)


def test_exam_paper_loop():
    """套卷：开考 → 逐题作答 → 交卷判分 → 历史记录。"""
    with SessionLocal() as db:
        db.add(
            ExamPaper(
                id="paper-loop-1",
                title="测试套卷",
                exam_type="mock",
                subject="行测",
                total_count=2,
                is_published=True,
            )
        )
        db.add(
            ExamQuestion(
                id="eq-loop-1",
                paper_id="paper-loop-1",
                section="常识判断",
                sort_order=1,
                stem="题1：下列哪个是 1？",
                options=json.dumps(["A", "B", "C"]),
                correct_answer="A",
                analysis="A 正确",
                is_active=True,
            )
        )
        db.add(
            ExamQuestion(
                id="eq-loop-2",
                paper_id="paper-loop-1",
                section="常识判断",
                sort_order=2,
                stem="题2：下列哪个是 3？",
                options=json.dumps(["A", "B", "C"]),
                correct_answer="C",
                analysis="C 正确",
                is_active=True,
            )
        )
        db.commit()

    with TestClient(app) as client:
        user = _register(client)
        headers = user["headers"]

        papers = _ok(client.get("/api/exam/papers", headers=headers))
        assert any(p["id"] == "paper-loop-1" for p in papers)
        detail = _ok(client.get("/api/exam/paper/paper-loop-1", headers=headers))
        assert detail["totalCount"] == 2

        started = _ok(client.post("/api/exam/start/paper-loop-1", headers=headers))
        attempt_id = started["attemptId"]
        assert len(started["questions"]) == 2

        _ok(
            client.post(
                "/api/exam/answer",
                params={"attempt_id": attempt_id},
                json={"questionId": "eq-loop-1", "answer": "A", "timeUsedSec": 10},
                headers=headers,
            )
        )
        _ok(
            client.post(
                "/api/exam/answer",
                params={"attempt_id": attempt_id},
                json={"questionId": "eq-loop-2", "answer": "B", "timeUsedSec": 15},
                headers=headers,
            )
        )

        result = _ok(client.post("/api/exam/submit", params={"attempt_id": attempt_id}, headers=headers))
        assert result["isFinished"] is True
        assert result["totalCount"] == 2
        assert result["answeredCount"] == 2
        assert result["correctCount"] == 1
        assert result["score"] == 1

        attempts = _ok(client.get("/api/exam/attempts", headers=headers))
        assert any(a["id"] == attempt_id for a in attempts)
        attempt = _ok(client.get(f"/api/exam/attempt/{attempt_id}", headers=headers))
        assert attempt["correctCount"] == 1


def test_signin_points_flow():
    """签到 → 积分入账 → 重复签到被拦截。"""
    with TestClient(app) as client:
        user = _register(client)
        headers = user["headers"]

        sign = _ok(client.post("/api/signin", headers=headers))
        assert sign["streak"] == 1 and sign["points"] == 5

        again = client.post("/api/signin", headers=headers)
        assert again.status_code == 200
        assert again.json()["code"] == 400

        assert _ok(client.get("/api/points", headers=headers)) == 5
        log = _ok(client.get("/api/points/log", headers=headers))
        assert any(item["source"] == "签到" and item["amount"] == 5 for item in log)


def test_admin_rbac():
    """管理端 RBAC：超管可读写，只读角色读可、写被 403。"""
    with TestClient(app) as client:
        login = _ok(
            client.post(
                "/admin/auth/login",
                json={"username": "admin", "password": "admin123"},
            )
        )
        assert login["role"] == "super_admin"
        assert "article:write" in login["permissions"]
        admin_headers = {"Authorization": f"Bearer {login['access_token']}"}
        articles = _ok(client.get("/admin/articles", headers=admin_headers))
        assert isinstance(articles, dict) and "items" in articles

        templates = _ok(client.get("/admin/content-ops/templates", headers=admin_headers))
        assert len(templates) == 10
        review_config = _ok(client.get("/admin/content-ops/review-config", headers=admin_headers))
        assert [stage["key"] for stage in review_config["stages"]] == ["teaching", "operations"]
        assert len(review_config["stages"][0]["checklist"]) == 3
        assert len(review_config["stages"][1]["checklist"]) == 5
        reference_library = _ok(client.get("/admin/content-ops/reference-library", headers=admin_headers))
        assert [platform["key"] for platform in reference_library["platforms"]] == ["wechat", "xiaohongshu"]
        assert reference_library["platforms"][0]["sourceStatus"] == "knowledge_base_verified"
        assert reference_library["platforms"][1]["sourceStatus"] == "derived_from_repository_plan"
        theory_template = next(item for item in templates if item["code"] == "theory_current")
        assert theory_template["channels"] == ["wechat", "xiaohongshu", "zhihu", "wechat_channels"]
        content_suffix = uuid.uuid4().hex[:8]
        content_article_id = f"art-ops-{content_suffix}"
        with SessionLocal() as db:
            db.add(Article(
                id=content_article_id, title="时政学习运营测试", source="学习材料", publish_date=today(),
                summary="用于验证内容入口。", content="围绕重点内容开展结构化学习。",
                status="published", allow_quiz=True, is_published=True,
            ))
            for index in range(5):
                db.add(Question(
                    id=f"q-ops-{content_suffix}-{index}", article_id=content_article_id, type="single",
                    stem=f"第 {index + 1} 题", options=json.dumps(["正确项", "干扰项"], ensure_ascii=False),
                    correct_answer="正确项", analysis="依据原文可判断。", source_sentence="围绕重点内容开展结构化学习。",
                    status="approved", origin="manual", is_active=True,
                ))
            db.commit()
        articles = _ok(client.get("/admin/articles", headers=admin_headers))
        published_article = next(item for item in articles["items"] if item["id"] == content_article_id)
        article_questions = _ok(client.get(f"/admin/questions?article_id={published_article['id']}&page_size=200", headers=admin_headers))["items"]
        _ok(client.put(
            f"/admin/theory-learning/entries/{published_article['id']}",
            headers=admin_headers,
            json={
                "title": published_article["title"], "description": "运营入口", "isDaily": True, "isEvergreen": False,
                "parts": [{"title": "今日五题", "questionIds": [item["id"] for item in article_questions[:5]]}],
                "collectionEnabled": False, "status": "published", "publishStart": "", "publishEnd": "", "sortOrder": 1,
            },
        ))
        theory_target = _ok(client.get("/admin/content-ops/entry-targets?productKey=theory", headers=admin_headers))[0]
        theory_entry_target = {
            "topicType": "daily", "entryId": theory_target["entryId"], "h5Path": theory_target["h5Path"],
            "miniappPath": theory_target["miniappPath"], "qrScene": "theory_core_loop", "officialAccountKeyword": "时政",
        }
        generated_package = _ok(
            client.post(
                "/admin/content-ops/packages/generate-from-article",
                headers=admin_headers,
                json={
                    "productKey": "theory",
                    "templateId": theory_template["id"],
                    "articleId": published_article["id"],
                    "campaignKey": "theory-auto-20260823",
                    "deepLink": theory_target["h5Path"],
                    "entryTarget": theory_entry_target,
                },
            )
        )
        assert generated_package["sourceType"] == "article"
        assert generated_package["slotValues"]["事实"]
        assert generated_package["slotValues"]["考法"]
        assert "channel=wechat" in generated_package["variants"]["wechat"]["ctaLink"]
        assert "product=theory" in generated_package["variants"]["wechat"]["ctaLink"]
        generated_review = client.post(
            f"/admin/content-ops/packages/{generated_package['id']}/status",
            headers=admin_headers,
            json={"status": "teaching_review"},
        )
        assert generated_review.json()["code"] == 0
        duplicate_generation = client.post(
            "/admin/content-ops/packages/generate-from-article",
            headers=admin_headers,
            json={
                "productKey": "theory",
                "templateId": theory_template["id"],
                "articleId": published_article["id"],
                "campaignKey": "theory-auto-20260823",
            },
        )
        assert duplicate_generation.json()["code"] == 400

        shenlun_template = next(item for item in templates if item["code"] == "shenlun_three_cut")
        rmrb_article = _ok(
            client.post(
                "/admin/rmrb/article",
                headers=admin_headers,
                json={
                    "title": "基层治理学习材料",
                    "source": "人民日报",
                    "sourceUrl": "https://paper.people.com.cn/test-shenlun",
                    "publishDate": "2026-08-20",
                    "summary": "深入一线了解群众诉求，因地制宜提升基层治理效能。",
                    "content": "学习基层治理既要摸清真实情况，也要真诚联系群众，并依据不同地区特点精准施策。",
                    "tags": ["基层治理", "群众路线"],
                },
            )
        )
        assert rmrb_article["sourceUrl"].startswith("https://paper.people.com.cn/")
        with SessionLocal() as db:
            db.add(ShenlunTeachingExample(
                article_id=rmrb_article["id"], version="1", source_excerpt="基层治理学习材料节选。",
                argument_json=json.dumps({
                    "overview": "从调研到精准施策", "conclusion": "以务实行动提升治理效能",
                    "points": [{"title": "深入调研", "claim": "摸清诉求", "evidence": "深入一线了解群众诉求", "summary": "以调研支撑施策", "method": "举例论证", "methodNote": "事实支撑判断", "template": "既要……也要……"}],
                }, ensure_ascii=False),
                terms_json=json.dumps([{"term": "因地制宜", "category": "方法"}], ensure_ascii=False),
                quotes_json="[]", verbs_json="[]",
                templates_json=json.dumps([{"type": "并列句", "original": "原句", "template": "既要……也要……", "imitate": "既要摸清诉求，也要精准施策。"}], ensure_ascii=False),
                practice_json=json.dumps({"prompt": "概括治理方法。", "minLength": 10, "maxLength": 100, "checks": ["对象清楚"], "referenceAnswer": "深入调研群众诉求，因地制宜精准施策。"}, ensure_ascii=False),
                status="published",
            ))
            db.commit()
        shenlun_target = _ok(client.get("/admin/content-ops/entry-targets?productKey=shenlun", headers=admin_headers))[0]
        shenlun_entry_target = {
            "topicType": "daily", "entryId": shenlun_target["entryId"], "h5Path": shenlun_target["h5Path"],
            "miniappPath": shenlun_target["miniappPath"], "qrScene": "shenlun_core_loop", "officialAccountKeyword": "申论",
        }
        shenlun_generated = _ok(
            client.post(
                "/admin/content-ops/packages/generate-from-article",
                headers=admin_headers,
                json={
                    "productKey": "shenlun",
                    "templateId": shenlun_template["id"],
                    "articleId": rmrb_article["id"],
                    "campaignKey": "shenlun-auto-20260820",
                    "deepLink": shenlun_target["h5Path"],
                    "entryTarget": shenlun_entry_target,
                },
            )
        )
        assert shenlun_generated["sourceType"] == "rmrb_article"
        assert all(shenlun_generated["slotValues"].values())
        assert "channel=wechat" in shenlun_generated["variants"]["wechat"]["ctaLink"]
        package = _ok(
            client.post(
                "/admin/content-ops/packages",
                headers=admin_headers,
                json={
                    "productKey": "shenlun",
                    "templateId": shenlun_template["id"],
                    "sourceType": shenlun_target["sourceType"],
                    "sourceId": shenlun_target["sourceId"],
                    "sourceTitle": "今日三刀训练",
                    "campaignKey": "xhs-20260823",
                    "deepLink": shenlun_target["h5Path"],
                    "entryTarget": shenlun_entry_target,
                    "plannedAt": (now() + timedelta(days=1)).isoformat(),
                    "variants": {
                        "xiaohongshu": {"title": "一篇时评怎么拆", "body": "从原文学习治理表达。", "slides": ["封面", "骨架"]},
                        "wechat": {"title": "今日申论学习包", "body": "从原文学习治理表达。"},
                    },
                },
            )
        )
        assert package["status"] == "draft"

        package = _ok(
            client.put(
                f"/admin/content-ops/packages/{package['id']}",
                headers=admin_headers,
                json={
                    "sourceTitle": "今日三刀训练（已编辑）",
                    "variants": {
                        "wechat": {"title": "今日申论学习包", "body": "审核前正文"},
                    },
                },
            )
        )
        assert package["sourceTitle"].endswith("（已编辑）")
        assert list(package["variants"]) == ["wechat"]

        missing_slots = client.post(
            f"/admin/content-ops/packages/{package['id']}/status",
            headers=admin_headers,
            json={"status": "teaching_review"},
        )
        assert missing_slots.json()["code"] == 400
        package = _ok(
            client.put(
                f"/admin/content-ops/packages/{package['id']}",
                headers=admin_headers,
                json={"slotValues": {slot: f"{slot}内容" for slot in shenlun_template["slots"]}},
            )
        )
        assert len(package["slotValues"]) == len(shenlun_template["slots"])
        preflight = _ok(client.get(f"/admin/content-ops/packages/{package['id']}/preflight", headers=admin_headers))
        assert preflight["passed"] is True
        assert preflight["resolvedEntry"]["entryId"] == rmrb_article["id"]

        invalid_publish = client.post(
            f"/admin/content-ops/packages/{package['id']}/status",
            headers=admin_headers,
            json={"status": "published"},
        )
        assert invalid_publish.json()["code"] == 400
        package = _ok(
            client.post(
                f"/admin/content-ops/packages/{package['id']}/status",
                headers=admin_headers,
                json={"status": "teaching_review", "reviewNote": "送教研"},
            )
        )
        locked_edit = client.put(
            f"/admin/content-ops/packages/{package['id']}",
            headers=admin_headers,
            json={"sourceTitle": "审核中不允许修改"},
        )
        assert locked_edit.json()["code"] == 400
        locked_export = client.get(
            f"/admin/content-ops/packages/{package['id']}/export",
            headers=admin_headers,
        )
        assert locked_export.json()["code"] == 400
        incomplete_teaching_review = client.post(
            f"/admin/content-ops/packages/{package['id']}/status",
            headers=admin_headers,
            json={"status": "ops_review", "reviewNote": "遗漏审核清单"},
        )
        assert incomplete_teaching_review.json()["code"] == 400
        review_checklists = {
            "ops_review": {
                "facts_accurate": True,
                "qualifiers_complete": True,
                "exercise_assessable": True,
            },
            "ready": {
                "opening_clear": True,
                "platform_fit": True,
                "visuals_ready": True,
                "cta_verified": True,
                "compliance_checked": True,
            },
        }
        for status in ("ops_review", "ready", "published"):
            package = _ok(
                client.post(
                    f"/admin/content-ops/packages/{package['id']}/status",
                    headers=admin_headers,
                    json={"status": status, "reviewNote": f"{status} ok", "checklist": review_checklists.get(status, {})},
                )
            )
            if status == "ops_review":
                assert package["reviewHistory"][-1]["stage"] == "teaching"
                assert package["reviewHistory"][-1]["reviewerUsername"] == "admin"
                with SessionLocal() as db:
                    stored_package = db.get(ContentPublishPackage, package["id"])
                    original_target = stored_package.entry_target_json
                    stored_package.entry_target_json = "{}"
                    db.commit()
                blocked_ready = client.post(
                    f"/admin/content-ops/packages/{package['id']}/status", headers=admin_headers,
                    json={"status": "ready", "reviewNote": "入口失效不得通过", "checklist": review_checklists["ready"]},
                )
                assert blocked_ready.json()["code"] == 400
                with SessionLocal() as db:
                    stored_package = db.get(ContentPublishPackage, package["id"])
                    stored_package.entry_target_json = original_target
                    db.commit()
            if status == "ready":
                assert [item["stage"] for item in package["reviewHistory"]] == ["teaching", "operations"]
            if status == "ready":
                publish_bundle = _ok(
                    client.get(
                        f"/admin/content-ops/packages/{package['id']}/export",
                        headers=admin_headers,
                    )
                )
                assert publish_bundle["schemaVersion"] == "content-publish-package/v2"
                assert publish_bundle["preflight"]["passed"] is True
                assert publish_bundle["channels"][0]["manualPublishRequired"] is True
                with SessionLocal() as db:
                    example = db.query(ShenlunTeachingExample).filter(ShenlunTeachingExample.article_id == rmrb_article["id"]).first()
                    example.status = "draft"
                    db.commit()
                stale_export = client.get(f"/admin/content-ops/packages/{package['id']}/export", headers=admin_headers)
                assert stale_export.json()["code"] == 400
                with SessionLocal() as db:
                    example = db.query(ShenlunTeachingExample).filter(ShenlunTeachingExample.article_id == rmrb_article["id"]).first()
                    example.status = "published"
                    db.commit()
        assert package["status"] == "published" and package["publishedAt"]
        ops_overview = _ok(client.get("/admin/content-ops/overview", headers=admin_headers))
        assert ops_overview["windowDays"] == 7
        assert ops_overview["statusCounts"]["published"] >= 1
        assert ops_overview["reviewBacklog"] >= 1
        assert "product_mix_empty" in {item["code"] for item in ops_overview["alerts"]}

        # 新建只读管理员
        with SessionLocal() as db:
            role = db.query(Role).filter(Role.code == "viewer").first()
            assert role is not None
            viewer_name = f"viewer_{uuid.uuid4().hex[:6]}"
            db.add(
                AdminUser(
                    username=viewer_name,
                    password_hash=hash_password("Viewer123!"),
                    nickname="只读",
                    role_id=role.id,
                )
            )
            db.commit()

        v_login = _ok(
            client.post(
                "/admin/auth/login",
                json={"username": viewer_name, "password": "Viewer123!"},
            )
        )
        v_headers = {"Authorization": f"Bearer {v_login['access_token']}"}
        assert v_login["role"] == "viewer"
        assert "article:write" not in v_login["permissions"]

        # 读接口可访问
        _ok(client.get("/admin/articles", headers=v_headers))
        _ok(client.get("/admin/content-ops/templates", headers=v_headers))

        # 写接口被 403 拦截
        denied = client.post(
            "/admin/articles",
            headers=v_headers,
            json={"title": "越权", "source": "x", "publish_date": "2026-08-14", "summary": "x"},
        )
        assert denied.status_code == 403, denied.text


def test_ziliao_drill_submit_and_stats():
    """资料分析：样例练习组 → 提交判分 → 今日统计。"""
    with TestClient(app) as client:
        user = _register(client)
        headers = user["headers"]

        sets = _ok(
            client.get(
                "/api/ziliao/drill/sets",
                params={"includeSample": "true"},
                headers=headers,
            )
        )
        assert sets, "样例练习组未初始化"
        sample = next(s for s in sets if s["isSample"])
        detail = _ok(client.get(f"/api/ziliao/drill/set/{sample['setId']}", headers=headers))
        questions = detail["questions"]
        assert questions

        with SessionLocal() as db:
            rows = (
                db.query(ExamQuestion)
                .filter(ExamQuestion.id.in_([q["id"] for q in questions]))
                .all()
            )
            correct_map = {r.id: r.correct_answer for r in rows}

        total = len(questions)
        answers = [
            {"questionId": q["id"], "userAnswer": correct_map[q["id"]]}
            for q in questions
        ]
        # 第一题故意答错（换一个选项）
        first = questions[0]
        wrong_option = next(
            opt for opt in first["options"] if opt != correct_map[first["id"]]
        )
        answers[0]["userAnswer"] = wrong_option

        result = _ok(
            client.post(
                "/api/ziliao/drill/submit",
                json={"setId": sample["setId"], "answers": answers, "timeUsedSec": 42},
                headers=headers,
            )
        )
        assert result["totalCount"] == total
        assert result["correctCount"] == total - 1
        assert len(result["wrongs"]) == 1

        overview = _ok(client.get("/api/ziliao/overview", headers=headers))
        assert overview["todaySets"] >= 1
        assert overview["todayTotal"] >= total
        assert overview["todayCorrect"] >= total - 1


def test_daily_task_state_machine_and_product_isolation():
    """今日任务：按产品隔离，草稿可恢复，状态只能顺序推进。"""
    task_date = "2026-08-23"
    with TestClient(app) as client:
        user = _register(client)
        shenlun_headers = {**user["headers"], "X-Product-Key": "shenlun"}
        theory_headers = {**user["headers"], "X-Product-Key": "theory"}

        with SessionLocal() as db:
            db.add_all(
                [
                    DailyLearningTask(
                        id="dlt-shenlun-loop",
                        product_key="shenlun",
                        task_date=task_date,
                        task_type="daily_training",
                        title="今日三刀训练",
                        description="精读并完成概括",
                        content_type="rmrb_article",
                        content_id="rmrb-test",
                        estimated_minutes=15,
                        total_steps=5,
                        status="published",
                    ),
                    DailyLearningTask(
                        id="dlt-theory-loop",
                        product_key="theory",
                        task_date=task_date,
                        task_type="daily_pack",
                        title="今日政治理论",
                        estimated_minutes=12,
                        total_steps=4,
                        status="published",
                    ),
                ]
            )
            db.commit()

        shenlun = _ok(
            client.get(
                "/api/product/daily-tasks",
                params={"date": task_date},
                headers=shenlun_headers,
            )
        )
        assert shenlun["productKey"] == "shenlun"
        assert [task["id"] for task in shenlun["tasks"]] == ["dlt-shenlun-loop"]
        assert shenlun["tasks"][0]["progress"]["state"] == "not_started"

        theory = _ok(
            client.get(
                "/api/product/daily-tasks",
                params={"date": task_date},
                headers=theory_headers,
            )
        )
        assert [task["id"] for task in theory["tasks"]] == ["dlt-theory-loop"]

        started = _ok(
            client.post(
                "/api/product/daily-tasks/dlt-shenlun-loop/progress",
                headers=shenlun_headers,
                json={"event": "start"},
            )
        )
        assert started["progress"]["state"] == "in_progress"

        saved = _ok(
            client.post(
                "/api/product/daily-tasks/dlt-shenlun-loop/progress",
                headers=shenlun_headers,
                json={
                    "event": "save",
                    "currentStep": 2,
                    "draft": {"answer": "基层协同机制仍需完善"},
                },
            )
        )
        assert saved["progress"]["currentStep"] == 2

        restored = _ok(
            client.get(
                "/api/product/daily-tasks",
                params={"date": task_date},
                headers=shenlun_headers,
            )
        )
        progress = restored["tasks"][0]["progress"]
        assert progress["state"] == "in_progress"
        assert progress["draft"]["answer"] == "基层协同机制仍需完善"

        invalid = client.post(
            "/api/product/daily-tasks/dlt-shenlun-loop/progress",
            headers=shenlun_headers,
            json={"event": "complete"},
        )
        assert invalid.status_code == 200
        assert invalid.json()["code"] == 400

        for event, expected in (
            ("submit", "submitted"),
            ("review", "reviewed"),
            ("complete", "completed"),
        ):
            updated = _ok(
                client.post(
                    "/api/product/daily-tasks/dlt-shenlun-loop/progress",
                    headers=shenlun_headers,
                    json={"event": event},
                )
            )
            assert updated["progress"]["state"] == expected

        completed = _ok(
            client.get(
                "/api/product/daily-tasks",
                params={"date": task_date},
                headers=shenlun_headers,
            )
        )
        assert completed["completion"] == 100
        assert completed["completedCount"] == 1

        cross_product = client.post(
            "/api/product/daily-tasks/dlt-shenlun-loop/progress",
            headers=theory_headers,
            json={"event": "start"},
        )
        assert cross_product.status_code == 200
        assert cross_product.json()["code"] == 400


def test_shenlun_home_provisions_one_daily_article_task():
    """申论首页为今日选择一篇已审核文章，重复加载不重复编排。"""
    task_date = today()
    with TestClient(app) as client:
        user = _register(client)
        headers = {**user["headers"], "X-Product-Key": "shenlun"}
        with SessionLocal() as db:
            existing_ids = [
                row[0]
                for row in db.query(DailyLearningTask.id).filter(
                    DailyLearningTask.product_key == "shenlun",
                    DailyLearningTask.task_date == task_date,
                )
            ]
            if existing_ids:
                db.query(UserDailyTaskProgress).filter(
                    UserDailyTaskProgress.task_id.in_(existing_ids)
                ).delete(synchronize_session=False)
            db.query(DailyLearningTask).filter(
                DailyLearningTask.product_key == "shenlun",
                DailyLearningTask.task_date == task_date,
            ).delete(synchronize_session=False)
            db.add(
                RmrbArticle(
                    id="rmrb-daily-home",
                    title="以务实行动答好民生考题",
                    source="人民时评",
                    publish_date=task_date,
                    summary="从群众关切出发，把好事实事办到心坎上。",
                    content="测试文章正文",
                    tags='["民生", "基层治理"]',
                    is_published=True,
                    sort_order=999,
                )
            )
            db.commit()

        first = _ok(client.get("/api/product/daily-tasks", headers=headers))
        second = _ok(client.get("/api/product/daily-tasks", headers=headers))

        assert first["date"] == task_date
        assert first["totalCount"] == 1
        assert second["totalCount"] == 1
        task = first["tasks"][0]
        assert task["taskType"] == "shenlun_article_training"
        assert task["contentId"] == "rmrb-daily-home"
        assert task["totalSteps"] == 4
        assert task["metadata"]["tags"] == ["民生", "基层治理"]
        assert task["metadata"]["question"]["maxLength"] == 120
        assert len(task["metadata"]["question"]["checks"]) == 3


def test_theory_home_only_provisions_evidence_backed_pack():
    """政治理论学习包至少含3道已审核且有原文依据的题。"""
    task_date = today()
    with TestClient(app) as client:
        user = _register(client)
        headers = {**user["headers"], "X-Product-Key": "theory"}
        with SessionLocal() as db:
            existing_ids = [
                row[0]
                for row in db.query(DailyLearningTask.id).filter(
                    DailyLearningTask.product_key == "theory",
                    DailyLearningTask.task_date == task_date,
                )
            ]
            if existing_ids:
                db.query(UserDailyTaskProgress).filter(
                    UserDailyTaskProgress.task_id.in_(existing_ids)
                ).delete(synchronize_session=False)
                db.query(DailyLearningTask).filter(
                    DailyLearningTask.id.in_(existing_ids)
                ).delete(synchronize_session=False)
            article = Article(
                id="art-theory-daily",
                title="准确把握高质量发展的实践要求",
                source="权威理论文章",
                publish_date=task_date,
                summary="理解主体、目标和政策边界。",
                content="理论文章正文",
                sections="[]",
                tags='["高质量发展", "新发展理念"]',
                status="published",
                allow_quiz=True,
                is_published=True,
                is_daily=True,
                importance=5,
            )
            db.add(article)
            for index in range(3):
                db.add(
                    Question(
                        id=f"q-theory-evidence-{index}",
                        article_id=article.id,
                        type="single",
                        stem=f"第{index + 1}道审核题",
                        options='["A", "B"]',
                        correct_answer='"A"',
                        analysis="依据原文可知。",
                        source_sentence=f"原文依据{index + 1}",
                        status="approved",
                        origin="manual",
                        is_active=True,
                    )
                )
            db.add(
                Question(
                    id="q-theory-without-evidence",
                    article_id=article.id,
                    type="single",
                    stem="尚未补齐依据的题目",
                    options='["A", "B"]',
                    correct_answer='"A"',
                    analysis="待补依据。",
                    source_sentence="",
                    status="approved",
                    origin="manual",
                    is_active=True,
                )
            )
            db.commit()

        first = _ok(client.get("/api/product/daily-tasks", headers=headers))
        second = _ok(client.get("/api/product/daily-tasks", headers=headers))

        assert first["totalCount"] == 1
        assert second["totalCount"] == 1
        task = first["tasks"][0]
        assert task["taskType"] == "theory_daily_pack"
        assert task["contentId"] == "art-theory-daily"
        assert task["metadata"]["questionCount"] == 3
        assert task["metadata"]["evidenceCount"] == 3
        assert task["metadata"]["focuses"] == ["高质量发展", "新发展理念"]

        theory_questions = _ok(
            client.get(
                "/api/questions",
                params={"articleId": "art-theory-daily"},
                headers=headers,
            )
        )
        general_questions = _ok(
            client.get(
                "/api/questions",
                params={"articleId": "art-theory-daily"},
                headers={**user["headers"], "X-Product-Key": "general"},
            )
        )
        assert len(theory_questions) == 3
        assert len(general_questions) == 4


def test_product_topics_served_and_switchable():
    """专题下发：默认只给方法类专题，管理端改设置即可切换，无需发版。"""
    with TestClient(app) as client:
        user = _register(client)
        theory_headers = {**user["headers"], "X-Product-Key": "theory"}
        shenlun_headers = {**user["headers"], "X-Product-Key": "shenlun"}

        theory = _ok(client.get("/api/product/topics", headers=theory_headers))
        assert theory["productKey"] == "theory"
        titles = [t["title"] for t in theory["items"]]
        assert titles == ["理论文章怎么读", "易混表述辨析", "规范表述积累"]

        # 提审期红线：默认专题不得出现政治专题名与「时政」字样
        blob = json.dumps(theory, ensure_ascii=False)
        for word in ("习近平", "马克思主义", "党和国家", "时政"):
            assert word not in blob

        # 按产品隔离：申论拿到自己的方法专题
        shenlun = _ok(client.get("/api/product/topics", headers=shenlun_headers))
        assert shenlun["items"][0]["title"] == "材料怎么拆"

        # 管理端改设置 → 立即切换，不需要发版或重启
        admin_login = _ok(
            client.post(
                "/admin/auth/login",
                json={"username": "admin", "password": "admin123"},
            )
        )
        admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}
        switched_value = json.dumps(
            [{"no": "新", "title": "新时代中国特色社会主义思想", "desc": "体系化学习核心要义"}],
            ensure_ascii=False,
        )
        _ok(
            client.put(
                "/admin/settings/topics.theory",
                headers=admin_headers,
                json={"value": switched_value},
            )
        )
        switched = _ok(client.get("/api/product/topics", headers=theory_headers))
        assert [t["title"] for t in switched["items"]] == ["新时代中国特色社会主义思想"]

        # 配置写坏时回落默认，保证前端不出现空页
        _ok(
            client.put(
                "/admin/settings/topics.theory",
                headers=admin_headers,
                json={"value": "not-json"},
            )
        )
        fallback = _ok(client.get("/api/product/topics", headers=theory_headers))
        assert [t["title"] for t in fallback["items"]] == titles


def test_feedback_persisted_and_handled_by_admin():
    """反馈：学员提交真实落库，管理端查看并显式采纳加分（不再随机判定）。"""
    with TestClient(app) as client:
        user = _register(client)
        theory_headers = {**user["headers"], "X-Product-Key": "theory"}

        submitted = _ok(
            client.post("/api/feedback", headers=theory_headers, json={"content": "第 3 题答案应为 B"})
        )
        assert submitted["status"] == "new"
        assert submitted["adopted"] is False  # 提交时不再随机送分

        empty = client.post("/api/feedback", headers=theory_headers, json={"content": "   "})
        assert empty.json().get("code") != 0

        admin_login = _ok(
            client.post(
                "/admin/auth/login",
                json={"username": "admin", "password": "admin123"},
            )
        )
        admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

        listing = _ok(
            client.get("/admin/feedbacks", params={"productKey": "theory"}, headers=admin_headers)
        )
        assert listing["total"] >= 1
        assert listing["items"][0]["content"] == "第 3 题答案应为 B"
        assert listing["items"][0]["productKey"] == "theory"

        before = _ok(client.get("/api/user/me", headers=user["headers"]))
        handled = _ok(
            client.post(
                f"/admin/feedbacks/{submitted['id']}/handle",
                headers=admin_headers,
                json={"action": "adopted", "note": "已修正", "points": 10},
            )
        )
        assert handled["status"] == "adopted"
        after = _ok(client.get("/api/user/me", headers=user["headers"]))
        assert after["points"] == before["points"] + 10

        again = client.post(
            f"/admin/feedbacks/{submitted['id']}/handle",
            headers=admin_headers,
            json={"action": "rejected"},
        )
        assert again.status_code == 400


def test_admin_password_change():
    """管理员自助改密：强度校验 + 旧密码验证 + 改后旧口令失效。

    测试库为模块共享，结束前把口令改回默认值，避免影响其他用例。
    """
    new_password = "N3wStrongPwd"
    with TestClient(app) as client:
        login = _ok(
            client.post("/admin/auth/login", json={"username": "admin", "password": "admin123"})
        )
        headers = {"Authorization": f"Bearer {login['access_token']}"}

        wrong_old = client.put(
            "/admin/auth/password",
            headers=headers,
            json={"oldPassword": "nope", "newPassword": new_password},
        )
        assert wrong_old.json().get("code") == 401

        weak = client.put(
            "/admin/auth/password",
            headers=headers,
            json={"oldPassword": "admin123", "newPassword": "abcdefgh"},
        )
        assert weak.status_code == 422  # 无数字，强度校验不通过

        same = client.put(
            "/admin/auth/password",
            headers=headers,
            json={"oldPassword": "admin123", "newPassword": "admin123"},
        )
        assert same.json().get("code") == 400

        changed = client.put(
            "/admin/auth/password",
            headers=headers,
            json={"oldPassword": "admin123", "newPassword": new_password},
        )
        assert changed.json().get("code") == 0

        stale = client.post("/admin/auth/login", json={"username": "admin", "password": "admin123"})
        assert stale.json().get("code") == 401

        relogin = _ok(
            client.post("/admin/auth/login", json={"username": "admin", "password": new_password})
        )
        assert relogin["role"] == "super_admin"

        restore = client.put(
            "/admin/auth/password",
            headers={"Authorization": f"Bearer {relogin['access_token']}"},
            json={"oldPassword": new_password, "newPassword": "admin123"},
        )
        assert restore.json().get("code") == 0


def teardown_module(_mod=None):
    engine.dispose()
    for path in (_DB, Path(f"{_DB}-shm"), Path(f"{_DB}-wal")):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
