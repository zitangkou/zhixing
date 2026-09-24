"""系统菜单权限：接口与角色种子一致，缺权限返回 403。"""
from __future__ import annotations

import os
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_system_perms.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["ALLOW_REGISTER"] = "true"
os.environ["SECRET_KEY"] = "system-perms-test-secret"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AdminUser, Role  # noqa: E402


def _login(client: TestClient, username: str, role_code: str) -> dict:
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.code == role_code).first()
        assert role is not None
        db.add(
            AdminUser(
                username=username,
                password_hash=hash_password("Passw0rd!"),
                nickname=username,
                role_id=role.id,
            )
        )
        db.commit()
    finally:
        db.close()
    res = client.post("/admin/auth/login", json={"username": username, "password": "Passw0rd!"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["code"] == 0, body
    return {"Authorization": f"Bearer {body['data']['access_token']}"}


def test_system_role_codes_cover_new_menus():
    for code in ("feedback:read", "feedback:write", "xingce:read", "xingce:write", "setting:read", "admin:read"):
        assert code in PERMISSIONS
        assert code in ROLE_PERMISSIONS["super_admin"]
    assert "feedback:read" in ROLE_PERMISSIONS["editor"]
    assert "xingce:write" in ROLE_PERMISSIONS["editor"]
    assert "setting:read" not in ROLE_PERMISSIONS["editor"]
    assert "feedback:read" in ROLE_PERMISSIONS["viewer"]
    assert "xingce:read" in ROLE_PERMISSIONS["viewer"]
    assert "xingce:write" not in ROLE_PERMISSIONS["viewer"]
    assert "feedback:write" not in ROLE_PERMISSIONS["viewer"]
    assert "admin:read" not in ROLE_PERMISSIONS["viewer"]
    assert "setting:read" in ROLE_PERMISSIONS["viewer"]
    assert "setting:write" not in ROLE_PERMISSIONS["viewer"]


def test_system_endpoints_follow_role_grants():
    with TestClient(app) as client:
        super_headers = _login(client, "root2", "super_admin")
        # 默认 admin 已由种子创建；再用 super_admin 角色账号覆盖「全菜单」路径
        for path in ("/admin/feedbacks", "/admin/xingce/overview", "/admin/settings", "/admin/roles"):
            res = client.get(path, headers=super_headers)
            assert res.status_code == 200, (path, res.text)
            assert res.json()["code"] == 0

        editor = _login(client, "ed1", "editor")
        assert client.get("/admin/feedbacks", headers=editor).status_code == 200
        assert client.get("/admin/xingce/overview", headers=editor).status_code == 200
        assert client.get("/admin/settings", headers=editor).status_code == 403
        assert client.get("/admin/roles", headers=editor).status_code == 403

        viewer = _login(client, "vw1", "viewer")
        assert client.get("/admin/feedbacks", headers=viewer).status_code == 200
        assert client.get("/admin/xingce/overview", headers=viewer).status_code == 200
        assert client.get("/admin/settings", headers=viewer).status_code == 200
        assert client.get("/admin/roles", headers=viewer).status_code == 403
        denied = client.put("/admin/settings/site_name", headers=viewer, json={"value": "x"})
        assert denied.status_code == 403
