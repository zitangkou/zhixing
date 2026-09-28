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
from app.services import knowledge_doc_service as docs  # noqa: E402
from app.services.knowledge_doc_service import (  # noqa: E402
    activate_version,
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
        # 导入只固化版本，不自动上线、不派生节点
        tree = db.query(KnowledgeTree).filter(KnowledgeTree.tree_key == "测试科").one()
        assert tree.live_version == 0 and not tree.is_visible
        assert db.query(KnowledgeNode).filter(KnowledgeNode.tree_key == "测试科").count() == 0
        _, err = activate_version(db, "测试科", r["version"], allow_no_assets=True)
        assert err is None
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
        assert pub["nodeDiffPreview"]["added"] == 1
        # 发布后未激活：节点不变
        assert "题型甲/方法一/新增叶" not in {
            n.path for n in db.query(KnowledgeNode).filter(KnowledgeNode.tree_key == "测试科")
        }
        _, err = activate_version(db, "测试科", pub["version"])
        assert err == "assets_not_ready"
        _, err = activate_version(db, "测试科", pub["version"], allow_no_assets=True)
        assert err is None
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
        r = import_md_to_draft(db, "测试科2", "测试科2", MD.replace("测试科", "测试科2"), publish=True, force=True)
        activate_version(db, "测试科2", r["version"], allow_no_assets=True)
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


# ---------------------------------------------------------------------------
# 资源上传安全 / 激活 / 清理
# ---------------------------------------------------------------------------
import struct  # noqa: E402
import zlib  # noqa: E402

import pytest  # noqa: E402

from app.services.knowledge_doc_service import save_version_assets, validate_svg  # noqa: E402


def _png(w: int, h: int) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + b"\xff\xff\xff" * w for _ in range(h))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


MARKMAP_LIKE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
    'viewBox="0 0 100 50" width="100" height="50">'
    "<style>.markmap-link{fill:none;stroke:#c00}</style>"
    '<g transform="translate(10,10)"><path class="markmap-link" d="M0,0 C10,0 10,20 20,20" fill="none"/>'
    '<circle r="3" fill="#fff" stroke="#c00"/><text x="4" y="4" font-size="16">知识点 http://x</text></g></svg>'
).encode()


