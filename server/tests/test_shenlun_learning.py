"""申论公共教研示范接口测试：匿名只读，和个人开采数据严格隔离。"""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.public.shenlun_learning import router
from app.database import get_db
from app.models import RmrbArticle, ShenlunMineLog, ShenlunTeachingExample
from app.models.base import Base

SHENLUN_HEADERS = {"X-Product-Key": "shenlun"}


def valid_example(**overrides) -> dict:
    data = {
        "id": "ste-a-v1",
        "article_id": "a",
        "version": "1",
        "source_excerpt": "材料节选。",
        "argument_json": json.dumps({
            "overview": "总论点与全文推进逻辑",
            "points": [{
                "title": "分论点一",
                "claim": "核心判断",
                "evidence": "材料事实",
                "summary": "论证小结",
                "method": "举例论证",
                "methodNote": "用事实支撑判断",
                "template": "既要……也要……",
            }],
            "conclusion": "回扣主题并提出行动方向",
        }, ensure_ascii=False),
        "terms_json": json.dumps([{"term": "系统施策", "category": "方法"}], ensure_ascii=False),
        "quotes_json": json.dumps([{"text": "行稳方能致远", "source": "文章"}], ensure_ascii=False),
        "verbs_json": json.dumps([{"verb": "夯实", "usage": "夯实基础"}], ensure_ascii=False),
        "templates_json": json.dumps([{
            "type": "递进句", "original": "原句", "template": "不仅……更要……", "imitate": "仿写句",
        }], ensure_ascii=False),
        "practice_json": json.dumps({
            "prompt": "请用一句话概括材料核心观点。",
            "minLength": 20,
            "maxLength": 120,
            "checks": ["观点明确", "包含行动方向"],
            "referenceAnswer": "应以系统思维统筹当前任务与长远目标，持续夯实发展基础。",
        }, ensure_ascii=False),
        "status": "published",
    }
    data.update(overrides)
    return data


@pytest.fixture
def fixture():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(RmrbArticle(
            id="a", title="测试文章", source="学习材料", publish_date="2026-09-07",
            summary="摘要", content="全文", tags=json.dumps(["治理", "实践"]),
            is_published=True, sort_order=10, read_count=7,
        ))
        db.add(ShenlunTeachingExample(**valid_example()))
        db.commit()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client:
            yield client, db
    engine.dispose()


def test_anonymous_list_and_detail_keep_private_tables_untouched(fixture):
    client, db = fixture
    listing = client.get("/shenlun/learning/articles", headers=SHENLUN_HEADERS)
    assert listing.status_code == 200
    assert listing.json()["data"][0]["teachingVersion"] == "1"

    response = client.get("/shenlun/learning/articles/a", headers=SHENLUN_HEADERS)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["article"]["content"] == "全文"
    assert data["example"]["argument"]["points"][0]["method"] == "举例论证"
    assert data["example"]["practice"]["referenceAnswer"]
    assert len(data["revision"]) == 64
    assert db.get(RmrbArticle, "a").read_count == 7
    assert db.query(ShenlunMineLog).count() == 0
    assert not db.new and not db.dirty


@pytest.mark.parametrize("product", ["general", "theory"])
def test_other_products_cannot_read_shenlun_examples(fixture, product):
    client, _ = fixture
    headers = {"X-Product-Key": product}
    assert client.get("/shenlun/learning/articles", headers=headers).status_code == 404
    assert client.get("/shenlun/learning/articles/a", headers=headers).status_code == 404


@pytest.mark.parametrize("change", [
    {"status": "draft"},
    {"source_excerpt": " "},
    {"argument_json": "{}"},
    {"argument_json": json.dumps({
        "overview": "总论点", "conclusion": "总结",
        "points": [{"title": "只有标题"}],
    })},
    {"terms_json": "[]"},
    {"templates_json": "[]"},
    {"practice_json": json.dumps({"prompt": "只有题目"})},
])
def test_draft_or_incomplete_example_fails_closed(fixture, change):
    client, db = fixture
    row = db.get(ShenlunTeachingExample, "ste-a-v1")
    for key, value in change.items():
        setattr(row, key, value)
    db.commit()
    assert client.get("/shenlun/learning/articles", headers=SHENLUN_HEADERS).json()["data"] == []
    assert client.get("/shenlun/learning/articles/a", headers=SHENLUN_HEADERS).status_code == 404


def test_unpublished_article_is_hidden(fixture):
    client, db = fixture
    db.get(RmrbArticle, "a").is_published = False
    db.commit()
    assert client.get("/shenlun/learning/articles", headers=SHENLUN_HEADERS).json()["data"] == []
    assert client.get("/shenlun/learning/articles/a", headers=SHENLUN_HEADERS).status_code == 404


def test_revision_tracks_teaching_content_but_not_read_count(fixture):
    client, db = fixture
    first = client.get("/shenlun/learning/articles/a", headers=SHENLUN_HEADERS).json()["data"]["revision"]
    db.get(RmrbArticle, "a").read_count += 1
    db.commit()
    second = client.get("/shenlun/learning/articles/a", headers=SHENLUN_HEADERS).json()["data"]["revision"]
    assert second == first
    db.get(ShenlunTeachingExample, "ste-a-v1").source_excerpt = "更新后的材料节选。"
    db.commit()
    third = client.get("/shenlun/learning/articles/a", headers=SHENLUN_HEADERS).json()["data"]["revision"]
    assert third != first
