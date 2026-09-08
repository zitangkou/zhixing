"""时政单篇学习入口编排测试；不涉及试卷。"""

import json

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Article, Question
from app.models.base import Base
from app.api.public.theory_learning_entries import router
from app.database import get_db
from app.services.theory_learning_entry_service import list_public_entries, save_entry


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Article(
            id="a", title="重点学习文章", source="权威材料", publish_date="2026-09-07",
            summary="摘要", content="正文", sections="[]", tags=json.dumps(["长期重点"]),
            status="published", is_published=True, allow_quiz=True,
        ))
        for index in range(6):
            session.add(Question(
                id=f"q{index}", article_id="a", type="single", stem=f"题目{index}",
                options=json.dumps(["甲", "乙"]), correct_answer="甲", analysis="解析",
                source_sentence="原文依据", status="approved", is_active=True,
            ))
        session.commit()
        yield session
    engine.dispose()


def payload(**overrides):
    value = {
        "title": "十五五规划重点学习",
        "description": "长期保留，空档期优先学习",
        "isDaily": True,
        "isEvergreen": True,
        "parts": [
            {"title": "今日 5 题", "questionIds": ["q0", "q1", "q2", "q3", "q4"]},
            {"title": "继续巩固", "questionIds": ["q5"]},
        ],
        "collectionEnabled": True,
        "status": "published",
        "publishStart": "",
        "publishEnd": "",
        "sortOrder": 100,
    }
    value.update(overrides)
    return value


def test_published_entry_controls_public_daily_and_evergreen_lists(db):
    saved = save_entry(db, "a", payload())
    assert saved["questionCount"] == 6
    assert [len(part["questionIds"]) for part in saved["parts"]] == [5, 1]
    public = list_public_entries(db)
    assert public[0]["title"] == "十五五规划重点学习"
    assert public[0]["isDaily"] is True
    assert public[0]["isEvergreen"] is True


def test_public_endpoint_is_anonymous_but_theory_only(db):
    save_entry(db, "a", payload())
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        response = client.get("/learning/entries", headers={"X-Product-Key": "theory"})
        assert response.status_code == 200
        assert response.json()["data"][0]["articleId"] == "a"
        assert client.get("/learning/entries", headers={"X-Product-Key": "shenlun"}).status_code == 404


def test_draft_can_be_prepared_but_never_appears_publicly(db):
    save_entry(db, "a", payload(status="draft", parts=[], collectionEnabled=False))
    assert list_public_entries(db) == []


def test_publish_window_hides_future_or_expired_entry(db):
    save_entry(db, "a", payload(status="draft"))
    save_entry(db, "a", payload(publishStart="2099-01-01"))
    assert list_public_entries(db) == []
    save_entry(db, "a", payload(publishStart="", publishEnd="2020-01-01"))
    assert list_public_entries(db) == []


def test_collection_requires_every_active_question(db):
    incomplete = payload(parts=[{"title": "仅一辑", "questionIds": ["q0", "q1", "q2", "q3", "q4"]}])
    with pytest.raises(HTTPException, match="全部有效题目"):
        save_entry(db, "a", incomplete)
    saved = save_entry(db, "a", {**incomplete, "collectionEnabled": False})
    assert saved["collectionEnabled"] is False


@pytest.mark.parametrize("parts", [
    [{"title": "超过五题", "questionIds": ["q0", "q1", "q2", "q3", "q4", "q5"]}],
    [
        {"title": "第一辑", "questionIds": ["q0"]},
        {"title": "第二辑", "questionIds": ["q0"]},
    ],
    [{"title": "外部题", "questionIds": ["not-found"]}],
])
def test_invalid_parts_fail_before_publish(db, parts):
    with pytest.raises(HTTPException):
        save_entry(db, "a", payload(parts=parts, collectionEnabled=False))


def test_unreviewed_question_blocks_published_entry(db):
    db.get(Question, "q0").status = "pending"
    db.commit()
    with pytest.raises(HTTPException, match="尚未审核完整"):
        save_entry(db, "a", payload())
