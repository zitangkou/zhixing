"""行测导入：同一题不得把同一材料插入两次。

2024 卷里 material_ids 会重复同一材料（多段/共用材料收成同一 id，sort 0 与 1）。
qb_question_material_links 的唯一键是 (question_id, material_id)。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

_DB = Path(__file__).resolve().parent / "_xingce_material_links.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["ALLOW_REGISTER"] = "true"
os.environ["SECRET_KEY"] = "xingce-material-link-secret"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Material, QuestionItem, QuestionMaterialLink  # noqa: E402
from scripts.import_xingce_2025 import ImportStats, sync_material_links  # noqa: E402


def _paper(*, year: int, paper_type: str, materials: list[dict], material_ids: list[str], stem: str) -> dict:
    return {
        "exam_year": year,
        "exam_name": f"{year}年度国家公务员考试《行测》{paper_type}",
        "paper_type": paper_type,
        "schema_version": 2,
        "total_questions": 1,
        "sections": [
            {
                "name": "资料分析",
                "materials": materials,
                "questions": [
                    {
                        "number": 116,
                        "section": "资料分析",
                        "stem": stem,
                        "options": {"A": "5%", "B": "8%", "C": "12%", "D": "15%"},
                        "answer": "C",
                        "explanation": "示例解析。",
                        "material_ids": material_ids,
                    }
                ],
            }
        ],
    }


PASSAGE = {
    "id": "m116_120",
    "title": "中型灌区续建配套",
    "content": "2024年中型灌区续建配套投资概述。",
    "kind": "text",
}
CHART = {
    "id": "m121_125",
    "title": "马铃薯出口",
    "content": "图2：出口额与出口量",
    "kind": "chart",
}


def _question_links(stem: str) -> list[tuple[str, str, int]]:
    db = SessionLocal()
    try:
        from app.models import QuestionVersion

        version = db.query(QuestionVersion).filter(QuestionVersion.stem == stem).one()
        links = (
            db.query(QuestionMaterialLink)
            .filter(QuestionMaterialLink.question_id == version.question_id)
            .order_by(QuestionMaterialLink.sort_order)
            .all()
        )
        return [(link.material_id, link.role, link.sort_order) for link in links]
    finally:
        db.close()


def _post_import(client: TestClient, headers: dict, paper: dict, name: str) -> dict:
    res = client.post(
        "/admin/xingce/import",
        headers=headers,
        files={"file": (name, json.dumps(paper, ensure_ascii=False).encode(), "application/json")},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("code") == 0, body
    return body["data"]


@pytest.fixture(scope="module")
def admin_client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        admin = client.post("/admin/auth/login", json={"username": "admin", "password": "admin123"})
        assert admin.status_code == 200, admin.text
        token = admin.json()["data"]["access_token"]
        yield client, {"Authorization": f"Bearer {token}"}


def test_admin_import_2024_duplicate_material_id_inserts_once(admin_client):
    """同一题 material_ids 含同一材料两次（sort 0 与 1）时，只落一行关联。"""
    client, headers = admin_client
    stem = "2024资料样题：灌区续建配套投资同比增长约为多少？"
    paper = _paper(
        year=2024,
        paper_type="省级",
        materials=[PASSAGE],
        material_ids=["m116_120", "m116_120"],
        stem=stem,
    )
    imported = _post_import(client, headers, paper, "2024-shengji.json")
    assert any("duplicate material link skipped" in w for w in imported["warnings"])
    links = _question_links(stem)
    assert len(links) == 1
    _material_id, role, sort_order = links[0]
    assert role == "primary"
    assert sort_order == 0

    again = _post_import(client, headers, paper, "2024-shengji.json")
    assert again["newQuestions"] == 0
    assert len(_question_links(stem)) == 1


def test_admin_import_keeps_distinct_materials(admin_client):
    """一题挂两份不同材料时仍各留一条，顺序为首次出现顺序。"""
    client, headers = admin_client
    stem = "2025资料样题：出口额与灌区投资应分别看哪则材料？"
    paper = _paper(
        year=2025,
        paper_type="市地级",
        materials=[PASSAGE, CHART],
        material_ids=["m116_120", "m121_125", "m116_120"],
        stem=stem,
    )
    _post_import(client, headers, paper, "2025-shidi.json")
    db = SessionLocal()
    try:
        from app.models import QuestionVersion

        version = db.query(QuestionVersion).filter(QuestionVersion.stem == stem).one()
        links = (
            db.query(QuestionMaterialLink, Material)
            .join(Material, Material.id == QuestionMaterialLink.material_id)
            .filter(QuestionMaterialLink.question_id == version.question_id)
            .order_by(QuestionMaterialLink.sort_order)
            .all()
        )
        assert [mat.source_key for _link, mat in links] == [
            "guokao:2025:m116_120",
            "guokao:2025:m121_125",
        ]
        assert [link.sort_order for link, _mat in links] == [0, 1]
        assert [link.role for link, _mat in links] == ["primary", "primary"]
    finally:
        db.close()


def test_sync_dedupes_distinct_source_ids_that_resolve_to_one_row():
    """不同来源 id 解析到同一材料行时，也不能插入两行。"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        item = QuestionItem(
            origin_type="real",
            subject="行测",
            module="资料分析",
            canonical_hash="dup-source-keys-one-material",
        )
        mat = Material(
            source_key="guokao:2024:shared-passage",
            title="共用文章",
            content="第一段\n第二段",
            material_type="text",
        )
        db.add(item)
        db.add(mat)
        db.flush()
        stats = ImportStats()
        sync_material_links(
            db,
            item,
            ["para-1", "para-2"],
            {"para-1": mat, "para-2": mat},
            stats,
        )
        db.commit()
        links = (
            db.query(QuestionMaterialLink)
            .filter(QuestionMaterialLink.question_id == item.id)
            .all()
        )
        assert len(links) == 1
        assert links[0].material_id == mat.id
        assert links[0].sort_order == 0
        assert any("source=para-2" in w for w in stats.warnings)
    finally:
        db.close()


def test_unique_constraint_still_rejects_a_second_link():
    """去重在导入层完成，库唯一约束保持不变。"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        item = QuestionItem(
            origin_type="real",
            subject="行测",
            module="资料分析",
            canonical_hash="constraint-still-holds",
        )
        mat = Material(
            source_key="guokao:2024:constraint-passage",
            title="约束材料",
            content="正文",
            material_type="text",
        )
        db.add(item)
        db.add(mat)
        db.flush()
        db.add(
            QuestionMaterialLink(
                question_id=item.id, material_id=mat.id, role="primary", sort_order=0
            )
        )
        db.flush()
        db.add(
            QuestionMaterialLink(
                question_id=item.id, material_id=mat.id, role="primary", sort_order=1
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
    finally:
        db.close()
