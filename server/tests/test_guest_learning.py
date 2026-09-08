"""游客记录登录合并协议测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_app_user
from app.api.public.guest_learning import router
from app.database import get_db
from app.models import AppUser, ShenlunMineLog, UserGuestLearningRecord, WrongAnswer
from app.models.base import Base


def make_fixture():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = AppUser(id="u1", username="tester", nickname="测试用户")
    db.add(user)
    db.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_app_user] = lambda: user
    return engine, db, TestClient(app)


def theory_record(updated_at="2026-09-07T10:00:00+08:00", answer="甲"):
    return {
        "recordType": "theory_article_quiz",
        "contentId": "article-a",
        "revision": "r" * 64,
        "payload": {"records": {"q1": {"answer": answer, "correct": answer == "甲"}}},
        "updatedAt": updated_at,
    }


def test_merge_is_idempotent_and_has_no_learning_side_effects():
    engine, db, client = make_fixture()
    try:
        body = {"deviceId": "device_123", "records": [theory_record()]}
        first = client.post("/learning/guest-records/merge", headers={"X-Product-Key": "theory"}, json=body)
        assert first.status_code == 200
        assert first.json()["data"]["accepted"] == 1
        second = client.post("/learning/guest-records/merge", headers={"X-Product-Key": "theory"}, json=body)
        assert second.json()["data"]["accepted"] == 0
        assert second.json()["data"]["unchanged"] == 1
        assert db.query(UserGuestLearningRecord).count() == 1
        assert db.query(WrongAnswer).count() == 0
        assert db.query(ShenlunMineLog).count() == 0
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_newer_snapshot_wins_and_is_available_on_another_device():
    engine, db, client = make_fixture()
    try:
        headers = {"X-Product-Key": "theory"}
        client.post("/learning/guest-records/merge", headers=headers, json={
            "deviceId": "device_old", "records": [theory_record()],
        })
        newer = theory_record("2026-09-07T11:00:00+08:00", "乙")
        merged = client.post("/learning/guest-records/merge", headers=headers, json={
            "deviceId": "device_new", "records": [newer],
        }).json()["data"]
        assert merged["accepted"] == 1
        records = client.get("/learning/guest-records", headers=headers).json()["data"]
        assert records[0]["payload"]["records"]["q1"]["answer"] == "乙"

        older = theory_record("2026-09-07T09:00:00+08:00", "丙")
        result = client.post("/learning/guest-records/merge", headers=headers, json={
            "deviceId": "device_old", "records": [older],
        }).json()["data"]
        assert result["unchanged"] == 1
        assert result["records"][0]["payload"]["records"]["q1"]["answer"] == "乙"
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_each_product_accepts_only_its_own_record_type():
    engine, db, client = make_fixture()
    try:
        shenlun = {
            "recordType": "shenlun_short_practice", "contentId": "rmrb-a", "revision": "v1",
            "payload": {"answer": "一段短作答", "checks": [True], "revealed": False},
            "updatedAt": "2026-09-07T10:00:00+08:00",
        }
        assert client.post("/learning/guest-records/merge", headers={"X-Product-Key": "shenlun"}, json={
            "deviceId": "device_123", "records": [shenlun],
        }).status_code == 200
        assert client.post("/learning/guest-records/merge", headers={"X-Product-Key": "theory"}, json={
            "deviceId": "device_123", "records": [shenlun],
        }).status_code == 422
        assert client.post("/learning/guest-records/merge", headers={"X-Product-Key": "shenlun"}, json={
            "deviceId": "device_123", "records": [theory_record()],
        }).status_code == 422
        assert len(client.get("/learning/guest-records", headers={"X-Product-Key": "theory"}).json()["data"]) == 0
        assert len(client.get("/learning/guest-records", headers={"X-Product-Key": "shenlun"}).json()["data"]) == 1
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_rejects_invalid_device_and_oversized_payload():
    engine, db, client = make_fixture()
    try:
        headers = {"X-Product-Key": "theory"}
        assert client.post("/learning/guest-records/merge", headers=headers, json={
            "deviceId": "bad id", "records": [],
        }).status_code == 422
        record = theory_record()
        record["payload"] = {"text": "字" * 50_001}
        assert client.post("/learning/guest-records/merge", headers=headers, json={
            "deviceId": "device_123", "records": [record],
        }).status_code == 422
        future = theory_record("2099-01-01T00:00:00+08:00")
        assert client.post("/learning/guest-records/merge", headers=headers, json={
            "deviceId": "device_123", "records": [future],
        }).status_code == 422
    finally:
        client.close()
        db.close()
        engine.dispose()
