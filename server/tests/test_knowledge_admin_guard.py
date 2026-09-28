"""知识树管理端守卫：旧节点 CRUD 已停用（410，节点不受影响），md 预览需 knowledge:write。"""
from __future__ import annotations

import os
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_knowledge_guard.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SECRET_KEY"] = "knowledge-guard-test-secret"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AdminUser, KnowledgeNode, Role  # noqa: E402


def _login(client: TestClient, username: str, role_code: str) -> dict:
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.code == role_code).first()
        assert role is not None
        db.add(AdminUser(username=username, password_hash=hash_password("Passw0rd!"),
                         nickname=username, role_id=role.id))
        db.commit()
    finally:
        db.close()
    res = client.post("/admin/auth/login", json={"username": username, "password": "Passw0rd!"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['data']['access_token']}"}


def test_legacy_node_crud_gone_and_nodes_kept():
    with TestClient(app) as client:
        h = _login(client, "kg_editor", "editor")
        db = SessionLocal()
        try:
            node = KnowledgeNode(tree_key="kg_tree", path="kg_tree/a", title="A", depth=1,
                                 sort_order=0)
            db.add(node)
            db.commit()
            nid = node.id
        finally:
            db.close()
        r1 = client.post("/admin/knowledge/node", json={"treeKey": "kg_tree", "title": "X"}, headers=h)
        r2 = client.put(f"/admin/knowledge/node/{nid}", json={"title": "改名"}, headers=h)
        r3 = client.delete(f"/admin/knowledge/node/{nid}", headers=h)
        for r in (r1, r2, r3):
            assert r.status_code == 200 and r.json()["code"] == 410, r.text
        db = SessionLocal()
        try:
            kept = db.get(KnowledgeNode, nid)
            assert kept is not None and kept.title == "A"
        finally:
            db.close()


def test_md_preview_requires_write():
    with TestClient(app) as client:
        viewer = _login(client, "kg_viewer", "viewer")
        editor = _login(client, "kg_editor2", "editor")
        body = {"treeKey": "kg_tree", "md": "# 根\n## 一\n- 点\n"}
        assert client.post("/admin/knowledge/preview", json=body, headers=viewer).status_code == 403
        r = client.post("/admin/knowledge/preview", json=body, headers=editor)
        assert r.status_code == 200, r.text
