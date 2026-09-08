#!/usr/bin/env python3
"""生成题入库脚本：将 xingce-structured-data/generated/ 下的 5 个引擎产出
幂等导入 P0 统一题库（question_items + question_versions）。

用法：
    cd server && PYTHONPATH=. python3 scripts/import_generated_questions.py
    cd server && PYTHONPATH=. python3 scripts/import_generated_questions.py --dry-run
    cd server && PYTHONPATH=. python3 scripts/import_generated_questions.py --engines qa_verbal_v2 qa_theory_v1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

# 复用 P0 导入脚本的哈希函数（保证去重逻辑一致）
from scripts.import_xingce_2025 import (
    _canonicalize_text,
    compute_canonical_hash,
    compute_content_hash,
    infer_response_type,
)
from app.database import Base, SessionLocal, engine as db_engine
from app.models import (
    ImportBatch,
    Material,
    QuestionItem,
    QuestionMaterialLink,
    QuestionVersion,
)
from app.timezone import now

# ── 路径 ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATED_DIR = REPO_ROOT / "xingce-structured-data" / "generated"

# 引擎注册表：引擎标识 → 文件名
ENGINE_FILES: dict[str, str] = {
    "qa_data_analysis_v2": "qa_data_analysis_v2.json",
    "qa_quantity_v1": "qa_quantity_v1.json",
    "qa_verbal_v2": "qa_verbal_v2.json",
    "qa_judgment_v1": "qa_judgment_v1.json",
    "qa_theory_v1": "qa_theory_v1.json",
}


# ── 统计 ──────────────────────────────────────────────
class GenImportStats:
    def __init__(self) -> None:
        self.total_source = 0
        self.new_questions = 0
        self.updated_questions = 0
        self.reused_questions = 0
        self.skipped_questions = 0
        self.new_versions = 0
        self.new_materials = 0
        self.new_material_links = 0
        self.per_engine: dict[str, dict] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.dry_run = False


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_analysis_payload(qdata: dict, engine: str) -> dict:
    """将引擎专属元信息组装为 analysis_payload_json。"""
    payload: dict[str, Any] = {"_engine": engine}

    # 资料分析 / 数量关系
    for key in ("calc_tree", "distractors", "dual_solve"):
        if key in qdata and qdata[key] is not None:
            payload[key] = qdata[key]

    # 言语理解
    for key in ("passage", "target_word", "pos", "logic_signal", "context_constraints"):
        if key in qdata and qdata[key] is not None:
            payload[key] = qdata[key]

    # 判断推理
    for key in ("definition", "key_elements", "options_detail", "validation"):
        if key in qdata and qdata[key] is not None:
            payload[key] = qdata[key]

    # 常识/政治理论
    for key in ("knowledge_point_id", "options_detail", "validation"):
        if key in qdata and qdata[key] is not None:
            payload[key] = qdata[key]

    # 通用 generation_meta
    if "generation_meta" in qdata and qdata["generation_meta"] is not None:
        payload["generation_meta"] = qdata["generation_meta"]

    # 原始 question_id（溯源）
    if "question_id" in qdata:
        payload["_source_question_id"] = qdata["question_id"]

    return payload


def _upsert_material_for_generated(
    db: Session, qid: str, material_data: dict, engine: str, stats: GenImportStats
) -> Material | None:
    """为资料分析生成题创建/复用材料（模拟数据）。"""
    if not material_data:
        return None

    material_id = material_data.get("material_id", f"{engine}-{qid}-mat")
    source_key = f"generated:{engine}:{material_id}"

    existing = db.query(Material).filter(Material.source_key == source_key).first()
    if existing:
        return existing

    content = material_data.get("content", "")
    title = material_data.get("title", f"{engine} 模拟材料 {material_id}")
    material_type = material_data.get("data_type", "synthetic")

    content_hash = hashlib.sha256(
        (title + content + json.dumps(material_data.get("raw_data", {}), sort_keys=True, ensure_ascii=False)).encode()
    ).hexdigest()

    mat = Material(
        source_key=source_key,
        title=title,
        content=content,
        material_type=material_type,
        source_ref_json={"engine": engine, "material_id": material_id},
        table_data_json=material_data.get("raw_data"),
        media_json=None,
        note=material_data.get("note", ""),
        content_hash=content_hash,
    )
    db.add(mat)
    db.flush()
    stats.new_materials += 1
    return mat


def import_engine(
    db: Session,
    engine: str,
    json_path: Path,
    stats: GenImportStats,
) -> None:
    """导入单个引擎的所有生成题。"""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    questions = data.get("questions", [])
    engine_stats = {"source": len(questions), "new": 0, "updated": 0, "reused": 0, "skipped": 0}

    for qdata in questions:
        stats.total_source += 1
        qid = qdata.get("question_id", "")
        if not qid:
            stats.skipped_questions += 1
            engine_stats["skipped"] += 1
            stats.warnings.append(f"{engine}: question missing question_id, skipped")
            continue

        stem = qdata.get("stem", "") or ""
        options = qdata.get("options")
        items = qdata.get("items")
        media = qdata.get("media")
        answer = qdata.get("answer")
        explanation = qdata.get("explanation", "") or ""
        module = qdata.get("module", "") or ""
        subtype = qdata.get("subtype", "") or ""
        difficulty = qdata.get("difficulty", 3)
        response_type = infer_response_type(answer)

        canonical_hash = compute_canonical_hash(stem, options, items, media)

        # 查找已有题目（优先按 id，其次按 canonical_hash）
        item = db.query(QuestionItem).filter(QuestionItem.id == qid).first()
        if item is None:
            item = db.query(QuestionItem).filter(QuestionItem.canonical_hash == canonical_hash).first()

        if item is None:
            # 新建
            if not stats.dry_run:
                item = QuestionItem(
                    id=qid,
                    origin_type="generated",
                    subject="行测",
                    module=module,
                    subtype=subtype,
                    response_type=response_type,
                    canonical_hash=canonical_hash,
                    difficulty=difficulty,
                    lifecycle_status="pending_review",
                )
                db.add(item)
                db.flush()
            stats.new_questions += 1
            engine_stats["new"] += 1
        else:
            # 已存在，检查是否需要更新
            changed = False
            if item.origin_type != "generated":
                item.origin_type = "generated"
                changed = True
            if item.module != module:
                item.module = module
                changed = True
            if item.subtype != subtype:
                item.subtype = subtype
                changed = True
            if item.response_type != response_type:
                item.response_type = response_type
                changed = True
            if item.difficulty != difficulty:
                item.difficulty = difficulty
                changed = True
            if item.canonical_hash != canonical_hash:
                item.canonical_hash = canonical_hash
                changed = True

            if changed:
                stats.updated_questions += 1
                engine_stats["updated"] += 1
            else:
                stats.reused_questions += 1
                engine_stats["reused"] += 1

        if stats.dry_run:
            continue

        # 计算内容哈希，决定是否新建版本
        answer_source = qdata.get("answer_source", "") or ""
        topic = qdata.get("topic", "") or ""
        formulas = qdata.get("formulas")
        content_hash = compute_content_hash(
            stem, items, options, answer, explanation, media, formulas, answer_source, topic, engine
        )

        existing_version = (
            db.query(QuestionVersion)
            .filter(QuestionVersion.question_id == item.id, QuestionVersion.content_hash == content_hash)
            .first()
        )

        if existing_version is None:
            max_ver = db.query(QuestionVersion).filter(QuestionVersion.question_id == item.id).count()
            version_no = max_ver + 1
            analysis_payload = _build_analysis_payload(qdata, engine)

            version = QuestionVersion(
                question_id=item.id,
                version_no=version_no,
                stem=stem,
                items_json=items,
                options_json=options,
                correct_answer_json=answer,
                explanation=explanation,
                analysis_payload_json=analysis_payload,
                content_hash=content_hash,
                change_summary="generated import" if version_no == 1 else f"generated import v{version_no}",
                answer_source=answer_source,
                media_json=media,
                formulas_json=formulas,
                topic=topic if isinstance(topic, str) else json.dumps(topic, ensure_ascii=False),
                tag=engine,
            )
            db.add(version)
            db.flush()
            stats.new_versions += 1
            item.current_version_id = version.id

        # 材料关联（资料分析）
        material_data = qdata.get("material")
        if material_data:
            mat = _upsert_material_for_generated(db, qid, material_data, engine, stats)
            if mat:
                # 先删旧关联再建（幂等）
                db.query(QuestionMaterialLink).filter(
                    QuestionMaterialLink.question_id == item.id
                ).delete()
                link = QuestionMaterialLink(
                    question_id=item.id,
                    material_id=mat.id,
                    role="primary",
                    sort_order=0,
                )
                db.add(link)
                stats.new_material_links += 1

    stats.per_engine[engine] = engine_stats
    db.flush()


def run_import(engines: list[str] | None = None, dry_run: bool = False) -> GenImportStats:
    """执行生成题导入。"""
    if engines is None:
        engines = list(ENGINE_FILES.keys())

    Base.metadata.create_all(bind=db_engine)
    stats = GenImportStats()
    stats.dry_run = dry_run

    source_hashes = []
    source_paths = []
    for engine in engines:
        fname = ENGINE_FILES.get(engine)
        if not fname:
            stats.errors.append(f"unknown engine: {engine}")
            continue
        fpath = GENERATED_DIR / fname
        if not fpath.exists():
            stats.errors.append(f"file not found: {fpath}")
            continue
        source_paths.append(str(fpath))
        source_hashes.append(file_sha256(fpath))

    if dry_run:
        # dry-run 不写数据库，直接导入到临时 session 但不 commit
        db = SessionLocal()
        try:
            for engine in engines:
                fname = ENGINE_FILES.get(engine)
                if not fname:
                    continue
                fpath = GENERATED_DIR / fname
                if not fpath.exists():
                    continue
                import_engine(db, engine, fpath, stats)
            db.rollback()
        finally:
            db.close()
        return stats

    combined_hash = hashlib.sha256("|".join(source_hashes).encode()).hexdigest()

    db = SessionLocal()
    try:
        batch = ImportBatch(
            source_path=";".join(source_paths),
            source_hash=combined_hash,
            schema_version="generated-v1",
            parsed_at=now(),
            status="in_progress",
        )
        db.add(batch)
        db.flush()

        for engine in engines:
            fname = ENGINE_FILES.get(engine)
            if not fname:
                continue
            fpath = GENERATED_DIR / fname
            if not fpath.exists():
                continue
            try:
                import_engine(db, engine, fpath, stats)
            except Exception as e:
                stats.errors.append(f"import {engine} failed: {e}")
                import traceback
                traceback.print_exc()

        batch.new_count = stats.new_questions
        batch.updated_count = stats.updated_questions
        batch.reused_count = stats.reused_questions
        batch.skipped_count = stats.skipped_questions
        batch.error_count = len(stats.errors)
        batch.warnings_json = stats.warnings if stats.warnings else None
        batch.status = "failed" if stats.errors else "completed"
        batch.detail_json = {
            "engine": "generated_questions",
            "total_source": stats.total_source,
            "new_versions": stats.new_versions,
            "new_materials": stats.new_materials,
            "new_material_links": stats.new_material_links,
            "per_engine": stats.per_engine,
        }
        db.commit()
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def print_report(stats: GenImportStats) -> None:
    mode = " [DRY-RUN]" if stats.dry_run else ""
    print("\n" + "=" * 60)
    print(f"  生成题入库报告{mode}")
    print("=" * 60)
    print(f"  源题量:         {stats.total_source}")
    print(f"  新建题目实体:   {stats.new_questions}")
    print(f"  更新题目实体:   {stats.updated_questions}")
    print(f"  复用题目实体:   {stats.reused_questions}")
    print(f"  跳过:           {stats.skipped_questions}")
    print(f"  新建版本:       {stats.new_versions}")
    print(f"  新建材料:       {stats.new_materials}")
    print(f"  材料关联:       {stats.new_material_links}")
    print(f"  错误:           {len(stats.errors)}")
    print(f"  警告:           {len(stats.warnings)}")
    print("-" * 60)
    for engine, es in stats.per_engine.items():
        print(f"  {engine}: 源={es['source']} 新建={es['new']} 更新={es['updated']} 复用={es['reused']} 跳过={es['skipped']}")
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
    parser = argparse.ArgumentParser(description="生成题幂等入库")
    parser.add_argument("--dry-run", action="store_true", help="预演模式，不写数据库")
    parser.add_argument(
        "--engines",
        nargs="+",
        choices=list(ENGINE_FILES.keys()),
        help="指定导入的引擎（默认全部）",
    )
    args = parser.parse_args()

    stats = run_import(engines=args.engines, dry_run=args.dry_run)
    print_report(stats)

    if stats.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
