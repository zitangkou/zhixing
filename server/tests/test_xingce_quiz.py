"""行测真题学员 API：抽题过滤无答案/高风险 flag，并判分。"""
from __future__ import annotations

import os
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_xingce_quiz.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SECRET_KEY"] = "xingce-quiz-secret"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.question_bank import (  # noqa: E402
    ExamPaperUnified,
    PaperQuestionPosition,
    PaperSection,
    QuestionItem,
    QuestionVersion,
)


def _seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    paper = ExamPaperUnified(
        exam_year=2025,
        exam_kind="国考",
        paper_type="省级",
        title="2025 国考行测省级",
        total_questions=3,
    )
    db.add(paper)
    db.flush()
    section = PaperSection(paper_id=paper.id, name="政治理论", sort_order=0, question_count=3)
    db.add(section)
    db.flush()

    index = 0

    def add_q(stem: str, answer: str | None, flags: list | None = None, module="政治理论") -> str:
        nonlocal index
        index += 1
        item = QuestionItem(
            origin_type="real",
            subject="行测",
            module=module,
            subtype="时政",
            response_type="single",
            canonical_hash=stem,
            lifecycle_status="active",
        )
        db.add(item)
        db.flush()
        version = QuestionVersion(
            question_id=item.id,
            version_no=1,
            stem=stem,
            options_json={"A": "甲", "B": "乙", "C": "丙", "D": "丁"},
            correct_answer_json=answer,
            explanation="解析",
            content_hash=stem,
        )
        db.add(version)
        db.flush()
        item.current_version_id = version.id
        db.add(
            PaperQuestionPosition(
                paper_id=paper.id,
                section_id=section.id,
                question_id=item.id,
                number=index,
                section_index=index,
                sort_order=index,
                quality_flags_json=flags,
            )
        )
        return item.id

    ok_id = add_q("可练题干", "B")
    add_q("无答案题干", None)
    add_q("错配题干", "A", ["section_type_mismatch"])
    db.commit()
    db.close()
    return ok_id


def test_xingce_catalog_and_quiz_filters_and_grades():
    ok_id = _seed()
    with TestClient(app) as client:
        catalog = client.get("/api/xingce/catalog")
        assert catalog.status_code == 200
        body = catalog.json()
        assert body["code"] == 0
        theory = next(m for m in body["data"]["modules"] if m["key"] == "政治理论")
        assert theory["count"] == 1
        assert 2025 in body["data"]["years"]
        papers = body["data"]["papers"]
        assert len(papers) == 1
        assert papers[0]["year"] == 2025
        assert papers[0]["paperType"] == "省级"
        assert papers[0]["count"] == 1

        scoped = client.get(
            "/api/xingce/catalog",
            params={"year": 2025, "paperType": "省级"},
        )
        scoped_theory = next(
            m for m in scoped.json()["data"]["modules"] if m["key"] == "政治理论"
        )
        assert scoped_theory["count"] == 1
        assert scoped.json()["data"]["papers"] == []

        quiz = client.get("/api/xingce/quiz", params={"module": "政治理论", "year": 2025})
        assert quiz.status_code == 200
        data = quiz.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == ok_id
        assert data[0]["options"][1].startswith("B.")

        wrong = client.post("/api/xingce/answer", json={"questionId": ok_id, "answer": "A. 甲"})
        assert wrong.json()["data"]["correct"] is False

        right = client.post("/api/xingce/answer", json={"questionId": ok_id, "answer": "B. 乙"})
        assert right.json()["data"]["correct"] is True

        empty = client.get("/api/xingce/quiz", params={"module": "资料分析"})
        assert empty.json()["code"] == 404
