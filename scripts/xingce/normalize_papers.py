#!/usr/bin/env python3
"""行测真题数据 schema v1 → v2 归一迁移。

规范定义见 xingce-structured-data/_schema/conventions.md。
幂等：已是 schema_version=2 的文件跳过；重复执行不产生额外变化。

用法：
    python3 scripts/xingce/normalize_papers.py --dry-run   # 只出报告，不写文件
    python3 scripts/xingce/normalize_papers.py             # 实际迁移
    python3 scripts/xingce/normalize_papers.py --year 2025 # 只处理某一年
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "xingce-structured-data"
PAPERS = ("shengji", "shidi", "xingzhengzhifa")

SECTION_TYPE = {
    "政治理论": "政治理论",
    "常识判断": "常识判断",
    "数量关系": "数量关系",
    "资料分析": "资料分析",
}

# v1 英文/混用值 → v2 中文枚举
TYPE_MAP = {
    "verbal": "选词填空",
    "reading": "片段阅读",
    "sentence_reorder": "语句排序",
    "quantity": "数量关系",
    "graphic": "图形推理",
    "definition": "定义判断",
    "analogy": "类比推理",
    "logic": "逻辑判断",
    "data_analysis": "资料分析",
    "选词填空": "选词填空",
    "片段阅读": "片段阅读",
    "语句排序": "语句排序",
    "语句填空": "语句填空",
    "标题选择": "标题选择",
    "文章阅读": "文章阅读",
    "图形推理": "图形推理",
    "定义判断": "定义判断",
    "类比推理": "类比推理",
    "逻辑判断": "逻辑判断",
    "数量关系": "数量关系",
    "资料分析": "资料分析",
    "政治理论": "政治理论",
    "常识判断": "常识判断",
}

# 判断推理模块里被误标 single_choice 的题：按题干内容归类（全部打 inferred + mismatch 标记）
JUDGMENT_FALLBACK_RULES = (
    (lambda s: "重新排列" in s, "语句排序"),
    (lambda s: "没有解释下列哪一问题" in s or "这段文字" in s, "片段阅读"),
    (lambda s: "因此," in s and "_" in s, "语句填空"),
    (lambda s: "问:" in s or "问：" in s, "数量关系"),
)

PROVENANCE_RULES = (
    (re.compile(r"^资料映射市地(\d+)$"),
     dict(role="mapped_from_shidi", from_paper="市地级", from_number=1)),
    (re.compile(r"^与市地共享\(市地(\d+)\)$"),
     dict(role="shared_with_shidi", from_paper="市地级", from_number=1)),
    (re.compile(r"^省级数量独有\(差异卷(\d+)\)$"),
     dict(role="province_only", from_paper="差异卷", diff_label=1)),
    (re.compile(r"^省级判断差异题\(差异卷标注(\d+)\)$"),
     dict(role="diff_book", from_paper="差异卷", diff_label=1)),
    (re.compile(r"^主卷共享（差异题待精确替换）$"), dict(role="shared", flag="diff_pending_replace")),
    (re.compile(r"^主卷共享（部分由差异卷替换）$"), dict(role="shared", flag="diff_pending_replace")),
)

SIMPLE_PROVENANCE = {
    "主卷": "main",
    "主卷共享": "shared",
    "省级判断": "province_only",
    "省级判断补全": "backfilled",
    # 市地 / 执法卷简写
    "共享": "shared",
    "数量共享": "shared",
    "判断": "main",
    "资料": "main",
}

# 含卷种关键词的兜底规则（在 SIMPLE 与正则之后）
KEYWORD_PROVENANCE = (
    ("行政执法", dict(role="diff_book", from_paper="行政执法类")),
    ("市地资料", dict(role="mapped_from_shidi", from_paper="市地级", flag="material_borrowed")),
    ("市地", dict(role="shared_with_shidi", from_paper="市地级")),
)


def norm_media_path(path: str) -> str:
    """统一为相对 xingce/ 的自描述路径。"""
    if not path:
        return path
    if path.startswith("media/"):
        return path
    if re.match(r"^https?://|^/", path):
        return path  # 异常值原样保留，交给校验报告
    return f"media/{path.lstrip('./')}"


def extract_media_paths(value):
    """兼容 list[dict] / list[str] / None，返回 path 列表。"""
    out = []
    for item in value or []:
        if isinstance(item, dict) and item.get("path"):
            out.append(item["path"])
        elif isinstance(item, str):
            out.append(item)
    return out


def resolve_type(q: dict, section: str, flags: set) -> str:
    raw = q.get("type")
    if raw and raw != "single_choice":
        mapped = TYPE_MAP.get(raw)
        if mapped:
            return mapped
        flags.add("type_unmapped")
        return raw or ""
    # single_choice 或缺失：先按模块，再按题干
    if section in SECTION_TYPE:
        return SECTION_TYPE[section]
    if section == "判断推理":
        for pred, t in JUDGMENT_FALLBACK_RULES:
            if pred(str(q.get("stem", ""))):
                flags.add("type_inferred_from_stem")
                flags.add("section_type_mismatch")
                return t
    flags.add("type_unresolved")
    return ""


def parse_provenance(q: dict, stats: collections.Counter) -> dict:
    raw = str(q.get("source_note") or "").strip()
    prov = {"role": "unknown", "from_paper": None, "from_number": None,
            "diff_label": None, "raw_note": raw or None}
    if not raw:
        return prov
    for pattern, spec in PROVENANCE_RULES:
        m = pattern.match(raw)
        if not m:
            continue
        groups = m.groups()
        prov["role"] = spec["role"]
        prov["from_paper"] = spec.get("from_paper")
        if spec.get("from_number"):
            prov["from_number"] = int(groups[0])
        if spec.get("diff_label"):
            prov["diff_label"] = groups[0]
        if spec.get("flag"):
            prov["_flag"] = spec["flag"]
        stats[f"provenance:{spec['role']}"] += 1
        return prov
    if raw in SIMPLE_PROVENANCE:
        prov["role"] = SIMPLE_PROVENANCE[raw]
        stats[f"provenance:{prov['role']}"] += 1
        return prov
    for keyword, spec in KEYWORD_PROVENANCE:
        if keyword in raw:
            prov["role"] = spec["role"]
            prov["from_paper"] = spec.get("from_paper")
            if spec.get("flag"):
                prov["_flag"] = spec["flag"]
            stats[f"provenance:{spec['role']}"] += 1
            return prov
    stats["provenance:unknown"] += 1
    return prov


ENUM_STEM_HINTS = ("相符的有", "正确的有", "有几项", "不正确的有", "表述正确", "对应正确的有")
COUNT_OPTION = re.compile(r"^\d+\s*项$")


def needs_enumeration(q: dict) -> bool:
    """判断该题是否属于「需要条目正文」的组合题 / 计数题。

    三个条件同时成立才算：
    1. 题干以列举设问收尾（「……相符的有：」「……正确的有几项？」）；
    2. **选项形态确实是指向条目**——含 ①②③ 的组合项，或「N 项」计数项；
    3. 否则视为正常单选题（「下列表述正确的是：」+ 四个完整陈述句），不缺条目。
    只靠题干收尾会误伤后者——这是本规则初版踩过的坑。
    """
    stem = str(q.get("stem") or "").rstrip()
    if not stem.endswith(("：", ":", "？", "?")) or not any(h in stem for h in ENUM_STEM_HINTS):
        return False
    options = q.get("options") or {}
    values = [str(v) for v in options.values()] if isinstance(options, dict) else []
    has_combo = any(any(c in v for c in "①②③④⑤") for v in values)
    is_count = bool(values) and all(COUNT_OPTION.match(v.strip()) for v in values)
    return has_combo or is_count


def normalize_question(q: dict, section: str, base_dir: Path, stats: collections.Counter) -> dict:
    flags = set(q.get("flags") or [])
    media_paths = [norm_media_path(p) for p in extract_media_paths(q.get("media"))]
    missing_files = [p for p in media_paths if base_dir and not (base_dir / p).exists()]
    had_figure_claim = bool(q.get("has_figure"))
    options = q.get("options") or None

    prov = parse_provenance(q, stats)
    extra_flag = prov.pop("_flag", None)
    if extra_flag:
        flags.add(extra_flag)
    if prov["role"] == "mapped_from_shidi":
        flags.add("material_borrowed")

    type_flags: set = set()
    qtype = resolve_type({**q, "type": q.get("type")}, section, type_flags)
    flags |= type_flags

    valid_media = [p for p in media_paths if p not in missing_files]
    needs_media = options is None or had_figure_claim or qtype == "图形推理"
    if needs_media and not valid_media:
        flags.add("media_missing")
    if missing_files:
        flags.add("media_file_absent")
    if q.get("answer") in (None, ""):
        flags.add("answer_missing")

    media = []
    for item in (q.get("media") or []):
        if isinstance(item, dict):
            new = dict(item)
            new["path"] = norm_media_path(str(item.get("path", "")))
            media.append(new)
        else:
            media.append({"path": norm_media_path(str(item)), "kind": "figure", "label": ""})

    raw_material = str(q.get("material_id") or q.get("material_ref") or "")
    material_ids = [p.strip() for p in raw_material.replace("，", "+").split("+") if p.strip()]

    # 列举设问必须有条目正文（在 items 里或在材料里），两者皆无即内容不完整
    if needs_enumeration(q) and not q.get("items") and not material_ids:
        flags.add("enumeration_missing")
        stats["enumeration_missing"] += 1

    prov["source_ref"] = {
        "file": q.get("source_file"),
        "page": q.get("source_page"),
    }

    return {
        "number": q.get("number"),
        "section": section,
        "stem": q.get("stem", ""),
        "items": q.get("items"),
        "options": options,
        "options_in_media": options is None,
        "type": qtype,
        "topic": q.get("topic"),
        "tag": q.get("tag"),
        "answer": q.get("answer"),
        "answer_source": q.get("answer_source"),
        "explanation": q.get("explanation"),
        "media": media,
        "formulas": q.get("formulas") or [],
        "material_ids": material_ids,
        "provenance": prov,
        "flags": sorted(flags),
    }


def normalize_materials(section: dict, stats: collections.Counter):
    """材料 id 统一为 m{起}_{止}，字段归一；并回填小题引用的悬空标记。"""
    materials = section.get("materials") or []
    questions = section.get("questions", [])

    def mark_dangling(q: dict) -> None:
        if q.get("material_ids"):
            q["flags"] = sorted(set(q.get("flags") or []) | {"material_ref_dangling"})
            stats["material_ref_dangling"] += 1

    if not materials:
        for q in questions:
            mark_dangling(q)
        return None

    by_id = {}
    remap = {}
    for mat in materials:
        old_id = mat.get("id") or f"mat{len(by_id) + 1}"
        nums = [q.get("number") for q in questions
                if old_id in (q.get("material_ids") or [])]
        nums = [n for n in nums if isinstance(n, int)]
        new_id = f"m{min(nums)}_{max(nums)}" if nums else str(old_id)
        remap[old_id] = new_id
        note = mat.get("note") or mat.get("chart_data_note") or mat.get("material_note") or ""
        by_id[new_id] = {
            "id": new_id,
            "title": mat.get("title", ""),
            "kind": mat.get("kind") or mat.get("type") or ("chart_table" if mat.get("table_data") else "text"),
            "number_range": [min(nums), max(nums)] if nums else None,
            "content": mat.get("content", ""),
            "table_data": mat.get("table_data"),
            "media": [
                ({**x, "path": norm_media_path(str(x.get("path", "")))} if isinstance(x, dict)
                 else {"path": norm_media_path(str(x)), "kind": "chart", "label": ""})
                for x in (mat.get("media") or [])
            ],
            "note": note,
        }
        stats["material_normalized"] += 1

    for q in questions:
        q["material_ids"] = [remap.get(mid, mid) for mid in (q.get("material_ids") or [])]
        if any(mid not in by_id for mid in q["material_ids"]):
            mark_dangling(q)
    return list(by_id.values())


def mark_intra_paper_duplicates(sections: list, stats: collections.Counter) -> int:
    """同一份卷内题干+选项+组合项+媒体完全相同的题，打 duplicate_in_paper 标记。"""
    groups: dict = {}
    for s in sections:
        for q in s["questions"]:
            key = json.dumps([str(q.get("stem", ""))[:200], q.get("options"), q.get("items"),
                              sorted(m["path"] for m in q.get("media") or [])],
                             ensure_ascii=False, sort_keys=True)
            groups.setdefault(key, []).append(q)
    dup_groups = [g for g in groups.values() if len(g) > 1]
    for g in dup_groups:
        for q in g:
            if "duplicate_in_paper" not in q["flags"]:
                q["flags"] = sorted(set(q["flags"]) | {"duplicate_in_paper"})
    if dup_groups:
        stats["duplicate_groups"] += len(dup_groups)
    return len(dup_groups)


def normalize_paper(path: Path, stats: collections.Counter) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema_version") == 2:
        stats["skipped_v2"] += 1
        return doc
    base_dir = path.parent.parent  # {YEAR}/xingce/
    sections_out = []
    modules = []
    for s in doc.get("sections", []):
        name = s.get("name", "")
        questions = [normalize_question(q, name, base_dir, stats) for q in s.get("questions", [])]
        materials = normalize_materials({**s, "questions": questions}, stats)
        nums = [q["number"] for q in questions if isinstance(q.get("number"), int)]
        sections_out.append({
            "name": name,
            "question_count": s.get("question_count", len(questions)),
            "materials": materials or [],
            "questions": questions,
        })
        if nums:
            modules.append({"name": name, "number_range": [min(nums), max(nums)],
                            "question_count": len(questions)})
    total = sum(m["question_count"] for m in modules)
    mark_intra_paper_duplicates(sections_out, stats)
    return {
        "schema_version": 2,
        "exam_year": doc.get("exam_year"),
        "exam_name": doc.get("exam_name", ""),
        "paper_type": doc.get("paper_type", ""),
        "total_questions": doc.get("total_questions", total),
        "actual_question_count": doc.get("actual_question_count", total),
        "modules": modules,
        "notes": doc.get("notes", ""),
        "media_index": doc.get("media_index", "media/media_index.json"),
        "sections": sections_out,
    }


def normalize_media_index(path: Path, stats: collections.Counter):
    if not path.exists():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    if "conventions" not in doc and all("path" in x for x in doc.get("pages", [])[:1] or [{}]):
        stats["media_index_skipped"] += 1
        return
    for key in ("pages", "figures"):
        for item in doc.get(key, []):
            if "file" in item:
                item["path"] = norm_media_path(str(item.pop("file")))
            elif item.get("path"):
                item["path"] = norm_media_path(str(item["path"]))
        stats[f"media_index_{key}"] = len(doc.get(key, []))
    doc.pop("conventions", None)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def question_key(q: dict) -> str:
    """去重键：题干 + 选项 + 组合项 + 媒体路径。

    只用题干会误合图形推理等「题干为套话、差异全在选项与图片」的题目。
    """
    payload = json.dumps(
        [str(q.get("stem", ""))[:200],
         q.get("options"),
         q.get("items"),
         sorted(m.get("path", "") for m in (q.get("media") or []))],
        ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def rebuild_merged(year_dir: Path, stats: collections.Counter) -> int:
    """从三套 v2 卷重建 all_merged.json：按题干去重的跨卷分析池。"""
    papers_dir = year_dir / "xingce" / "papers"
    pool: dict = {}
    order = []
    for paper in PAPERS:
        f = papers_dir / f"{paper}.json"
        if not f.exists():
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        if doc.get("schema_version") != 2:
            stats["merged_skipped_not_v2"] += 1
            continue
        for s in doc["sections"]:
            for q in s["questions"]:
                key = question_key(q)
                entry = pool.get(key)
                if entry is None:
                    entry = dict(q)
                    entry.pop("number", None)
                    entry["occurrences"] = []
                    pool[key] = entry
                    order.append(key)
                entry["occurrences"].append({
                    "paper": doc.get("paper_type"),
                    "number": q.get("number"),
                })
    items = [pool[k] for k in order]
    out = {
        "schema_version": 2,
        "exam_year": json.loads((papers_dir / "shengji.json").read_text(encoding="utf-8")).get("exam_year"),
        "purpose": "跨卷去重分析池，不作为「唯一真题」使用",
        "total_unique_questions": len(items),
        "questions": items,
    }
    (papers_dir / "all_merged.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stats["merged_unique"] = len(items)
    return len(items)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--year", help="只处理指定年份")
    ap.add_argument("--merged", action="store_true", help="同时重建 all_merged.json 分析池")
    args = ap.parse_args()

    stats: collections.Counter = collections.Counter()
    targets = []
    year_dirs = []
    for year_dir in sorted(DATA.glob("20*")):
        if args.year and year_dir.name != args.year:
            continue
        for paper in PAPERS:
            f = year_dir / "xingce" / "papers" / f"{paper}.json"
            if f.exists():
                targets.append(f)
                if year_dir not in year_dirs:
                    year_dirs.append(year_dir)

    changed = 0
    flag_stats: collections.Counter = collections.Counter()
    type_stats: collections.Counter = collections.Counter()
    for f in targets:
        doc = normalize_paper(f, stats)
        rel = f.relative_to(REPO)
        for s in doc["sections"]:
            for q in s["questions"]:
                for fl in q["flags"]:
                    flag_stats[fl] += 1
                type_stats[q["type"] or "(未判定)"] += 1
        if args.dry_run:
            flagged = sum(1 for s in doc["sections"] for q in s["questions"] if q["flags"])
            print(f"[dry] {rel}: {doc['actual_question_count']}题 "
                  f"modules={len(doc['modules'])} 带flag题数={flagged}")
        else:
            f.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"迁移 {rel}")
        changed += 1
        if not args.dry_run:
            normalize_media_index(f.parent.parent / "media" / "media_index.json", stats)

    if args.merged and not args.dry_run:
        for yd in year_dirs:
            n = rebuild_merged(yd, stats)
            print(f"重建 {yd.name}/xingce/papers/all_merged.json：{n} 道去重题")

    print("\n=== 归一后 type 分布 ===")
    for t, c in type_stats.most_common():
        print(f"  {t}: {c}")
    print("\n=== 数据质量 flag 分布 ===")
    for fl, c in flag_stats.most_common():
        print(f"  {fl}: {c}")
    print("\n=== 迁移汇总 ===")
    for k in sorted(stats):
        print(f"  {k}: {stats[k]}")
    print(f"\n处理 {changed} 个卷文件；{'仅预览，未写入' if args.dry_run else '已写入（可用 git diff 复核 / git checkout 回滚）'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
