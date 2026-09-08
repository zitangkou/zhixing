#!/usr/bin/env python3
"""从 papers/*.json 反向生成每年的标准状态文件，消除手工维护导致的漂移。

产出两件事（均以数据为准，不接受手工填写）：
1. {YEAR}/xingce/source/EXTRACT_STATUS.json —— 统一结构的断点/完成度状态
2. 回填 {YEAR}/xingce/meta.json 的 papers.{id}.modules（2024 缺失即由此补齐）

用法：
    python3 scripts/xingce/sync_status.py                # 全部年份
    python3 scripts/xingce/sync_status.py --year 2025
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "xingce-structured-data"
PAPERS = ("shengji", "shidi", "xingzhengzhifa")

# 各年官方题量（未核实的年份留空，避免把预设当事实）
OFFICIAL_TOTALS = {
    "2026": {"shengji": 135, "shidi": 130, "xingzhengzhifa": 130},
    "2025": {"shengji": 135, "shidi": 130, "xingzhengzhifa": 130},
    "2024": {"shengji": 135, "shidi": 130, "xingzhengzhifa": 130},
}


def summarize(paper_doc: dict, expected: int | None) -> dict:
    questions = [q for s in paper_doc.get("sections", []) for q in s.get("questions", [])]
    n = len(questions)
    answered = sum(1 for q in questions if q.get("answer"))
    tagged = sum(1 for q in questions if q.get("topic") and q.get("tag"))
    flags: collections.Counter = collections.Counter(
        f for q in questions for f in (q.get("flags") or []))
    if expected is None:
        status = "unknown_total"
    elif n < expected:
        status = "partial"
    else:
        status = "complete"
    return {
        "file": f"papers/{PAPER_FILE[paper_doc['paper_type']]}",
        "questions": n,
        "official_total": expected,
        "status": status,
        "answer_coverage": f"{answered}/{n}",
        "tag_coverage": f"{tagged}/{n}",
        "open_flags": dict(flags),
    }


PAPER_FILE = {"省级": "shengji.json", "市地级": "shidi.json", "行政执法类": "xingzhengzhifa.json"}


def sync_year(year_dir: Path, today: str) -> dict:
    papers_dir = year_dir / "xingce" / "papers"
    xingce = year_dir / "xingce"
    year = year_dir.name
    totals = OFFICIAL_TOTALS.get(year, {})

    paper_summaries = {}
    modules: dict = {}
    pending: list[str] = []

    for key in PAPERS:
        f = papers_dir / f"{key}.json"
        if not f.exists():
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        if doc.get("schema_version") != 2:
            pending.append(f"{key}.json 仍是旧 schema，先跑 normalize_papers.py")
        expected = totals.get(key)
        paper_summaries[key] = summarize(doc, expected)
        if expected and paper_summaries[key]["questions"] < expected:
            pending.append(
                f"{key} 缺 {expected - paper_summaries[key]['questions']} 题（官方 {expected}）")
        for m in doc.get("modules", []):
            modules.setdefault(m["name"], 0)
            modules[m["name"]] += m["question_count"]
        # 媒体与材料完整性
        for s in doc.get("sections", []):
            for q in s["questions"]:
                if "enumeration_missing" in (q.get("flags") or []):
                    pending.append(f"{key} {s['name']}#{q['number']} 列举条目缺失")

    status_doc = {
        "schema_version": 2,
        "year": int(year),
        "updated": today,
        "generated_by": "scripts/xingce/sync_status.py（请勿手工编辑，重跑脚本即可）",
        "papers": paper_summaries,
        "module_question_totals": modules,
        "pending": sorted(set(pending)),
        "source_files_present": sorted(p.name for p in (xingce / "source").glob("*.pdf")),
    }
    out = xingce / "source" / "EXTRACT_STATUS.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 回填 meta.json 的 modules
    meta_file = xingce / "meta.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        changed = False
        for key in PAPERS:
            f = papers_dir / f"{key}.json"
            if not f.exists() or key not in meta.get("papers", {}):
                continue
            doc = json.loads(f.read_text(encoding="utf-8"))
            target = meta["papers"][key]
            if target.get("modules") != doc.get("modules"):
                target["modules"] = doc.get("modules")
                changed = True
        if changed:
            meta["updated"] = today
            meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    return status_doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year")
    args = ap.parse_args()

    today = date.today().isoformat()
    for year_dir in sorted(DATA.glob("20*")):
        if args.year and year_dir.name != args.year:
            continue
        if not (year_dir / "xingce" / "papers").exists():
            continue
        doc = sync_year(year_dir, today)
        print(f"{year_dir.name}: papers={len(doc['papers'])} "
              f"模块={list(doc['module_question_totals'])} 待办={len(doc['pending'])}")
        for p in doc["pending"][:6]:
            print(f"    - {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
