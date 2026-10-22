"""创意平台 API：闭环校验、对象权限与幂等行为。"""
from __future__ import annotations
import os
import json
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_creative_platform.db"
if _DB.exists(): _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["ALLOW_REGISTER"] = "true"
os.environ["SECRET_KEY"] = "creative-platform-test-secret"
from app.config import get_settings
get_settings.cache_clear()
from fastapi.testclient import TestClient
import pytest
from app.core.security import hash_password
from app.database import SessionLocal
from app.main import app
from app.api.admin import creative as creative_api
from app.database import engine
from app.models import AdminUser, Role

def login(client, username, role_code="super_admin"):
    db=SessionLocal()
    try:
        role=db.query(Role).filter_by(code=role_code).first()
        db.add(AdminUser(username=username,password_hash=hash_password("Passw0rd!"),nickname=username,role_id=role.id));db.commit()
    finally: db.close()
    body=client.post("/admin/auth/login",json={"username":username,"password":"Passw0rd!"}).json()
    return {"Authorization":f"Bearer {body['data']['access_token']}"}

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_database():
    yield
    engine.dispose()
    if _DB.exists(): _DB.unlink()

def test_creative_capture_practice_privacy_and_recycle(tmp_path, monkeypatch):
    monkeypatch.setattr(creative_api, "DATA_DIR", tmp_path)
    with TestClient(app) as client:
        a=login(client,"creative_a"); b=login(client,"creative_b")
        viewer=login(client,"creative_viewer","viewer")
        assert client.get("/admin/creative/overview",headers=viewer).status_code==403
        db=SessionLocal()
        try:
            editor_role=db.query(Role).filter_by(code="editor").first()
            editor_role.permissions=json.dumps(["creative:read","creative:write","creative:manage"])
            db.commit()
        finally: db.close()
        manager=login(client,"creative_manager","editor")
        denied=client.get("/admin/creative/overview")
        assert denied.status_code==401
        capture={"text":"我想打造抖音公考内容矩阵","idempotencyKey":"stable-capture-001"}
        first=client.post("/admin/creative/captures",headers=a,json=capture)
        assert first.status_code==200 and first.json()["data"]["status"]=="inbox"
        idea_id=first.json()["data"]["id"]
        retry=client.post("/admin/creative/captures",headers=a,json=capture)
        assert retry.json()["data"]["id"]==idea_id
        conflict=client.post("/admin/creative/captures",headers=a,json={**capture,"text":"不同内容"})
        assert conflict.status_code==409
        assert client.get(f"/admin/creative/ideas/{idea_id}",headers=b).status_code==404
        assert client.get(f"/admin/creative/ideas/{idea_id}",headers=manager).status_code==404
        shared=client.post("/admin/creative/ideas",headers=a,json={"title":"共享的内容方向","visibility":"shared"}).json()["data"]
        assert client.get(f"/admin/creative/ideas/{shared['id']}",headers=manager).status_code==200
        assert client.patch(f"/admin/creative/ideas/{shared['id']}",headers=manager,json={"title":"由运营协助维护","version":shared["version"]}).status_code==200
        item=client.get(f"/admin/creative/ideas/{idea_id}",headers=a).json()["data"]["idea"]
        invalid=client.post(f"/admin/creative/ideas/{idea_id}/transition",headers=a,json={"status":"in_progress","version":item["version"]})
        assert invalid.status_code==400
        saved=client.patch(f"/admin/creative/ideas/{idea_id}",headers=a,json={"nextAction":"制作三条样片","version":item["version"]})
        assert saved.status_code==200
        item=saved.json()["data"]
        moved=client.post(f"/admin/creative/ideas/{idea_id}/transition",headers=a,json={"status":"in_progress","version":item["version"]})
        assert moved.status_code==200
        practice=client.post(f"/admin/creative/ideas/{idea_id}/practices",headers=a,json={"title":"制作样片","action":"完成第一条","result":"开头需要缩短","nextAction":"调整开场","updateNextAction":True,"version":moved.json()["data"]["version"]})
        assert practice.status_code==200
        timeline=client.get(f"/admin/creative/ideas/{idea_id}/timeline",headers=a).json()["data"]
        assert timeline["total"]>=3 and timeline["items"][0]["type"] in {"practice","event"}
        child=client.post("/admin/creative/ideas",headers=a,json={"title":"三种开头","ideaType":"content_topic","parentId":idea_id})
        assert child.status_code==200
        assert client.delete(f"/admin/creative/ideas/{idea_id}",headers=a).status_code==409
        material=client.post("/admin/creative/materials",headers=a,json={"title":"参考视频","url":"https://example.com/video","kind":"link"})
        material_id=material.json()["data"]["id"]
        material_data=material.json()["data"]
        patched_material=client.patch(f"/admin/creative/materials/{material_id}",headers=a,json={"insight":"记录一个可借鉴的开场","version":material_data["version"]})
        assert patched_material.status_code==200
        assert client.get(f"/admin/creative/materials/{material_id}",headers=a).json()["data"]["insight"]=="记录一个可借鉴的开场"
        assert client.post(f"/admin/creative/ideas/{idea_id}/materials/{material_id}",headers=a).status_code==200
        assert client.delete(f"/admin/creative/materials/{material_id}",headers=a).status_code==200
        assert client.post(f"/admin/creative/materials/{material_id}/restore",headers=a).status_code==200
        upload=client.post(f"/admin/creative/materials/{material_id}/attachments",headers=a,files={"file":("ref.png",b"\x89PNG\r\n\x1a\nexample","image/png")})
        assert upload.status_code==200,upload.text
        attachment_id=upload.json()["data"]["id"]
        download=client.get(f"/admin/creative/attachments/{attachment_id}/download",headers=a)
        assert download.status_code==200 and download.content.startswith(b"\x89PNG")
        assert client.get(f"/admin/creative/attachments/{attachment_id}/download",headers=b).status_code==404
        assert client.delete(f"/admin/creative/attachments/{attachment_id}",headers=a).status_code==200
        assert client.get(f"/admin/creative/attachments/{attachment_id}/download",headers=a).status_code==404
        exported=client.get(f"/admin/creative/ideas/{idea_id}/export",headers=a)
        assert "抖音公考内容矩阵" in exported.json()["data"]["content"]
        tags=client.post("/admin/creative/tags",headers=a,json={"name":"短视频"}).json()["data"]
        assert client.patch(f"/admin/creative/ideas/{idea_id}",headers=a,json={"tagNames":["短视频"],"version":client.get(f"/admin/creative/ideas/{idea_id}",headers=a).json()["data"]["idea"]["version"]}).status_code==200
        assert client.get("/admin/creative/ideas",headers=a,params={"tag":"短视频"}).json()["data"]["total"]==1
        assert client.patch(f"/admin/creative/tags/{tags['id']}",headers=a,json={"name":"视频创作"}).status_code==200
