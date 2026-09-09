"""词表待收录：未知分类进入 inbox，晋升写入正式表。"""

from __future__ import annotations

import os
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_vocab_inbox.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SECRET_KEY"] = "vocab-inbox-secret"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ShenlunTermCategory, VocabInbox  # noqa: E402
from app.services.rmrb_meta_service import ensure_rmrb_meta_defaults  # noqa: E402
from app.services.vocab_inbox_service import (  # noqa: E402
    ignore_inbox,
    list_inbox,
    observe,
    observe_from_mine,
    promote_inbox,
)


def test_observe_unknown_then_promote():
    with TestClient(app):
        db = SessionLocal()
        try:
            ensure_rmrb_meta_defaults(db)
            observe(db, "term_category", "民生关切", source_title="示例时评")
            observe(db, "term_category", "其他")
            db.commit()
            pending = list_inbox(db, kind="term_category")
            names = {x["name"] for x in pending}
            assert "民生关切" in names
            assert "其他" not in names
            row = next(x for x in pending if x["name"] == "民生关切")
            out = promote_inbox(db, row["id"])
            assert out["status"] == "promoted"
            cat = db.query(ShenlunTermCategory).filter(ShenlunTermCategory.name == "民生关切").first()
            assert cat is not None
            observe(db, "term_category", "民生关切")
            db.commit()
            still = list_inbox(db, kind="term_category")
            assert all(x["name"] != "民生关切" for x in still)
        finally:
            db.close()


def test_observe_mine_and_ignore():
    with TestClient(app):
        db = SessionLocal()
        try:
            observe_from_mine(
                db,
                terms=[{"term": "协同治理", "category": "新分类甲", "plainWord": ""}],
                verbs=[{"word": "夯实", "category": "新动词乙"}],
                templates=[{"type": "custom_x", "typeName": "设问收束型"}],
                argument={"templateName": "新骨架丙", "overviewMethod": "", "points": [{"method": "新方法丁"}]},
                article_title="开采测试",
            )
            db.commit()
            names = {x["name"] for x in list_inbox(db)}
            assert "新分类甲" in names
            assert "新动词乙" in names
            assert "设问收束型" in names
            assert "新骨架丙" in names
            assert "新方法丁" in names
            item = next(x for x in list_inbox(db) if x["name"] == "新分类甲")
            ignore_inbox(db, item["id"])
            row = db.query(VocabInbox).filter(VocabInbox.name == "新分类甲").first()
            assert row.status == "ignored"
            observe(db, "term_category", "新分类甲")
            db.commit()
            assert db.query(VocabInbox).filter(VocabInbox.name == "新分类甲").first().status == "ignored"
        finally:
            db.close()
