"""知识框架发布 / 用户状态测试。使用独立临时库。"""
from __future__ import annotations

import os
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_knowledge_publish.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SECRET_KEY"] = "knowledge-publish-test-secret"

from app.config import get_settings

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app.db_compat import run_compat_migrations  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, KnowledgeNode, KnowledgeTree, UserKnowledgeState  # noqa: E402
from app.services.knowledge_doc_service import (  # noqa: E402
    import_md_to_draft,
    publish_tree,
    save_draft,
    upsert_user_state,
)

Base.metadata.create_all(bind=engine)
run_compat_migrations()

MD = """# 测试科

## 题型甲

### 方法一

- 要点A
  - 细节1
- 要点B

## 题型乙

### 方法二
"""


def test_publish_keeps_stable_ids():
    db = SessionLocal()
    try:
        r = import_md_to_draft(db, "测试科", "测试科", MD, publish=True, force=True)
        assert r.get("ok"), r
        nodes1 = {
            n.path: n.id
            for n in db.query(KnowledgeNode).filter(
                KnowledgeNode.tree_key == "测试科", KnowledgeNode.archived_at.is_(None)
            )
        }
        assert "题型甲/方法一/要点A/细节1" in nodes1

        tree = db.query(KnowledgeTree).filter(KnowledgeTree.tree_key == "测试科").one()
        md2 = MD.replace("- 要点B\n", "- 要点B\n- 新增叶\n")
        save_draft(db, "测试科", md2, tree.draft_revision)
        tree = db.query(KnowledgeTree).filter(KnowledgeTree.tree_key == "测试科").one()
        pub, err, _ = publish_tree(db, "测试科", tree.draft_revision)
        assert err is None, err
        nodes2 = {
            n.path: n.id
            for n in db.query(KnowledgeNode).filter(
                KnowledgeNode.tree_key == "测试科", KnowledgeNode.archived_at.is_(None)
            )
        }
        assert nodes1["题型甲/方法一/要点A/细节1"] == nodes2["题型甲/方法一/要点A/细节1"]
        assert "题型甲/方法一/新增叶" in nodes2
        assert pub and pub["version"] >= 2
    finally:
        db.close()


def test_user_states_are_isolated():
    db = SessionLocal()
    try:
        import_md_to_draft(db, "测试科2", "测试科2", MD.replace("测试科", "测试科2"), publish=True, force=True)
        node = (
            db.query(KnowledgeNode)
            .filter(KnowledgeNode.tree_key == "测试科2", KnowledgeNode.path == "题型甲/方法一/要点A")
            .first()
        )
        assert node
        upsert_user_state(db, "u-a", node.id, my_note="A的备注", is_starred=True)
        upsert_user_state(db, "u-b", node.id, my_note="B的备注", is_starred=False)
        sa = db.query(UserKnowledgeState).filter_by(user_id="u-a", node_id=node.id).one()
        sb = db.query(UserKnowledgeState).filter_by(user_id="u-b", node_id=node.id).one()
        assert sa.my_note == "A的备注" and sa.is_starred
        assert sb.my_note == "B的备注" and not sb.is_starred
    finally:
        db.close()


def test_public_sync_removed_and_maps_ok():
    client = TestClient(app)
    r = client.post("/api/knowledge/sync", headers={"X-User-Id": "u-demo-001"})
    assert r.status_code in (404, 405)
    r2 = client.get("/api/knowledge/maps")
    assert r2.status_code == 200
    body = r2.json()
    assert body.get("code") == 0
    assert isinstance(body.get("data"), list)
