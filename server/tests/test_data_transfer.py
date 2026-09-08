"""数据导出/导入 service 往返测试（独立临时库，不污染开发库）。

覆盖：导出结构正确、datetime 序列化、字符串主键 id 保留、int 主键 id 重建、整表替换导入。
"""
from __future__ import annotations

import os
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_data_transfer.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SECRET_KEY"] = "dt-test-secret"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402
    AppUser,
    Article,
    CorpusItem,
    DailyReview,
    ManualWrong,
    PlanTask,
    PointsLog,
    Question,
    WrongAnswer,
)
from app.services.data_transfer_service import export_core_data, import_core_data  # noqa: E402

UID = "u-dt-001"


def _setup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add(AppUser(id=UID, username="dt_user", nickname="测试学员"))
    # WrongAnswer.question_id 有外键，需先造 Article -> Question
    art = Article(id="art-dt", title="测试文章", source="测试", publish_date="2026-08-15", summary="s", content="c")
    db.add(art)
    db.add(Question(id="q-dt", article_id="art-dt", type="single", stem="题干", correct_answer="A", analysis="解析"))
    db.commit()
    return db


def test_export_import_roundtrip():
    db = _setup()

    db.add(CorpusItem(user_id=UID, original="执政为民", kind="句", status="owned"))
    db.add(PlanTask(user_id=UID, plan_date="2026-08-15", content="做资料分析", priority=5))
    db.add(PointsLog(user_id=UID, amount=10, log_type="income", source="sign", description="签到"))
    db.add(ManualWrong(user_id=UID, subject="常识", stem="题目", correct_answer="A", wrong_reason="知识点盲"))
    db.add(DailyReview(user_id=UID, review_date="2026-08-14", completion=80, mood="good"))
    db.add(WrongAnswer(user_id=UID, question_id="q-dt", wrong_count=2, user_answer="B", review_stage=1))
    db.commit()

    payload = export_core_data(db, UID)
    assert payload["version"] == 1
    assert "exportedAt" in payload
    for key in ("wrongAnswers", "manualWrongs", "corpusItems", "planTasks", "dailyReviews", "pointsLogs"):
        assert key in payload, key
    assert len(payload["corpusItems"]) == 1
    assert len(payload["planTasks"]) == 1
    assert len(payload["pointsLogs"]) == 1
    assert len(payload["manualWrongs"]) == 1
    assert len(payload["dailyReviews"]) == 1
    assert len(payload["wrongAnswers"]) == 1

    # 不泄漏 user_id；字符串主键保留 id；int 主键(WrongAnswer)不导出 id
    assert "user_id" not in payload["corpusItems"][0]
    assert payload["corpusItems"][0]["id"].startswith("cps")
    assert payload["manualWrongs"][0]["id"].startswith("mw")
    assert "id" not in payload["wrongAnswers"][0]
    assert payload["wrongAnswers"][0]["question_id"] == "q-dt"

    # datetime 序列化为 ISO 字符串
    assert isinstance(payload["manualWrongs"][0]["last_wrong_at"], str)

    corpus_id = payload["corpusItems"][0]["id"]
    manual_id = payload["manualWrongs"][0]["id"]

    # 整表替换导入：清空后加回，条数一致、字符串主键 id 保留
    result = import_core_data(db, UID, payload)
    assert result["corpusItems"] == 1
    assert result["wrongAnswers"] == 1

    payload2 = export_core_data(db, UID)
    assert len(payload2["corpusItems"]) == 1
    assert payload2["corpusItems"][0]["id"] == corpus_id
    assert payload2["manualWrongs"][0]["id"] == manual_id
    # 导入后 datetime 还原正确（无时区）
    assert payload2["manualWrongs"][0]["last_wrong_at"] == payload["manualWrongs"][0]["last_wrong_at"]

    # 再导一次（幂等替换），不应翻倍
    import_core_data(db, UID, payload)
    assert len(export_core_data(db, UID)["corpusItems"]) == 1

    db.close()
