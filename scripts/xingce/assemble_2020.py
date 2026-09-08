#!/usr/bin/env python3
"""2020 国考行测两卷组装脚本（省级/市地级，无行政执法卷）。

输入（2020/xingce/_extract/）：
  主卷 5 模块：changshi.json, yuyan.json, shuliang.json, panduan.json, ziliao.json（市地级底版）
  省级差异：shengji_diff_{changshi,yuyan_a,yuyan_b,shuliang,panduan_a,panduan_b,ziliao}.json

组装规则：
  市地卷（130）= 主卷直接，role=main（模块范围 常1-20/言21-60/数61-70/判71-110/资111-130）
  省级卷（135）= 各模块：共享题按 offset 法映射到省级题号（offset=省级start-市地start），
                         独有题按差异册顺序填剩余空位
                         模块范围 常1-20/言21-60/数61-75/判76-115/资116-135

用法：python3 scripts/xingce/assemble_2020.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "xingce-structured-data"
Y20 = DATA / "2020" / "xingce"
EX = Y20 / "_extract"

YEAR = 2020
EXAM_NAME = "2020年度国家公务员考试"

# 市地：常1-20/言21-60/数61-70/判71-110/资111-130（130题）
MODULES_SHIDI = [
    {"name": "常识判断", "count": 20, "start": 1},
    {"name": "言语理解与表达", "count": 40, "start": 21},
    {"name": "数量关系", "count": 10, "start": 61},
    {"name": "判断推理", "count": 40, "start": 71},
    {"name": "资料分析", "count": 20, "start": 111},
]
# 省级：常1-20/言21-60/数61-75/判76-115/资116-135（135题）
MODULES_SHENGJI = [
    {"name": "常识判断", "count": 20, "start": 1},
    {"name": "言语理解与表达", "count": 40, "start": 21},
    {"name": "数量关系", "count": 15, "start": 61},
    {"name": "判断推理", "count": 40, "start": 76},
    {"name": "资料分析", "count": 20, "start": 116},
]

# 省级各模块：市地共享题号（省级号 = 市地号 + offset）
# 差异册注释确认：
#   常识：市地1、2、6~7、9~11、17~19未在省级出现 → 共享10题
#   言语：市地21、25、27~30、33、36、38、40、45、47、52、54~58未在省级出现 → 共享22题
#   数量：省级15道=市地10道全共享+5道独有 → 共享10题
#   判断：市地71、74、76~77、106~110未在省级出现 → 共享31题
#   资料：省级111~115、126~130未在市地出现 → 共享市地111~120（10题）
SHENGJI_SHARED = {
    "常识判断": [3, 4, 5, 8, 12, 13, 14, 15, 16, 20],
    "言语理解与表达": [
        22, 23, 24, 26, 31, 32, 34, 35, 37, 39,
        41, 42, 43, 44, 46, 48, 49, 50, 51, 53,
        59, 60,
    ],
    "数量关系": [61, 62, 63, 64, 65, 66, 67, 68, 69, 70],
    "判断推理": [
        72, 73, 75, 78, 79, 80, 81, 82, 83, 84,
        85, 86, 87, 88, 89, 90, 91, 92, 93, 94,
        95, 96, 97, 98, 99, 100, 101, 102, 103, 104,
        105,
    ],
    "资料分析": [111, 112, 113, 114, 115, 116, 117, 118, 119, 120],
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_main_questions():
    """主卷 5 模块 → {module_name: [question,...]}，保留文件内市地题号。"""
    out = {}
    for mod in MODULES_SHIDI:
        name = mod["name"]
        fname = {
            "常识判断": "changshi.json",
            "言语理解与表达": "yuyan.json",
            "数量关系": "shuliang.json",
            "判断推理": "panduan.json",
            "资料分析": "ziliao.json",
        }[name]
        data = load_json(EX / fname)
        out[name] = sorted(data["questions"], key=lambda q: q["number"])
    return out


def load_province_diffs():
    """省级差异 → {module_name: [q,...]}（按差异册顺序）。"""
    out = {}
    files = [
        ("常识判断", "shengji_diff_changshi.json"),
        ("言语理解与表达", "shengji_diff_yuyan_a.json"),
        ("言语理解与表达", "shengji_diff_yuyan_b.json"),
        ("数量关系", "shengji_diff_shuliang.json"),
        ("判断推理", "shengji_diff_panduan_a.json"),
        ("判断推理", "shengji_diff_panduan_b.json"),
        ("资料分析", "shengji_diff_ziliao.json"),
    ]
    for mod, fname in files:
        data = load_json(EX / fname)
        out.setdefault(mod, []).extend(data["questions"])
    return out


def load_material_pool():
    """主卷+省级差异的顶层 materials（dict id→content）合并为材料池。"""
    pool = {}
    for fname in ("changshi.json", "yuyan.json", "shuliang.json", "panduan.json", "ziliao.json"):
        data = load_json(EX / fname)
        mats = data.get("materials") or {}
        if isinstance(mats, dict):
            pool.update(mats)
    for fname in ("shengji_diff_yuyan_b.json", "shengji_diff_ziliao.json"):
        data = load_json(EX / fname)
        mats = data.get("materials") or {}
        if isinstance(mats, dict):
            pool.update(mats)
    return pool


def build_paper(questions, modules, paper_type, total, material_pool, notes_extra=None):
    sections = []
    for mod in modules:
        name = mod["name"]
        start = mod["start"]
        qs = sorted(questions[name], key=lambda q: q["number"])
        expect = list(range(start, start + mod["count"]))
        got = [q["number"] for q in qs]
        if got != expect:
            raise ValueError(f"{paper_type} {name} 题号不连续: got={got} expect={expect}")
        for q in qs:
            q["section"] = name
        # 收集本模块被引用的材料
        mats = []
        seen = set()
        for q in qs:
            for mid in q.get("material_ids") or []:
                if mid in seen or mid not in material_pool:
                    continue
                seen.add(mid)
                content = material_pool[mid]
                # content 可能是 dict（含 title/text）或 str
                if isinstance(content, dict):
                    text_content = content.get("text", "")
                    title = content.get("title", "")
                else:
                    text_content = str(content)
                    title = text_content.split("\n")[0][:40]
                mats.append({
                    "id": mid,
                    "title": title,
                    "kind": "text",
                    "number_range": [],
                    "content": text_content,
                    "table_data": None,
                    "media": [],
                    "note": "",
                })
        sections.append({
            "name": name,
            "number_range": [start, start + mod["count"] - 1],
            "question_count": mod["count"],
            "materials": mats,
            "questions": qs,
        })
    return {
        "schema_version": 2,
        "exam_year": YEAR,
        "exam_name": EXAM_NAME,
        "paper_type": paper_type,
        "total_questions": total,
        "actual_question_count": total,
        "modules": [
            {"name": m["name"], "number_range": [m["start"], m["start"] + m["count"] - 1], "question_count": m["count"]}
            for m in modules
        ],
        "notes": notes_extra or "2020 组装：省级135=市地共享83+省级独有52；答案待接入。",
        "media_index": {},
        "sections": sections,
    }


def assemble():
    main_q = load_main_questions()
    prov_diffs = load_province_diffs()
    prov_count = {name: len(qs) for name, qs in prov_diffs.items()}
    print(f"省级差异题量: {prov_count}")

    # ---------- 市地卷 ----------
    shidi = {}
    for mod in MODULES_SHIDI:
        name = mod["name"]
        qs = []
        for q in main_q[name]:
            qq = copy.deepcopy(q)
            qq["provenance"]["role"] = "main"
            qq["provenance"]["raw_note"] = "市地级主卷"
            qs.append(qq)
        shidi[name] = qs

    # ---------- 省级卷 ----------
    shengji = {}
    prov_start_of = {m["name"]: m["start"] for m in MODULES_SHENGJI}
    shidi_start_of = {m["name"]: m["start"] for m in MODULES_SHIDI}
    for mod in MODULES_SHENGJI:
        name = mod["name"]
        shared_nums = SHENGJI_SHARED[name]
        offset = prov_start_of[name] - shidi_start_of[name]
        shared_by_num = {q["number"]: q for q in main_q[name]}
        prov_start = mod["start"]
        target_map = {}
        for n in shared_nums:
            if n not in shared_by_num:
                raise ValueError(f"省级{name}: 找不到市地共享题 {n}")
            q = copy.deepcopy(shared_by_num[n])
            new_n = n + offset
            q["number"] = new_n
            q["provenance"]["role"] = "shared"
            q["provenance"]["from_paper"] = "shidi"
            q["provenance"]["from_number"] = n
            q["provenance"]["raw_note"] = "省级与市地共享"
            target_map[new_n] = q
        diffs = prov_diffs[name]
        free = [n for n in range(prov_start, prov_start + mod["count"]) if n not in target_map]
        if len(free) != len(diffs):
            raise ValueError(f"省级{name}: 空位 {len(free)} != 独有题 {len(diffs)} (free={free})")
        for n, q in zip(free, diffs):
            qq = copy.deepcopy(q)
            qq["number"] = n
            qq["provenance"]["role"] = "province_only"
            qq["provenance"]["from_paper"] = "shengji"
            qq["provenance"]["from_number"] = n
            qq["provenance"]["raw_note"] = "省级独有"
            target_map[n] = qq
        shengji[name] = [target_map[n] for n in range(prov_start, prov_start + mod["count"])]
        print(f"  省级{name}: 共享{len(shared_nums)} + 独有{len(diffs)} = {mod['count']}")

    # 落盘
    papers_dir = Y20 / "papers"
    papers_dir.mkdir(exist_ok=True)
    material_pool = load_material_pool()
    papers = {
        "shengji": build_paper(shengji, MODULES_SHENGJI, "省级", 135, material_pool,
                                notes_extra="2020 省级卷 135 题：市地共享83 + 省级独有52。"),
        "shidi": build_paper(shidi, MODULES_SHIDI, "市地级", 130, material_pool,
                              notes_extra="2020 市地级主卷 130 题。"),
    }
    for key, paper in papers.items():
        (papers_dir / f"{key}.json").write_text(
            json.dumps(paper, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  wrote {key}.json: {paper['actual_question_count']} 题")
    merged = {
        "schema_version": 2,
        "exam_year": YEAR,
        "exam_name": EXAM_NAME,
        "papers": {k: p["sections"] for k, p in papers.items()},
        "notes": "2020 两卷合并（shengji/shidi），无行政执法卷。",
    }
    (papers_dir / "all_merged.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  wrote all_merged.json")

    # diff_map.json
    diff_map = {
        "schema_version": 2,
        "exam_year": YEAR,
        "generated_by": "assemble_2020.py",
        "note": "省级卷共享题号=市地号+offset(判断/资料+5,其余+0)；2020无行政执法卷。",
        "mapping": {
            "shengji": {
                name: {
                    "shared_from_shidi": SHENGJI_SHARED[name],
                    "province_only_count": prov_count[name],
                } for name in [m["name"] for m in MODULES_SHENGJI]
            },
        },
    }
    (EX / "diff_map.json").write_text(
        json.dumps(diff_map, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  wrote diff_map.json")


if __name__ == "__main__":
    assemble()