@pytest.mark.parametrize(
    "svg,ok",
    [
        (MARKMAP_LIKE_SVG, True),
        (b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', False),
        (b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>', False),
        (b'<svg xmlns="http://www.w3.org/2000/svg"><a href="https://evil"><text>x</text></a></svg>', False),
        (b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
         b'<use xlink:href="https://evil#a"/></svg>', False),
        (b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><div/></foreignObject></svg>', False),
        (b'<svg xmlns="http://www.w3.org/2000/svg"><style>@import url(https://evil/x.css);</style></svg>', False),
        (b'<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill:url(https://evil/x)"/></svg>', False),
        (b'<!DOCTYPE svg [<!ENTITY a "b">]><svg xmlns="http://www.w3.org/2000/svg"/>', False),
        (b'<html xmlns="http://www.w3.org/1999/xhtml"><body/></html>', False),
    ],
)
def test_validate_svg(svg, ok):
    assert (validate_svg(svg) is None) is ok, validate_svg(svg)


@pytest.fixture()
def assets_root(tmp_path, monkeypatch):
    monkeypatch.setattr(docs, "_assets_root", lambda: tmp_path)
    return tmp_path


def _published_tree(db, key: str) -> tuple:
    r = import_md_to_draft(db, key, key, MD.replace("测试科", key), publish=True, force=True)
    tree = db.query(KnowledgeTree).filter(KnowledgeTree.tree_key == key).one()
    return tree, r["version"]


def _good_manifest():
    files = {
        "overview-abc.png": _png(40, 30),
        "overview-abc.thumb.png": _png(20, 15),
        "s01-abc.png": _png(50, 20),
        "full-abc.svg": MARKMAP_LIKE_SVG,
        "tree.json": b'{"title": "x"}',
    }
    manifest = {
        "theme": "brand-red",
        "scale": 2,
        "overview": {"url": "overview-abc.png", "thumbUrl": "overview-abc.thumb.png"},
        "segments": [{"key": "s01", "title": "题型甲", "rootPath": "题型甲", "nodeCount": 5, "url": "s01-abc.png"}],
        "svg": {"url": "full-abc.svg"},
        "treeJsonUrl": "tree.json",
    }
    return manifest, files


def test_assets_upload_activates_and_rebuilds_urls(assets_root):
    db = SessionLocal()
    try:
        tree, v = _published_tree(db, "资源科")
        manifest, files = _good_manifest()
        manifest["overview"]["url_extra"] = "https://evil"  # 未知字段被丢弃
        out, err = save_version_assets(db, "资源科", v, manifest=manifest, files=files)
        assert err == "", err
        db.refresh(tree)
        assert tree.live_version == v
        m = out["manifest"]
        assert m["overview"]["url"] == f"/uploads/knowledge/{tree.id}/v{v}/overview-abc.png"
        assert "url_extra" not in m["overview"]
        assert m["segments"][0]["width"] == 50 and m["segments"][0]["key"] == "s01"
        assert (assets_root / tree.id / f"v{v}" / "full-abc.svg").is_file()
        # 激活后节点已派生
        assert db.query(KnowledgeNode).filter(KnowledgeNode.tree_key == "资源科").count() > 0
    finally:
        db.close()


@pytest.mark.parametrize(
    "mutate,err_prefix",
    [
        (lambda m, f: (m["segments"][0].update(url="evil.html"), f.update({"evil.html": b"<script>"})), "bad_name"),
        (lambda m, f: f.update({"../escape.png": _png(2, 2)}), "bad_name"),
        (lambda m, f: m["segments"][0].update(url="https://evil.example/x.png"), "bad_name"),
        (lambda m, f: m["segments"][0].update(url="missing.png"), "missing_file"),
        (lambda m, f: m["segments"][0].update(key="申论-中文"), "bad_segment_key"),
        (lambda m, f: f.update({"s01-abc.png": b"not a png"}), "bad_png"),
        (lambda m, f: f.update({"s01-abc.png": _png(5000, 10)}), "png_too_big"),
        (lambda m, f: f.update({"overview-abc.thumb.png": _png(2000, 10)}), "png_too_big"),
        (lambda m, f: f.update({"full-abc.svg": b'<svg xmlns="http://www.w3.org/2000/svg" onload="x"/>'}), "bad_svg"),
        (lambda m, f: f.update({"tree.json": b"[1,2]"}), "bad_json"),
    ],
)
def test_assets_rejected_without_touching_existing(assets_root, mutate, err_prefix):
    db = SessionLocal()
    try:
        key = "拒绝科"
        tree = db.query(KnowledgeTree).filter(KnowledgeTree.tree_key == key).first()
        if not tree:
            tree, v = _published_tree(db, key)
            manifest, files = _good_manifest()
            _, err = save_version_assets(db, key, v, manifest=manifest, files=files)
            assert err == ""
            db.refresh(tree)
        v = tree.live_version
        vdir = assets_root / tree.id / f"v{v}"
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "sentinel.png").write_bytes(b"keep")
        manifest, files = _good_manifest()
        mutate(manifest, files)
        out, err = save_version_assets(db, key, v, manifest=manifest, files=files)
        assert out is None and err.startswith(err_prefix), err
        # 校验失败不得删除或改动已有目录
        assert (vdir / "sentinel.png").read_bytes() == b"keep"
        assert not any(p.suffix == ".html" for p in (assets_root / tree.id).rglob("*"))
    finally:
        db.close()


def test_cleanup_never_removes_live(assets_root, monkeypatch):
    monkeypatch.setattr(docs, "_KEEP_VERSIONS", 2)
    db = SessionLocal()
    try:
        key = "清理科"
        tree, v1 = _published_tree(db, key)
        manifest, files = _good_manifest()
        assert save_version_assets(db, key, v1, manifest=manifest, files=files)[1] == ""
        # 之后发布多个版本但只生成图片不上线
        versions = []
        for i in range(4):
            db.refresh(tree)
            save_draft(db, key, MD.replace("测试科", key) + f"\n## 新题型{i}\n\n- a\n", tree.draft_revision)
            db.refresh(tree)
            pub, err, _ = publish_tree(db, key, tree.draft_revision)
            assert err is None
            m, f = _good_manifest()
            assert save_version_assets(db, key, pub["version"], manifest=m, files=f, activate=False)[1] == ""
            versions.append(pub["version"])
        db.refresh(tree)
        assert tree.live_version == v1
        assert (assets_root / tree.id / f"v{v1}").is_dir(), "live 资源被清理"
        assert (assets_root / tree.id / f"v{versions[-1]}").is_dir()
        assert not (assets_root / tree.id / f"v{versions[0]}").exists()
        # 回滚上线旧版本：不新建版本，节点恢复
        out, err = activate_version(db, key, versions[-1])
        assert err is None and out["previousLive"] == v1
        paths = {
            n.path
            for n in db.query(KnowledgeNode).filter(
                KnowledgeNode.tree_key == key, KnowledgeNode.archived_at.is_(None)
            )
        }
        assert "新题型3" in paths and "新题型0" not in paths
        out, err = activate_version(db, key, v1, expected_live=999)
        assert err == "conflict"
    finally:
        db.close()


def test_public_map_hidden_until_visible_and_ids_attached(assets_root):
    db = SessionLocal()
    client = TestClient(app)
    try:
        key = "公开科"
        tree, v = _published_tree(db, key)
        manifest, files = _good_manifest()
        assert save_version_assets(db, key, v, manifest=manifest, files=files)[1] == ""
        keys = [m["treeKey"] for m in client.get("/api/knowledge/maps").json()["data"]]
        assert key not in keys  # 未设可见
        docs.patch_tree(db, key, {"isVisible": True})
        keys = [m["treeKey"] for m in client.get("/api/knowledge/maps").json()["data"]]
        assert key in keys
        detail = client.get(f"/api/knowledge/maps/{key}").json()["data"]
        node_ids = {
            n.id for n in db.query(KnowledgeNode).filter(KnowledgeNode.tree_key == key)
        }
        first = detail["tree"]["children"][0]
        assert first["id"] in node_ids
    finally:
        db.close()


def test_public_tree_list_hides_hidden_and_unpublished(assets_root):
    """P1-5：学员端 /knowledge/trees 与 /knowledge/tree/{key} 只暴露可见且已上线的树。"""
    from app.models import KnowledgeNode as KN

    from app.core.security import create_access_token
    from app.models import AppUser

    db = SessionLocal()
    client = TestClient(app)
    user = db.query(AppUser).filter(AppUser.username == "kp_visibility").first()
    if not user:
        user = AppUser(username="kp_visibility", password_hash="x")
        db.add(user)
        db.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    try:
        # 遗留节点：没有 knowledge_trees 行（如生产的「申论题型」）
        db.add(KN(tree_key="遗留题型", title="旧节点", path="旧节点", depth=0, sort_order=0))
        db.commit()
        key = "可见性科"
        tree, v = _published_tree(db, key)
        manifest, files = _good_manifest()
        assert save_version_assets(db, key, v, manifest=manifest, files=files)[1] == ""

        def listed():
            r = client.get("/api/knowledge/trees", headers=headers)
            assert r.status_code == 200, r.text
            return {t["treeKey"] for t in r.json()["data"]}

        assert "遗留题型" not in listed()
        assert key not in listed()  # 已上线但未设可见
        assert client.get(f"/api/knowledge/tree/{key}", headers=headers).json()["code"] != 0
        assert client.get("/api/knowledge/tree/遗留题型", headers=headers).json()["code"] != 0

        docs.patch_tree(db, key, {"isVisible": True})
        assert key in listed()
        d = client.get(f"/api/knowledge/tree/{key}", headers=headers).json()
        assert d["code"] == 0 and d["data"]["title"] == key
    finally:
        db.close()


def test_migrate_legacy_user_state_dry_run_apply_idempotent():
    from datetime import datetime, timedelta

    from app.models import AppUser
    from app.scripts.migrate_user_knowledge_state import migrate

    db = SessionLocal()
    try:
        user = AppUser(username="kp_migrate", password_hash="x")
        db.add(user)
        db.commit()
        uid = user.id
        t0 = datetime(2026, 1, 1)
        a = KnowledgeNode(tree_key="mig_tree", title="甲", path="甲", depth=0, sort_order=0,
                          my_note="旧备注甲", is_starred=True, mastery_level="familiar",
                          review_count=3, last_reviewed_at=t0, next_review_at=t0 + timedelta(days=3))
        b = KnowledgeNode(tree_key="mig_tree", title="乙", path="乙", depth=0, sort_order=1,
                          my_note="旧备注乙", last_reviewed_at=t0)
        c = KnowledgeNode(tree_key="mig_tree", title="丙", path="丙", depth=0, sort_order=2)  # 无旧状态
        db.add_all([a, b, c])
        db.commit()
        # 乙：学员已在新表写过更新的备注 → 冲突时保留新表
        db.add(UserKnowledgeState(user_id=uid, node_id=b.id, tree_key="mig_tree", path="乙",
                                  my_note="新备注乙", updated_at=t0 + timedelta(days=10)))
        db.commit()

        dry = migrate(db, uid, tree_key="mig_tree")
        assert (dry.with_legacy_state, dry.created, dry.updated) == (2, 1, 1)  # 乙补复习进度
        assert dry.conflicts[0]["kept"] == "current"
        assert db.query(UserKnowledgeState).filter_by(user_id=uid, node_id=a.id).first() is None

        res = migrate(db, uid, tree_key="mig_tree", apply=True)
        assert res.created == 1
        st_a = db.query(UserKnowledgeState).filter_by(user_id=uid, node_id=a.id).one()
        assert (st_a.my_note, st_a.is_starred, st_a.mastery_level, st_a.review_count) == (
            "旧备注甲", True, "familiar", 3)
        st_b = db.query(UserKnowledgeState).filter_by(user_id=uid, node_id=b.id).one()
        assert st_b.my_note == "新备注乙"
        assert st_b.last_reviewed_at == t0  # 复习进度补齐
        assert db.get(KnowledgeNode, a.id).my_note == "旧备注甲"  # 不清空旧字段

        again = migrate(db, uid, tree_key="mig_tree", apply=True)
        assert (again.created, again.updated) == (0, 0)
        assert db.query(UserKnowledgeState).filter_by(user_id=uid).count() == 2
    finally:
        db.close()


def test_migrate_requires_existing_user():
    import pytest

    from app.scripts.migrate_user_knowledge_state import migrate

    db = SessionLocal()
    try:
        with pytest.raises(ValueError):
            migrate(db, "no-such-user")
    finally:
        db.close()


def test_import_keeps_unpublished_draft_unless_forced():
    db = SessionLocal()
    try:
        md1 = "# 草稿保护\n## 一\n- 点\n"
        r = import_md_to_draft(db, "draft_guard", "草稿保护", md1, admin_id="t")
        assert r["ok"]
        rev = r["draftRevision"]
        # 同内容：不升 revision
        same = import_md_to_draft(db, "draft_guard", "草稿保护", md1, force=True, keep_unpublished=True)
        assert same["ok"] and same.get("unchanged") and same["draftRevision"] == rev
        # 从未发布 → 视为未发布修改，默认拒绝
        md2 = md1 + "- 新点\n"
        dirty = import_md_to_draft(db, "draft_guard", "草稿保护", md2, force=True, keep_unpublished=True)
        assert dirty == {"ok": False, "error": "draft_dirty", "treeKey": "draft_guard", "draftRevision": rev}
        # 发布后草稿 == 最新版本 → 允许覆盖
        pub, err, _ = publish_tree(db, "draft_guard", rev, admin_id="t")
        assert pub and not err
        ok = import_md_to_draft(db, "draft_guard", "草稿保护", md2, force=True, keep_unpublished=True)
        assert ok["ok"] and ok["draftRevision"] == rev + 1
        # 再改一版未发布，显式 force 覆盖
        forced = import_md_to_draft(db, "draft_guard", "草稿保护", md2 + "- 再加\n", force=True)
        assert forced["ok"]
    finally:
        db.close()


def test_list_tree_metas_counts_and_live_state():
    db = SessionLocal()
    try:
        md = "# 元信息\n## 一\n- 甲\n- 乙\n"
        r = import_md_to_draft(db, "meta_tree", "元信息", md, admin_id="t")
        pub, err, _ = publish_tree(db, "meta_tree", r["draftRevision"], admin_id="t")
        assert pub and not err
        activate_version(db, "meta_tree", pub["version"], admin_id="t", allow_no_assets=True)
        metas = {m["treeKey"]: m for m in docs.list_tree_metas(db)}
        m = metas["meta_tree"]
        assert m["liveVersion"] == pub["version"]
        assert m["liveNodeCount"] == db.query(KnowledgeNode).filter(
            KnowledgeNode.tree_key == "meta_tree", KnowledgeNode.archived_at.is_(None)).count() > 0
        assert m["hasUnpublishedChanges"] is False and m["livePublishedAt"] is not None
        save_draft(db, "meta_tree", md + "- 丙\n", m["draftRevision"], admin_id="t")
        assert {x["treeKey"]: x for x in docs.list_tree_metas(db)}["meta_tree"]["hasUnpublishedChanges"] is True
    finally:
        db.close()
