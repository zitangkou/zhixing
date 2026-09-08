"""统一题库导入测试：幂等性、共享题、对账、重建。

使用独立临时库，避免污染开发库。须在导入 app 之前设置 DATABASE_URL。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_TEST_DB = Path(__file__).resolve().parent / "_question_bank_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["SECRET_KEY"] = "qb-test-secret"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402
    ExamPaperUnified,
    ImportBatch,
    Material,
    PaperQuestionPosition,
    PaperSection,
    QuestionItem,
    QuestionMaterialLink,
    QuestionVersion,
)
from scripts.import_xingce_2025 import run_import  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PAPERS_DIR = REPO_ROOT / "xingce-structured-data" / "2025" / "xingce" / "papers"

EXPECTED_COUNTS = {"省级": 135, "市地级": 130, "行政执法类": 130}


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def first_import():
    """首次导入。"""
    return run_import()


@pytest.fixture(scope="module")
def second_import():
    """第二次导入（验证幂等性）。"""
    return run_import()


# ── 1. 幂等性测试 ─────────────────────────────────────


class TestIdempotency:
    def test_second_run_zero_new_questions(self, first_import, second_import):
        assert second_import.new_questions == 0, "第二次导入不应新建题目实体"

    def test_second_run_zero_new_versions(self, first_import, second_import):
        assert second_import.new_versions == 0, "第二次导入不应新建题目版本"

    def test_second_run_zero_new_positions(self, first_import, second_import):
        assert second_import.new_positions == 0, "第二次导入不应新建题位"

    def test_second_run_zero_updated_positions(self, first_import, second_import):
        assert second_import.updated_positions == 0, "第二次导入不应更新题位（内容未变）"

    def test_second_run_all_positions_reused(self, first_import, second_import):
        assert second_import.reused_positions == 395, "第二次导入应复用全部 395 题位"

    def test_total_positions_unchanged_after_rerun(self, db_session, first_import, second_import):
        total = db_session.query(PaperQuestionPosition).count()
        assert total == 395, f"重跑后题位总数应为 395，实际 {total}"

    def test_total_entities_unchanged_after_rerun(self, db_session, first_import, second_import):
        entities = db_session.query(QuestionItem).filter(QuestionItem.origin_type == "real").count()
        assert entities == first_import.new_questions, "重跑后题目实体数不应变化"

    def test_no_errors(self, first_import, second_import):
        assert first_import.errors == []
        assert second_import.errors == []


# ── 2. 共享题测试 ─────────────────────────────────────


class TestSharedQuestions:
    def test_political_theory_20_entities(self, db_session, first_import):
        entities = (
            db_session.query(QuestionItem)
            .filter(QuestionItem.module == "政治理论", QuestionItem.origin_type == "real")
            .all()
        )
        assert len(entities) == 20, f"政治理论应有 20 个逻辑题实体，实际 {len(entities)}"

    def test_each_political_theory_entity_has_3_positions(self, db_session, first_import):
        entities = (
            db_session.query(QuestionItem)
            .filter(QuestionItem.module == "政治理论", QuestionItem.origin_type == "real")
            .all()
        )
        for e in entities:
            pos_count = (
                db_session.query(PaperQuestionPosition)
                .filter(PaperQuestionPosition.question_id == e.id)
                .count()
            )
            assert pos_count == 3, f"政治理论题 {e.id} 应有 3 个题位（三卷共享），实际 {pos_count}"

    def test_shared_entities_spread_across_three_papers(self, db_session, first_import):
        """每个政治理论实体的 3 个题位分别属于 3 份不同试卷。"""
        entities = (
            db_session.query(QuestionItem)
            .filter(QuestionItem.module == "政治理论", QuestionItem.origin_type == "real")
            .all()
        )
        for e in entities[:5]:  # 抽样检查前 5 个
            positions = (
                db_session.query(PaperQuestionPosition)
                .filter(PaperQuestionPosition.question_id == e.id)
                .all()
            )
            paper_ids = {pos.paper_id for pos in positions}
            assert len(paper_ids) == 3, f"政治理论题 {e.id} 应关联 3 份不同试卷"

    def test_shared_question_same_answer_across_papers(self, db_session, first_import):
        """同一道共享题在三卷中的答案一致。"""
        entity = (
            db_session.query(QuestionItem)
            .filter(QuestionItem.module == "政治理论")
            .first()
        )
        version = (
            db_session.query(QuestionVersion)
            .filter(QuestionVersion.question_id == entity.id)
            .order_by(QuestionVersion.version_no.desc())
            .first()
        )
        answer = version.correct_answer_json
        positions = (
            db_session.query(PaperQuestionPosition)
            .filter(PaperQuestionPosition.question_id == entity.id)
            .all()
        )
        for pos in positions:
            v = (
                db_session.query(QuestionVersion)
                .filter(QuestionVersion.question_id == pos.question_id)
                .order_by(QuestionVersion.version_no.desc())
                .first()
            )
            assert v.correct_answer_json == answer, f"共享题在不同卷中答案不一致: {v.correct_answer_json} vs {answer}"


# ── 3. 对账测试 ───────────────────────────────────────


class TestReconciliation:
    @pytest.mark.parametrize("paper_type,expected", list(EXPECTED_COUNTS.items()))
    def test_per_paper_position_count(self, db_session, first_import, paper_type, expected):
        paper = (
            db_session.query(ExamPaperUnified)
            .filter(ExamPaperUnified.paper_type == paper_type)
            .first()
        )
        assert paper is not None, f"未找到 {paper_type} 试卷"
        count = (
            db_session.query(PaperQuestionPosition)
            .filter(PaperQuestionPosition.paper_id == paper.id)
            .count()
        )
        assert count == expected, f"{paper_type} 应有 {expected} 题位，实际 {count}"

    def test_total_positions_395(self, db_session, first_import):
        total = db_session.query(PaperQuestionPosition).count()
        assert total == 395, f"总题位数应为 395，实际 {total}"

    @pytest.mark.parametrize("paper_type", list(EXPECTED_COUNTS.keys()))
    def test_number_continuity(self, db_session, first_import, paper_type):
        paper = (
            db_session.query(ExamPaperUnified)
            .filter(ExamPaperUnified.paper_type == paper_type)
            .first()
        )
        positions = (
            db_session.query(PaperQuestionPosition)
            .filter(PaperQuestionPosition.paper_id == paper.id)
            .order_by(PaperQuestionPosition.number)
            .all()
        )
        numbers = [pos.number for pos in positions]
        expected = list(range(1, len(numbers) + 1))
        assert numbers == expected, f"{paper_type} 题号不连续: missing={set(expected) - set(numbers)}"

    def test_answer_coverage_100_percent(self, db_session, first_import):
        positions = db_session.query(PaperQuestionPosition).all()
        with_answer = 0
        for pos in positions:
            version = (
                db_session.query(QuestionVersion)
                .filter(QuestionVersion.question_id == pos.question_id)
                .order_by(QuestionVersion.version_no.desc())
                .first()
            )
            if version and version.correct_answer_json:
                with_answer += 1
        assert with_answer == 395, f"答案覆盖率应为 100% (395/395)，实际 {with_answer}/395"

    def test_all_positions_have_provenance(self, db_session, first_import):
        without_provenance = (
            db_session.query(PaperQuestionPosition)
            .filter(PaperQuestionPosition.provenance_json.is_(None))
            .count()
        )
        assert without_provenance == 0, f"有 {without_provenance} 个题位缺失 provenance"

    def test_materials_linked(self, db_session, first_import):
        materials = db_session.query(Material).all()
        assert len(materials) > 0, "应导入材料实体"
        links = db_session.query(QuestionMaterialLink).count()
        assert links > 0, "应存在题目-材料关联"

    def test_section_counts_match(self, db_session, first_import):
        """每个试卷的模块数和题量与源 JSON 一致。"""
        for paper_type in EXPECTED_COUNTS:
            paper = (
                db_session.query(ExamPaperUnified)
                .filter(ExamPaperUnified.paper_type == paper_type)
                .first()
            )
            sections = (
                db_session.query(PaperSection)
                .filter(PaperSection.paper_id == paper.id)
                .order_by(PaperSection.sort_order)
                .all()
            )
            total_in_sections = sum(s.question_count for s in sections)
            assert total_in_sections == EXPECTED_COUNTS[paper_type], (
                f"{paper_type} 模块题量合计 {total_in_sections} != {EXPECTED_COUNTS[paper_type]}"
            )

    def test_unique_constraint_paper_number(self, db_session, first_import):
        """(paper_id, number) 唯一约束：每个试卷内题号不重复。"""
        papers = db_session.query(ExamPaperUnified).all()
        for paper in papers:
            positions = (
                db_session.query(PaperQuestionPosition)
                .filter(PaperQuestionPosition.paper_id == paper.id)
                .all()
            )
            numbers = [pos.number for pos in positions]
            assert len(numbers) == len(set(numbers)), f"{paper.paper_type} 存在重复题号"


# ── 4. 重建测试 ───────────────────────────────────────


class TestRebuild:
    def _rebuild_paper(self, db_session, paper_type: str) -> dict:
        """从数据库重建试卷结构。"""
        paper = (
            db_session.query(ExamPaperUnified)
            .filter(ExamPaperUnified.paper_type == paper_type)
            .first()
        )
        sections = (
            db_session.query(PaperSection)
            .filter(PaperSection.paper_id == paper.id)
            .order_by(PaperSection.sort_order)
            .all()
        )
        result = {"paper_type": paper.paper_type, "sections": []}
        for sec in sections:
            positions = (
                db_session.query(PaperQuestionPosition)
                .filter(
                    PaperQuestionPosition.paper_id == paper.id,
                    PaperQuestionPosition.section_id == sec.id,
                )
                .order_by(PaperQuestionPosition.number)
                .all()
            )
            questions = []
            for pos in positions:
                version = (
                    db_session.query(QuestionVersion)
                    .filter(QuestionVersion.question_id == pos.question_id)
                    .order_by(QuestionVersion.version_no.desc())
                    .first()
                )
                questions.append(
                    {
                        "number": pos.number,
                        "section": sec.name,
                        "stem": version.stem,
                        "items": version.items_json,
                        "options": version.options_json,
                        "answer": version.correct_answer_json,
                        "explanation": version.explanation,
                        "provenance": pos.provenance_json,
                        "flags": pos.quality_flags_json,
                    }
                )
            result["sections"].append({"name": sec.name, "questions": questions})
        return result

    @pytest.mark.parametrize("paper_type", list(EXPECTED_COUNTS.keys()))
    def test_rebuild_section_structure(self, db_session, first_import, paper_type):
        """重建的试卷模块结构与源 JSON 一致。"""
        rebuilt = self._rebuild_paper(db_session, paper_type)
        source_file = PAPERS_DIR / {"省级": "shengji.json", "市地级": "shidi.json", "行政执法类": "xingzhengzhifa.json"}[paper_type]
        source = json.loads(source_file.read_text(encoding="utf-8"))

        assert len(rebuilt["sections"]) == len(source["sections"]), (
            f"{paper_type} 模块数不匹配: rebuilt={len(rebuilt['sections'])} source={len(source['sections'])}"
        )
        for reb_sec, src_sec in zip(rebuilt["sections"], source["sections"]):
            assert reb_sec["name"] == src_sec["name"], f"模块名不匹配: {reb_sec['name']} vs {src_sec['name']}"
            assert len(reb_sec["questions"]) == len(src_sec["questions"]), (
                f"{paper_type}/{reb_sec['name']} 题量不匹配: {len(reb_sec['questions'])} vs {len(src_sec['questions'])}"
            )

    @pytest.mark.parametrize("paper_type", list(EXPECTED_COUNTS.keys()))
    def test_rebuild_answers_match_source(self, db_session, first_import, paper_type):
        """重建的答案与源 JSON 完全一致。"""
        rebuilt = self._rebuild_paper(db_session, paper_type)
        source_file = PAPERS_DIR / {"省级": "shengji.json", "市地级": "shidi.json", "行政执法类": "xingzhengzhifa.json"}[paper_type]
        source = json.loads(source_file.read_text(encoding="utf-8"))

        mismatches = 0
        for reb_sec, src_sec in zip(rebuilt["sections"], source["sections"]):
            for reb_q, src_q in zip(reb_sec["questions"], src_sec["questions"]):
                if reb_q["answer"] != src_q["answer"]:
                    mismatches += 1
        assert mismatches == 0, f"{paper_type} 有 {mismatches} 道题答案与源 JSON 不一致"

    @pytest.mark.parametrize("paper_type", list(EXPECTED_COUNTS.keys()))
    def test_rebuild_stems_match_source(self, db_session, first_import, paper_type):
        """重建的题干与源 JSON 完全一致。"""
        rebuilt = self._rebuild_paper(db_session, paper_type)
        source_file = PAPERS_DIR / {"省级": "shengji.json", "市地级": "shidi.json", "行政执法类": "xingzhengzhifa.json"}[paper_type]
        source = json.loads(source_file.read_text(encoding="utf-8"))

        mismatches = 0
        for reb_sec, src_sec in zip(rebuilt["sections"], source["sections"]):
            for reb_q, src_q in zip(reb_sec["questions"], src_sec["questions"]):
                if reb_q["stem"] != src_q.get("stem", ""):
                    mismatches += 1
        assert mismatches == 0, f"{paper_type} 有 {mismatches} 道题题干与源 JSON 不一致"

    def test_rebuild_provenance_preserved(self, db_session, first_import):
        """provenance 信息在重建中完整保留。"""
        rebuilt = self._rebuild_paper(db_session, "省级")
        source = json.loads((PAPERS_DIR / "shengji.json").read_text(encoding="utf-8"))

        for reb_sec, src_sec in zip(rebuilt["sections"], source["sections"]):
            for reb_q, src_q in zip(reb_sec["questions"], src_sec["questions"]):
                src_prov = src_q.get("provenance")
                if src_prov:
                    assert reb_q["provenance"] is not None, f"Q{reb_q['number']} provenance 丢失"
                    assert reb_q["provenance"].get("role") == src_prov.get("role"), (
                        f"Q{reb_q['number']} provenance.role 不匹配"
                    )

    def test_rebuild_flags_preserved(self, db_session, first_import):
        """flags 信息在重建中完整保留。"""
        rebuilt = self._rebuild_paper(db_session, "省级")
        source = json.loads((PAPERS_DIR / "shengji.json").read_text(encoding="utf-8"))

        for reb_sec, src_sec in zip(rebuilt["sections"], source["sections"]):
            for reb_q, src_q in zip(reb_sec["questions"], src_sec["questions"]):
                src_flags = src_q.get("flags") or []
                reb_flags = reb_q["flags"] or []
                assert len(reb_flags) == len(src_flags), (
                    f"Q{reb_q['number']} flags 数量不匹配: {len(reb_flags)} vs {len(src_flags)}"
                )


# ── 5. 数据完整性测试 ─────────────────────────────────


class TestDataIntegrity:
    def test_every_position_has_question(self, db_session, first_import):
        positions = db_session.query(PaperQuestionPosition).all()
        for pos in positions:
            item = db_session.query(QuestionItem).filter(QuestionItem.id == pos.question_id).first()
            assert item is not None, f"题位 {pos.id} 关联的题目 {pos.question_id} 不存在"

    def test_every_question_has_version(self, db_session, first_import):
        items = db_session.query(QuestionItem).all()
        for item in items:
            version = (
                db_session.query(QuestionVersion)
                .filter(QuestionVersion.question_id == item.id)
                .first()
            )
            assert version is not None, f"题目 {item.id} 没有版本"

    def test_current_version_id_set(self, db_session, first_import):
        items = db_session.query(QuestionItem).all()
        for item in items:
            assert item.current_version_id is not None, f"题目 {item.id} 未设置 current_version_id"
            version = db_session.query(QuestionVersion).filter(QuestionVersion.id == item.current_version_id).first()
            assert version is not None, f"题目 {item.id} 的 current_version_id 指向不存在的版本"

    def test_import_batch_recorded(self, db_session, first_import):
        batches = db_session.query(ImportBatch).all()
        assert len(batches) >= 1, "应至少有一条导入批次记录"
        latest = batches[-1]
        assert latest.status == "completed", f"最新导入批次状态应为 completed，实际 {latest.status}"
        assert latest.error_count == 0, "导入批次不应有错误"

    def test_canonical_hash_unique_for_distinct_questions(self, db_session, first_import):
        """不同题干的题目应有不同 canonical_hash（共享题除外）。"""
        items = db_session.query(QuestionItem).all()
        hashes = [item.canonical_hash for item in items]
        # 所有实体的 canonical_hash 应该唯一（因为我们按 hash 去重创建实体）
        assert len(hashes) == len(set(hashes)), "存在重复 canonical_hash 的题目实体"

    def test_material_content_not_empty(self, db_session, first_import):
        materials = db_session.query(Material).all()
        for mat in materials:
            # 材料可以是文本、表格或图表型；至少有 content、table_data 或 media 之一
            has_content = bool(mat.content) or mat.table_data_json is not None or bool(mat.media_json)
            assert has_content, f"材料 {mat.id} ({mat.source_key}) 既无 content 也无 table_data/media"
