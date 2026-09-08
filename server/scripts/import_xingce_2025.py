#!/usr/bin/env python3
"""2025 国考三卷真题幂等导入脚本。

将 xingce-structured-data/2025/xingce/papers/ 下的省级/市地/行政执法三卷
JSON 幂等导入统一题库（question_items / question_versions / qb_exam_papers /
qb_paper_sections / qb_paper_question_positions / qb_materials /
qb_question_material_links / qb_import_batches）。

用法：
    cd server && PYTHONPATH=. python3 scripts/import_xingce_2025.py
    cd server && PYTHONPATH=. python3 scripts/import_xingce_2025.py --papers shengji shidi
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import (
    Base,
    ExamPaperUnified,
    ImportBatch,
    Material,
    PaperQuestionPosition,
    PaperSection,
    QuestionItem,
    QuestionMaterialLink,
    QuestionVersion,
)
from app.timezone import now

# ── 路径 ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "xingce-structured-data" / "2025" / "xingce" / "papers"

PAPER_FILES = {
    "省级": "shengji.json",
    "市地级": "shidi.json",
    "行政执法类": "xingzhengzhifa.json",
}

PAPER_ARG_MAP = {
    "shengji": "省级",
    "shidi": "市地级",
    "xingzhengzhifa": "行政执法类",
    "省级": "省级",
    "市地级": "市地级",
    "行政执法类": "行政执法类",
}


# ── 哈希工具 ──────────────────────────────────────────
def _canonicalize_text(text: str) -> str:
    """标准化文本：去除多余空白、统一标点。"""
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r"\s+", " ", t)
    return t


def compute_canonical_hash(
    stem: str,
    options: dict | None,
    items: list | None,
    media: list | None = None,
    options_in_media: bool | None = None,
) -> str:
    """逻辑题去重哈希：标准化题干 + 选项 + 组合条目 + 媒体引用。

    图形推理等题的题干模板相同但图片不同，必须纳入 media 才能区分。
    三卷共享题（如政治理论 20 题）题干、选项和媒体均一致，哈希相同。
    """
    parts = [_canonicalize_text(stem)]
    if options:
        parts.append(json.dumps(options, sort_keys=True, ensure_ascii=False))
    if items:
        parts.append(json.dumps(items, sort_keys=True, ensure_ascii=False))
    if media:
        # 仅取媒体路径和类型，排除尺寸等可能变化的元数据
        media_signature = [
            {"path": m.get("path", ""), "kind": m.get("kind", "")}
            for m in media
            if isinstance(m, dict)
        ]
        parts.append(json.dumps(media_signature, sort_keys=True, ensure_ascii=False))
    if options_in_media:
        parts.append("options_in_media")
    raw = "||".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_content_hash(
    stem: str,
    items: list | None,
    options: dict | None,
    answer: Any,
    explanation: str,
    media: list | None,
    formulas: list | None,
    answer_source: str,
    topic: str,
    tag: str,
) -> str:
    """题目内容版本哈希：全部题面内容，用于检测版本变更。"""
    parts = [
        _canonicalize_text(stem),
        json.dumps(items, sort_keys=True, ensure_ascii=False) if items else "",
        json.dumps(options, sort_keys=True, ensure_ascii=False) if options else "",
        json.dumps(answer, sort_keys=True, ensure_ascii=False) if answer else "",
        _canonicalize_text(explanation),
        json.dumps(media, sort_keys=True, ensure_ascii=False) if media else "",
        json.dumps(formulas, sort_keys=True, ensure_ascii=False) if formulas else "",
        answer_source or "",
        topic or "",
        tag or "",
    ]
    raw = "||".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_material_hash(content: str, table_data: Any, title: str) -> str:
    parts = [
        _canonicalize_text(title),
        _canonicalize_text(content),
        json.dumps(table_data, sort_keys=True, ensure_ascii=False) if table_data else "",
    ]
    return hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()


def infer_response_type(answer: Any) -> str:
    """从答案格式推断作答类型。"""
    if answer is None:
        return "single"
    if isinstance(answer, list):
        return "multiple" if len(answer) > 1 else "single"
    s = str(answer).strip()
    if re.match(r"^[A-D]{2,}$", s):
        return "multiple"
    if s in ("对", "错", "正确", "错误", "T", "F", "√", "×"):
        return "judge"
    return "single"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ── 材料收集 ──────────────────────────────────────────
def collect_materials(paper_data: dict, year: int) -> dict[str, dict]:
    """从试卷 JSON 收集所有材料（顶层 materials dict + 各 section 的 materials list）。

    返回 {material_id: material_dict}，material_dict 至少含 id/title/content/material_type/source_ref/table_data/media/note。
    """
    result: dict[str, dict] = {}

    # 顶层 materials dict（如 m106_110）
    top_materials = paper_data.get("materials") or {}
    if isinstance(top_materials, dict):
        for mid, m in top_materials.items():
            if not isinstance(m, dict):
                continue
            result[mid] = {
                "id": m.get("id", mid),
                "title": m.get("title", ""),
                "content": m.get("content", ""),
                "material_type": m.get("kind", m.get("material_type", "text")),
                "source_ref": m.get("source_ref"),
                "table_data": m.get("table_data"),
                "media": m.get("media"),
                "note": m.get("note", ""),
                "extraction_method": m.get("extraction_method"),
            }

    # 各 section 的 materials list（资料分析等）
    for section in paper_data.get("sections", []):
        sec_materials = section.get("materials") or []
        if isinstance(sec_materials, list):
            for m in sec_materials:
                if not isinstance(m, dict):
                    continue
                mid = m.get("id", "")
                if not mid:
                    continue
                if mid in result:
                    continue  # 已从顶层或其他 section 收集
                result[mid] = {
                    "id": mid,
                    "title": m.get("title", ""),
                    "content": m.get("content", ""),
                    "material_type": m.get("kind", m.get("material_type", "text")),
                    "source_ref": m.get("source_ref"),
                    "table_data": m.get("table_data"),
                    "media": m.get("media"),
                    "note": m.get("note", ""),
                    "number_range": m.get("number_range"),
                }

    return result


# ── 核心导入逻辑 ──────────────────────────────────────
class ImportStats:
    def __init__(self) -> None:
        self.new_questions = 0
        self.updated_questions = 0
        self.reused_questions = 0
        self.new_versions = 0
        self.new_positions = 0
        self.updated_positions = 0
        self.reused_positions = 0
        self.new_materials = 0
        self.reused_materials = 0
        self.new_material_links = 0
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.per_paper: dict[str, dict] = {}


def upsert_material(db: Session, mid: str, mdata: dict, year: int, stats: ImportStats) -> Material:
    """创建或复用材料。"""
    source_key = f"guokao:{year}:{mid}"
    existing = db.query(Material).filter(Material.source_key == source_key).first()
    if existing:
        stats.reused_materials += 1
        return existing

    content_hash = compute_material_hash(
        mdata.get("content", ""),
        mdata.get("table_data"),
        mdata.get("title", ""),
    )
    mat = Material(
        source_key=source_key,
        title=mdata.get("title", ""),
        content=mdata.get("content", ""),
        material_type=mdata.get("material_type", "text"),
        source_ref_json=mdata.get("source_ref"),
        table_data_json=mdata.get("table_data"),
        media_json=mdata.get("media"),
        note=mdata.get("note", ""),
        content_hash=content_hash,
    )
    db.add(mat)
    db.flush()
    stats.new_materials += 1
    return mat


def upsert_question_item(
    db: Session,
    qdata: dict,
    canonical_hash: str,
    stats: ImportStats,
) -> QuestionItem:
    """创建或复用逻辑题目实体（按 canonical_hash 去重，三卷共享题自然合并）。"""
    existing = db.query(QuestionItem).filter(QuestionItem.canonical_hash == canonical_hash).first()
    if existing:
        stats.reused_questions += 1
        return existing

    module = qdata.get("section", "") or ""
    subtype = qdata.get("type", "") or ""
    answer = qdata.get("answer")
    response_type = infer_response_type(answer)

    item = QuestionItem(
        origin_type="real",
        subject="行测",
        module=module,
        subtype=subtype,
        response_type=response_type,
        canonical_hash=canonical_hash,
        difficulty=3,
        lifecycle_status="active",
    )
    db.add(item)
    db.flush()
    stats.new_questions += 1
    return item


def upsert_question_version(
    db: Session,
    item: QuestionItem,
    qdata: dict,
    stats: ImportStats,
) -> QuestionVersion:
    """创建或复用题目内容版本（按 question_id + content_hash 去重）。"""
    stem = qdata.get("stem", "") or ""
    items = qdata.get("items")
    options = qdata.get("options")
    answer = qdata.get("answer")
    explanation = qdata.get("explanation", "") or ""
    media = qdata.get("media")
    formulas = qdata.get("formulas")
    answer_source = qdata.get("answer_source", "") or ""
    topic = qdata.get("topic") or ""
    tag = qdata.get("tag") or ""

    content_hash = compute_content_hash(
        stem, items, options, answer, explanation, media, formulas, answer_source, topic, tag
    )

    existing = (
        db.query(QuestionVersion)
        .filter(QuestionVersion.question_id == item.id, QuestionVersion.content_hash == content_hash)
        .first()
    )
    if existing:
        return existing

    # 计算下一个 version_no
    max_ver = db.query(QuestionVersion).filter(QuestionVersion.question_id == item.id).count()
    version_no = max_ver + 1

    version = QuestionVersion(
        question_id=item.id,
        version_no=version_no,
        stem=stem,
        items_json=items,
        options_json=options,
        correct_answer_json=answer,
        explanation=explanation,
        analysis_payload_json=None,
        content_hash=content_hash,
        change_summary="initial import" if version_no == 1 else f"import revision v{version_no}",
        answer_source=answer_source,
        media_json=media,
        formulas_json=formulas,
        topic=topic if isinstance(topic, str) else json.dumps(topic, ensure_ascii=False),
        tag=tag if isinstance(tag, str) else json.dumps(tag, ensure_ascii=False),
    )
    db.add(version)
    db.flush()
    stats.new_versions += 1

    # 更新 question_items.current_version_id
    item.current_version_id = version.id
    return version


def upsert_position(
    db: Session,
    paper: ExamPaperUnified,
    section: PaperSection,
    item: QuestionItem,
    qdata: dict,
    section_index: int,
    sort_order: int,
    year: int,
    stats: ImportStats,
) -> PaperQuestionPosition:
    """创建或更新试卷题位（按 paper_id + number 幂等）。"""
    number = qdata.get("number", 0)
    source_key = f"guokao:{year}:{paper.paper_type}:{number}"
    provenance = qdata.get("provenance")
    flags = qdata.get("flags")

    existing = (
        db.query(PaperQuestionPosition)
        .filter(PaperQuestionPosition.paper_id == paper.id, PaperQuestionPosition.number == number)
        .first()
    )

    if existing:
        changed = False
        if existing.question_id != item.id:
            existing.question_id = item.id
            changed = True
        if existing.section_id != section.id:
            existing.section_id = section.id
            changed = True
        if existing.section_index != section_index:
            existing.section_index = section_index
            changed = True
        if existing.sort_order != sort_order:
            existing.sort_order = sort_order
            changed = True
        # JSON 字段比较
        if json.dumps(existing.provenance_json, sort_keys=True, ensure_ascii=False) != json.dumps(
            provenance, sort_keys=True, ensure_ascii=False
        ):
            existing.provenance_json = provenance
            changed = True
        if json.dumps(existing.quality_flags_json, sort_keys=True, ensure_ascii=False) != json.dumps(
            flags, sort_keys=True, ensure_ascii=False
        ):
            existing.quality_flags_json = flags
            changed = True
        if existing.source_key != source_key:
            existing.source_key = source_key
            changed = True

        if changed:
            stats.updated_positions += 1
        else:
            stats.reused_positions += 1
        return existing

    pos = PaperQuestionPosition(
        paper_id=paper.id,
        section_id=section.id,
        question_id=item.id,
        number=number,
        section_index=section_index,
        sort_order=sort_order,
        provenance_json=provenance,
        quality_flags_json=flags,
        source_key=source_key,
    )
    db.add(pos)
    db.flush()
    stats.new_positions += 1
    return pos


def sync_material_links(
    db: Session,
    item: QuestionItem,
    material_ids: list[str],
    material_map: dict[str, Material],
    stats: ImportStats,
) -> None:
    """同步题目-材料关联（先删后建，保证幂等）。"""
    if not material_ids:
        return

    # 删除旧关联
    db.query(QuestionMaterialLink).filter(QuestionMaterialLink.question_id == item.id).delete()

    for idx, mid in enumerate(material_ids):
        mat = material_map.get(mid)
        if mat is None:
            stats.warnings.append(f"material_id={mid} not found for question {item.id}")
            continue
        link = QuestionMaterialLink(
            question_id=item.id,
            material_id=mat.id,
            role="primary",
            sort_order=idx,
        )
        db.add(link)
        stats.new_material_links += 1
    db.flush()


def upsert_section(
    db: Session,
    paper: ExamPaperUnified,
    sec_name: str,
    sort_order: int,
    number_start: int,
    number_end: int,
    question_count: int,
    stats: ImportStats,
) -> PaperSection:
    """创建或复用试卷模块（按 paper_id + sort_order 幂等）。"""
    existing = (
        db.query(PaperSection)
        .filter(PaperSection.paper_id == paper.id, PaperSection.sort_order == sort_order)
        .first()
    )
    if existing:
        changed = False
        if existing.name != sec_name:
            existing.name = sec_name
            changed = True
        if existing.number_start != number_start:
            existing.number_start = number_start
            changed = True
        if existing.number_end != number_end:
            existing.number_end = number_end
            changed = True
        if existing.question_count != question_count:
            existing.question_count = question_count
            changed = True
        return existing

    sec = PaperSection(
        paper_id=paper.id,
        name=sec_name,
        sort_order=sort_order,
        number_start=number_start,
        number_end=number_end,
        question_count=question_count,
    )
    db.add(sec)
    db.flush()
    return sec


def import_paper(
    db: Session,
    paper_type: str,
    json_path: Path,
    batch: ImportBatch,
    stats: ImportStats,
) -> ExamPaperUnified:
    """导入单份试卷（全量 upsert，幂等）。"""
    paper_data = json.loads(json_path.read_text(encoding="utf-8"))
    year = paper_data.get("exam_year", 2025)
    title = paper_data.get("exam_name", "")
    schema_version = str(paper_data.get("schema_version", ""))
    total_questions = paper_data.get("total_questions", 0) or paper_data.get("actual_question_count", 0)

    # Upsert paper
    paper = (
        db.query(ExamPaperUnified)
        .filter(
            ExamPaperUnified.exam_year == year,
            ExamPaperUnified.exam_kind == "国考",
            ExamPaperUnified.paper_type == paper_type,
        )
        .first()
    )
    if paper is None:
        paper = ExamPaperUnified(
            exam_year=year,
            exam_kind="国考",
            paper_type=paper_type,
            title=title,
            source_document=str(json_path.name),
            schema_version=schema_version,
            total_questions=total_questions,
            import_batch_id=batch.id,
        )
        db.add(paper)
        db.flush()
    else:
        paper.title = title
        paper.source_document = str(json_path.name)
        paper.schema_version = schema_version
        paper.total_questions = total_questions
        paper.import_batch_id = batch.id

    # 收集材料
    materials_raw = collect_materials(paper_data, year)
    material_map: dict[str, Material] = {}
    for mid, mdata in materials_raw.items():
        material_map[mid] = upsert_material(db, mid, mdata, year, stats)

    # 记录源数据中的题号和 section sort_order，用于事后清理陈旧数据
    source_numbers: set[int] = set()
    source_section_orders: set[int] = set()

    # Upsert sections 和题目
    sections_data = paper_data.get("sections", [])
    paper_stats = {"positions": 0, "questions_new": 0, "questions_reused": 0, "materials": len(material_map)}
    global_sort = 0

    for sec_idx, section in enumerate(sections_data):
        sec_name = section.get("name", "")
        questions = section.get("questions", [])
        if not questions:
            continue

        source_section_orders.add(sec_idx)
        number_start = questions[0].get("number", 0)
        number_end = questions[-1].get("number", 0)

        sec = upsert_section(
            db, paper, sec_name, sec_idx, number_start, number_end, len(questions), stats
        )

        for q_idx, qdata in enumerate(questions):
            global_sort += 1
            number = qdata.get("number", 0)
            source_numbers.add(number)

            stem = qdata.get("stem", "") or ""
            options = qdata.get("options")
            items = qdata.get("items")
            media = qdata.get("media")
            options_in_media = qdata.get("options_in_media")

            canonical_hash = compute_canonical_hash(stem, options, items, media, options_in_media)

            # Upsert question item（共享题自动合并）
            item = upsert_question_item(db, qdata, canonical_hash, stats)
            # Upsert version
            upsert_question_version(db, item, qdata, stats)

            # Upsert position
            upsert_position(
                db, paper, sec, item, qdata,
                section_index=q_idx + 1,
                sort_order=global_sort,
                year=year,
                stats=stats,
            )

            # Material links
            mat_ids = qdata.get("material_ids") or []
            if mat_ids:
                sync_material_links(db, item, mat_ids, material_map, stats)

            paper_stats["positions"] += 1

        paper_stats["questions_new"] = stats.new_questions
        paper_stats["questions_reused"] = stats.reused_questions

    # 清理陈旧 positions（源数据中已不存在的题号）
    stale_positions = (
        db.query(PaperQuestionPosition)
        .filter(PaperQuestionPosition.paper_id == paper.id)
        .filter(~PaperQuestionPosition.number.in_(source_numbers))
        .all()
    )
    for pos in stale_positions:
        db.delete(pos)

    # 清理陈旧 sections
    stale_sections = (
        db.query(PaperSection)
        .filter(PaperSection.paper_id == paper.id)
        .filter(~PaperSection.sort_order.in_(source_section_orders))
        .all()
    )
    for sec in stale_sections:
        db.delete(sec)

    stats.per_paper[paper_type] = paper_stats
    db.flush()
    return paper


def run_import(paper_types: list[str] | None = None) -> ImportStats:
    """执行导入，返回统计。"""
    if paper_types is None:
        paper_types = list(PAPER_FILES.keys())

    # 确保表存在
    Base.metadata.create_all(bind=engine)

    stats = ImportStats()
    source_hashes = []
    source_paths = []

    db = SessionLocal()
    try:
        # 计算所有源文件哈希
        for pt in paper_types:
            fname = PAPER_FILES[pt]
            fpath = DATA_DIR / fname
            source_paths.append(str(fpath))
            source_hashes.append(file_sha256(fpath))

        combined_hash = hashlib.sha256("|".join(source_hashes).encode()).hexdigest()

        batch = ImportBatch(
            source_path=";".join(source_paths),
            source_hash=combined_hash,
            schema_version="2",
            parsed_at=now(),
            status="in_progress",
        )
        db.add(batch)
        db.flush()

        for pt in paper_types:
            fname = PAPER_FILES[pt]
            fpath = DATA_DIR / fname
            if not fpath.exists():
                stats.errors.append(f"file not found: {fpath}")
                continue
            try:
                import_paper(db, pt, fpath, batch, stats)
            except Exception as e:
                stats.errors.append(f"import {pt} failed: {e}")
                import traceback
                traceback.print_exc()

        # 更新 batch
        batch.new_count = stats.new_questions + stats.new_positions + stats.new_materials
        batch.updated_count = stats.updated_questions + stats.updated_positions
        batch.reused_count = stats.reused_questions + stats.reused_positions + stats.reused_materials
        batch.skipped_count = 0
        batch.error_count = len(stats.errors)
        batch.warnings_json = stats.warnings if stats.warnings else None
        batch.status = "failed" if stats.errors else "completed"
        batch.detail_json = {
            "new_questions": stats.new_questions,
            "reused_questions": stats.reused_questions,
            "new_versions": stats.new_versions,
            "new_positions": stats.new_positions,
            "updated_positions": stats.updated_positions,
            "reused_positions": stats.reused_positions,
            "new_materials": stats.new_materials,
            "reused_materials": stats.reused_materials,
            "new_material_links": stats.new_material_links,
            "per_paper": stats.per_paper,
        }
        db.commit()
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def print_report(stats: ImportStats) -> None:
    print("\n" + "=" * 60)
    print("  2025 国考三卷导入报告")
    print("=" * 60)
    print(f"  新建题目实体:   {stats.new_questions}")
    print(f"  复用题目实体:   {stats.reused_questions}")
    print(f"  新建题目版本:   {stats.new_versions}")
    print(f"  新建题位:       {stats.new_positions}")
    print(f"  更新题位:       {stats.updated_positions}")
    print(f"  复用题位:       {stats.reused_positions}")
    print(f"  新建材料:       {stats.new_materials}")
    print(f"  复用材料:       {stats.reused_materials}")
    print(f"  材料关联:       {stats.new_material_links}")
    print(f"  错误:           {len(stats.errors)}")
    print(f"  警告:           {len(stats.warnings)}")
    print("-" * 60)
    for pt, ps in stats.per_paper.items():
        print(f"  {pt}: {ps['positions']} 题位, 材料 {ps.get('materials', 0)}")
    if stats.errors:
        print("-" * 60)
        for e in stats.errors:
            print(f"  ERROR: {e}")
    if stats.warnings:
        print("-" * 60)
        for w in stats.warnings[:20]:
            print(f"  WARN: {w}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="2025 国考三卷真题幂等导入")
    parser.add_argument(
        "--papers",
        nargs="+",
        choices=list(PAPER_ARG_MAP.keys()),
        help="指定导入的卷（默认全部）",
    )
    args = parser.parse_args()

    if args.papers:
        paper_types = [PAPER_ARG_MAP[p] for p in args.papers]
    else:
        paper_types = None

    stats = run_import(paper_types)
    print_report(stats)

    if stats.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
