#!/usr/bin/env python3
"""M1：xingce-structured-data (schema v2) → 统一题库 qb_* 导入器。

发布期安全：默认写 server/data/zhixing_dev.db（开发副本），生产库需显式 --db 且发布后启用。
用法（PYTHONPATH=server，cwd=server）：
    ../.venv/bin/python ../scripts/xingce/qb_import.py --year 2025 --dry-run
    ../.venv/bin/python ../scripts/xingce/qb_import.py --year 2025 2026
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "server"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.question_bank import (ExamPaperUnified, ImportBatch, Material,
                                      PaperQuestionPosition, PaperSection,
                                      QuestionItem, QuestionVersion)

DATA = REPO / "xingce-structured-data"
PAPERS = (("shengji", "省级"), ("shidi", "市地级"), ("xingzhengzhifa", "行政执法类"))
HIGH_RISK = {"section_type_mismatch", "content_mismatch_needs_source", "enumeration_missing"}
FOOT = re.compile(r"第\d+页/共\d+页")
norm = lambda s: re.sub(r"[^\u4e00-\u9fa50-9A-Za-z]", "", FOOT.sub("", s or ""))
sha = lambda s: hashlib.sha1(s.encode("utf-8")).hexdigest()


def canonical(stem, items, options):
    opts = options or {}
    return sha(norm(stem) + norm(json.dumps(items or [], ensure_ascii=False)) +
               norm(json.dumps([opts.get(k, "") for k in "ABCD"], ensure_ascii=False)))


def content_hash(q):
    return sha(norm(q["stem"]) + norm(json.dumps(q.get("options") or {}, ensure_ascii=False)) +
               str(q.get("answer")) + norm((q.get("explanation") or "")[:400]))


def load_training(year):
    p = DATA / str(year) / "xingce" / "_extract" / "answer_decisions.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return {x["number"]: x for x in d.get("questions", [])}


def import_paper(session, year, paper_id, paper_type, batch_stats):
    f = DATA / str(year) / "xingce" / "papers" / f"{paper_id}.json"
    doc = json.loads(f.read_text(encoding="utf-8"))
    year_n = doc["exam_year"]

    paper = session.scalar(select(ExamPaperUnified).where(
        ExamPaperUnified.exam_year == year_n, ExamPaperUnified.exam_kind == "国考",
        ExamPaperUnified.paper_type == paper_type))
    if paper is None:
        paper = ExamPaperUnified(exam_year=year_n, exam_kind="国考", paper_type=paper_type,
                                 title=doc["exam_name"], schema_version="2",
                                 total_questions=doc["actual_question_count"],
                                 source_document=doc.get("notes", "")[:500],
                                 import_batch_id=None)
        session.add(paper)
        session.flush()
        batch_stats["new_papers"] += 1
    else:
        batch_stats["reused_papers"] += 1

    for si, sec in enumerate(doc.get("sections", [])):
        section = session.scalar(select(PaperSection).where(
            PaperSection.paper_id == paper.id, PaperSection.name == sec["name"]))
        if section is None:
            nums = [q["number"] for q in sec["questions"]]
            section = PaperSection(paper_id=paper.id, name=sec["name"], sort_order=si,
                                   number_start=min(nums), number_end=max(nums),
                                   question_count=len(sec["questions"]))
            session.add(section)
            session.flush()
        # 材料
        for m in sec.get("materials", []):
            skey = f"guokao:{year_n}:{m['id']}"
            if session.scalar(select(Material).where(Material.source_key == skey)) is None:
                session.add(Material(source_key=skey, title=m.get("title", ""), content=m.get("content", ""),
                                     material_type=m.get("kind", "text"), table_data_json=m.get("table_data"),
                                     media_json=m.get("media"), note=m.get("note", ""),
                                     source_ref_json={"file": f"{paper_id}.json"}))
                batch_stats["new_materials"] += 1

        for idx, q in enumerate(sec["questions"]):
            n = q["number"]
            chash = canonical(q["stem"], q.get("items"), q.get("options"))
            item = session.scalar(select(QuestionItem).where(QuestionItem.canonical_hash == chash))
            created = False
            if item is None:
                item = QuestionItem(origin_type="real", subject="行测", module=q["section"],
                                    subtype=q.get("subtype") or q["type"], response_type="single",
                                    difficulty=3, canonical_hash=chash)
                session.add(item)
                session.flush()
                batch_stats["new_questions"] += 1
                created = True
            else:
                batch_stats["reused_questions"] += 1
            chash_v = content_hash(q)
            if session.scalar(select(QuestionVersion).where(
                    QuestionVersion.question_id == item.id, QuestionVersion.content_hash == chash_v)) is None:
                vno = (session.scalar(select(QuestionVersion.version_no).where(
                    QuestionVersion.question_id == item.id).order_by(QuestionVersion.version_no.desc())) or 0) + 1
                payload = None
                session.add(QuestionVersion(
                    question_id=item.id, version_no=vno, stem=q["stem"],
                    items_json=q.get("items"), options_json=q.get("options"),
                    correct_answer_json=q.get("answer"), explanation=q.get("explanation") or "",
                    answer_source=q.get("answer_source") or "", topic=q.get("topic") or "",
                    tag=q.get("tag") or "", media_json=q.get("media"), formulas_json=q.get("formulas"),
                    content_hash=chash_v, change_summary=f"{SRC_TAG}/{year_n}{paper_type}#{n}"))
                batch_stats["new_versions"] += 1
            # 题位
            pkey = f"guokao:{year_n}:{paper_id}:{n}"
            if session.scalar(select(PaperQuestionPosition).where(PaperQuestionPosition.source_key == pkey)) is None:
                session.add(PaperQuestionPosition(
                    paper_id=paper.id, section_id=section.id, question_id=item.id, number=n,
                    section_index=idx, provenance_json=q.get("provenance"),
                    quality_flags_json=q.get("flags"), source_key=pkey))
                batch_stats["new_positions"] += 1
            else:
                batch_stats["skipped_positions"] += 1


SRC_TAG = "qb_import_v1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", nargs="+", required=True)
    ap.add_argument("--papers", nargs="+", default=[p for p, _ in PAPERS])
    ap.add_argument("--db", default=str(REPO / "server/data/zhixing_dev.db"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    engine = create_engine(f"sqlite:///{args.db}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    stats = {"new_papers": 0, "reused_papers": 0, "new_questions": 0, "reused_questions": 0,
             "new_versions": 0, "new_positions": 0, "skipped_positions": 0, "new_materials": 0}
    batch = ImportBatch(source_path=str(DATA), source_hash=sha(",".join(args.year) + args.db),
                        schema_version="2", status="pending" if args.dry_run else "completed")
    if not args.dry_run:
        session.add(batch)
        session.flush()
    try:
        for y in args.year:
            for pid, ptype in PAPERS:
                if pid in args.papers:
                    import_paper(session, y, pid, ptype, stats)
        if args.dry_run:
            session.rollback()
            print(f"[DRY-RUN] {stats}")
        else:
            batch.import_batch_id = batch.id
            session.commit()
            print(f"[OK] {stats}")
            # 门禁报告
            hr = session.query(PaperQuestionPosition).filter(
                PaperQuestionPosition.quality_flags_json.op('LIKE')('%section_type_mismatch%')).count()
            na = session.query(PaperQuestionPosition).count()
            print(f"题位总数 {na}，高风险 flag 题位 {hr}（默认集合应排除）")
    except Exception as e:
        session.rollback()
        print(f"[FAILED] {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
