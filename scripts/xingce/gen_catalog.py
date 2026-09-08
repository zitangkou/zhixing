#!/usr/bin/env python3
"""catalog.json 脚本化生成与 CI 断言。

扫描 xingce-structured-data/{year}/xingce/papers/*.json，自动汇总题量与
答案覆盖率，生成/校验 catalog.json。手工维护字段（status / notes / media /
answer_source）从已有 catalog 中保留，新增年份/试卷用默认值占位。

用法：
    python3 scripts/xingce/gen_catalog.py            # 重新生成 catalog.json
    python3 scripts/xingce/gen_catalog.py --check    # 仅断言，不写文件（CI 用）
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "xingce-structured-data"
CATALOG = DATA / "catalog.json"
SKIP_FILES = {"all_merged.json"}

# 手工维护字段——生成时从已有 catalog 保留，不参与扫描计算
HAND_FIELDS_YEAR = ("status", "notes", "media", "answer_source")
HAND_FIELDS_TOP = ("known_gaps", "schema_version", "tools")

DEFAULT_STATUS = "papers_assembled"
DEFAULT_MEDIA = {"pages": 0, "figures": 0}


def iter_year_dirs() -> list[Path]:
    """返回所有年份目录（按年份降序，最新在前，与 catalog 惯例一致）。"""
    dirs = [p for p in DATA.iterdir() if p.is_dir() and p.name.isdigit()]
    return sorted(dirs, key=lambda p: int(p.name), reverse=True)


def iter_paper_files(year_dir: Path) -> list[Path]:
    """返回某年份下所有试卷 JSON（跳过 all_merged.json 等汇总文件）。"""
    papers_dir = year_dir / "xingce" / "papers"
    if not papers_dir.is_dir():
        return []
    files = [
        p for p in sorted(papers_dir.glob("*.json"))
        if p.name not in SKIP_FILES
    ]
    return files


def count_questions(paper_data: dict) -> int:
    """遍历 sections[].questions[] 累加题数。"""
    total = 0
    for section in paper_data.get("sections", []):
        total += len(section.get("questions", []))
    return total


def count_answered(paper_data: dict) -> tuple[int, int]:
    """返回 (answer 非空题数, 总题数)。"""
    answered = 0
    total = 0
    for section in paper_data.get("sections", []):
        for q in section.get("questions", []):
            total += 1
            if q.get("answer"):
                answered += 1
    return answered, total


def scan() -> dict:
    """扫描全部数据，返回生成的 catalog 结构（不含手工字段填充）。"""
    years = []
    for year_dir in iter_year_dirs():
        year = int(year_dir.name)
        papers = []
        year_answered = 0
        year_total = 0

        for pf in iter_paper_files(year_dir):
            with pf.open(encoding="utf-8") as f:
                data = json.load(f)
            paper_id = pf.stem
            paper_type = data.get("paper_type", paper_id)
            total_q = count_questions(data)
            answered, total = count_answered(data)
            year_answered += answered
            year_total += total

            rel_path = f"{year}/xingce/papers/{pf.name}"
            papers.append({
                "id": paper_id,
                "paper_type": paper_type,
                "file": rel_path,
                "total_questions": total_q,
            })

        if not papers:
            continue

        coverage_pct = round(year_answered / year_total * 100) if year_total else 0
        answer_coverage = f"{year_answered}/{year_total} ({coverage_pct}%)"

        years.append({
            "year": year,
            "subject": "xingce",
            "status": DEFAULT_STATUS,
            "path": f"{year}/xingce",
            "papers": papers,
            "media": dict(DEFAULT_MEDIA),
            "notes": "",
            "answer_coverage": answer_coverage,
            "answer_source": None,
        })

    return {
        "project": "国考行测真题结构化数据",
        "root": "xingce-structured-data",
        "updated": date.today().isoformat(),
        "years": years,
        "known_gaps": [],
        "schema_version": 2,
        "tools": {
            "validate": "scripts/xingce/validate_papers.py",
            "migrate": "scripts/xingce/normalize_papers.py",
            "status": "scripts/xingce/sync_status.py",
        },
    }


def merge_hand_fields(generated: dict, existing: dict) -> dict:
    """将已有 catalog 中的手工维护字段合并到生成结果中。"""
    # 顶层手工字段
    for key in HAND_FIELDS_TOP:
        if key in existing:
            generated[key] = existing[key]

    # 按年份匹配手工字段
    existing_years = {y["year"]: y for y in existing.get("years", [])}
    for year_entry in generated["years"]:
        y = year_entry["year"]
        if y in existing_years:
            src = existing_years[y]
            for key in HAND_FIELDS_YEAR:
                if key in src:
                    year_entry[key] = src[key]
    return generated


# --check 模式下不参与比较的字段（时间戳等非数据字段）
CHECK_IGNORE_FIELDS = {"updated"}

# 列表元素匹配键：列表 of dicts 按指定字段配对比较，而非按索引
LIST_KEY_FIELDS = {
    "years": "year",
    "papers": "id",
}


def _match_list_items(a_list: list, b_list: list, key_field: str) -> list[tuple[dict | None, dict | None, str]]:
    """按键字段配对两个列表，返回 [(a_item, b_item, label), ...]。"""
    a_map = {item.get(key_field): item for item in a_list if isinstance(item, dict)}
    b_map = {item.get(key_field): item for item in b_list if isinstance(item, dict)}
    all_keys = list(a_map.keys()) + [k for k in b_map if k not in a_map]
    pairs = []
    for k in all_keys:
        a_item = a_map.get(k)
        b_item = b_map.get(k)
        label = f"{key_field}={k}"
        pairs.append((a_item, b_item, label))
    return pairs


def deep_diff(a: dict, b: dict, path: str = "") -> list[str]:
    """递归比较两个 dict，返回差异描述列表。列表 of dicts 按键字段配对。"""
    diffs = []
    keys = set(a.keys()) | set(b.keys())
    for key in sorted(keys):
        if path == "" and key in CHECK_IGNORE_FIELDS:
            continue
        cur = f"{path}.{key}" if path else key
        if key not in a:
            diffs.append(f"  {cur}: 仅在现有 catalog 中存在 (={json.dumps(b[key], ensure_ascii=False)})")
        elif key not in b:
            diffs.append(f"  {cur}: 仅在扫描结果中存在 (={json.dumps(a[key], ensure_ascii=False)})")
        elif isinstance(a[key], dict) and isinstance(b[key], dict):
            diffs.extend(deep_diff(a[key], b[key], cur))
        elif isinstance(a[key], list) and isinstance(b[key], list):
            key_field = LIST_KEY_FIELDS.get(key)
            if key_field and all(isinstance(x, dict) for x in a[key] + b[key]):
                # 按键字段配对比较
                pairs = _match_list_items(a[key], b[key], key_field)
                for a_item, b_item, label in pairs:
                    item_path = f"{cur}[{label}]"
                    if a_item is None:
                        diffs.append(f"  {item_path}: 仅在现有 catalog 中存在")
                    elif b_item is None:
                        diffs.append(f"  {item_path}: 仅在扫描结果中存在")
                    else:
                        diffs.extend(deep_diff(a_item, b_item, item_path))
            else:
                if len(a[key]) != len(b[key]):
                    diffs.append(f"  {cur}: 列表长度不同 (扫描={len(a[key])}, 现有={len(b[key])})")
                else:
                    for i, (va, vb) in enumerate(zip(a[key], b[key])):
                        if isinstance(va, dict) and isinstance(vb, dict):
                            diffs.extend(deep_diff(va, vb, f"{cur}[{i}]"))
                        elif va != vb:
                            diffs.append(f"  {cur}[{i}]: 扫描={json.dumps(va, ensure_ascii=False)}, 现有={json.dumps(vb, ensure_ascii=False)}")
        elif a[key] != b[key]:
            diffs.append(f"  {cur}: 扫描={json.dumps(a[key], ensure_ascii=False)}, 现有={json.dumps(b[key], ensure_ascii=False)}")
    return diffs


def cmd_check() -> int:
    """--check 模式：断言现有 catalog 与扫描结果一致。"""
    if not CATALOG.exists():
        print(f"[FAIL] catalog.json 不存在: {CATALOG}")
        return 1

    with CATALOG.open(encoding="utf-8") as f:
        existing = json.load(f)

    generated = scan()
    generated = merge_hand_fields(generated, existing)

    diffs = deep_diff(generated, existing)

    if diffs:
        print("[FAIL] catalog.json 与实际扫描结果不一致：")
        for d in diffs:
            print(d)
        print(f"\n共 {len(diffs)} 处差异。运行 `python3 scripts/xingce/gen_catalog.py` 重新生成。")
        return 1

    total_papers = sum(len(y["papers"]) for y in generated["years"])
    total_questions = sum(p["total_questions"] for y in generated["years"] for p in y["papers"])
    print(f"[OK] catalog.json 校验通过：{len(generated['years'])} 年份 / {total_papers} 试卷 / {total_questions} 题")
    return 0


def cmd_generate() -> int:
    """生成模式：扫描并写入 catalog.json。"""
    existing = {}
    if CATALOG.exists():
        with CATALOG.open(encoding="utf-8") as f:
            existing = json.load(f)

    generated = scan()
    generated = merge_hand_fields(generated, existing)

    with CATALOG.open("w", encoding="utf-8") as f:
        json.dump(generated, f, ensure_ascii=False, indent=2)
        f.write("\n")

    total_papers = sum(len(y["papers"]) for y in generated["years"])
    total_questions = sum(p["total_questions"] for y in generated["years"] for p in y["papers"])
    print(f"[OK] 已生成 catalog.json：{len(generated['years'])} 年份 / {total_papers} 试卷 / {total_questions} 题")
    print(f"     路径: {CATALOG}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="catalog.json 脚本化生成与校验")
    parser.add_argument("--check", action="store_true", help="仅断言现有 catalog 与扫描结果一致，不写文件")
    args = parser.parse_args()

    if args.check:
        return cmd_check()
    return cmd_generate()


if __name__ == "__main__":
    sys.exit(main())
