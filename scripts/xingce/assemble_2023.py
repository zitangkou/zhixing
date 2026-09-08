#!/usr/bin/env python3
"""2023 国考行测三卷组装脚本（省级/市地级/行政执法类）。

输入（2023/xingce/_extract/）：
  主卷 5 模块：changshi.json, yuyan.json, shuliang.json, panduan.json, ziliao.json（市地级底版）
  省级差异：shengji_diff_{changshi,yuyan_a,yuyan_b,shuliang,panduan_a,panduan_b,ziliao}.json
  执法差异：xzzf_diff_a.json（常识+言语）, xzzf_diff_b.json（数量+判断）

组装规则：
  市地卷（130）= 主卷直接，role=main（模块范围 常1-20/言21-60/数61-70/判71-110/资111-130）
  省级卷（135）= 各模块：共享题按 offset 法映射到省级题号（offset=省级start-市地start），
                         独有题按差异册顺序填剩余空位
                         模块范围 常1-20/言21-60/数61-75/判76-115/资116-135
  执法卷（130）= 各模块：市地共享 + 省级共享 + 执法独有，按 市地→省级→独有 顺序编号

用法：python3 scripts/xingce/assemble_2023.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "xingce-structured-data"
Y23 = DATA / "2023" / "xingce"
EX = Y23 / "_extract"

YEAR = 2023
EXAM_NAME = "2023年度国家公务员考试"

# 各卷模块定义：name + 各卷题量/起始号
# 市地：常1-20/言21-60/数61-70/判71-110/资111-130（130题）
# 省级：常1-20/言21-60/数61-75/判76-115/资116-135（135题）
# 执法：常1-20/言21-60/数61-70/判71-110/资111-130（130题）
MODULES_SHIDI = [
    {"name": "常识判断", "count": 20, "start": 1},
    {"name": "言语理解与表达", "count": 40, "start": 21},
    {"name": "数量关系", "count": 10, "start": 61},
    {"name": "判断推理", "count": 40, "start": 71},
    {"name": "资料分析", "count": 20, "start": 111},
]
MODULES_SHENGJI = [
    {"name": "常识判断", "count": 20, "start": 1},
    {"name": "言语理解与表达", "count": 40, "start": 21},
    {"name": "数量关系", "count": 15, "start": 61},
    {"name": "判断推理", "count": 40, "start": 76},
    {"name": "资料分析", "count": 20, "start": 116},
]
MODULES_XZZF = MODULES_SHIDI  # 执法模块范围与市地相同（数量10题）

# 省级各模块：市地共享题号（省级号 = 市地号 + offset）
SHENGJI_SHARED = {
    "常识判断": [1, 2, 4, 13, 14, 17, 20],
    "言语理解与表达": [21, 25, 26, 27, 31, 35, 41, 42, 43, 45, 48, 50, 58],
    "数量关系": [61, 62, 64, 67, 68],
    "判断推理": [71, 72, 74, 76, 79, 82, 84, 85, 87, 89, 93, 94, 95, 96, 97, 100, 102, 104, 105],
    "资料分析": [116, 117, 118, 119, 120],
}

# 执法各模块共享：市地题号 + 省级差异标签
XZZF_SHARED = {
    "常识判断": {
        "shidi": [2, 3, 7, 8, 9, 10, 11, 12, 15, 16, 17, 18],
        "shengji_labels": ["①", "②", "④", "⑤", "⑩"],
    },
    "言语理解与表达": {
        "shidi": [23, 25, 27, 29, 30, 32, 34, 36, 37, 39, 40, 43, 44, 46, 49, 51, 53, 54, 55, 57],
        "shengji_labels": ["⑭", "⑮", "㉑", "㉓", "㉘", "㉚"],
    },
    "数量关系": {
        "shidi": [65],
        "shengji_labels": ["41", "42", "43", "44"],  # 差异册注OCR残缺（显示④④④④），按省级数量独有顺序取前4，待确认
        "shengji_note": "省级共享4题题号未确认（原件OCR显示④④④④），本脚本按省级数量独有题顺序取41-44，已记入CONFIRM_LOG待核",
    },
    "判断推理": {
        "shidi": [71, 75, 77, 78, 80, 81, 83, 88, 90, 91, 92, 95, 97, 98, 99, 101, 106, 107, 108, 109, 110],
        "shengji_labels": ["⑤①", "⑤⑦", "⑥④", "⑥⑤", "⑥⑥"],
    },
    "资料分析": {
        "shidi": [111, 112, 113, 114, 115, 121, 122, 123, 124, 125],
        "shengji_labels": ["⑦②", "⑦③", "⑦④", "⑦⑤", "⑦⑥", "⑦⑦", "⑦⑧", "⑦⑨", "⑧⓪", "⑧①"],
        "shengji_note": "执法资料 = 市地111-115+121-125 + 省级宽带组(⑦②-⑦⑥)+集成电路组(⑦⑦-⑧①)，无独有题",
    },
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


def load_xzzf_diffs():
    out = {}
    for fname in ("xzzf_diff_a.json", "xzzf_diff_b.json"):
        data = load_json(EX / fname)
        for q in data["questions"]:
            out.setdefault(q["module"], []).append(q)
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
            raise ValueError(f"{paper_type} {name} 题号不连续: {got}")
        # 每题补齐 section 字段
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
                mats.append({
                    "id": mid,
                    "title": content.split("\n")[0][:40] if isinstance(content, str) else "",
                    "kind": "text",
                    "number_range": [],
                    "content": content,
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
        "notes": notes_extra or "2023 组装：省级135=市地共享49+省级独有86；执法130=市地共享+省级共享+执法独有；答案待接入。",
        "media_index": {},
        "sections": sections,
    }


def assemble():
    main_q = load_main_questions()
    prov_diffs = load_province_diffs()
    xzzf_diffs = load_xzzf_diffs()
    prov_count = {name: len(qs) for name, qs in prov_diffs.items()}

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
            raise ValueError(f"省级{name}: 空位 {len(free)} != 独有题 {len(diffs)}")
        for n, q in zip(free, diffs):
            qq = copy.deepcopy(q)
            qq["number"] = n
            qq["provenance"]["role"] = "province_only"
            qq["provenance"]["from_paper"] = "shengji"
            qq["provenance"]["from_number"] = n
            qq["provenance"]["raw_note"] = "省级独有"
            target_map[n] = qq
        shengji[name] = [target_map[n] for n in range(prov_start, prov_start + mod["count"])]

    # ---------- 执法卷 ----------
    xzzf = {}
    for mod in MODULES_XZZF:
        name = mod["name"]
        cfg = XZZF_SHARED[name]
        shared_by_num = {q["number"]: q for q in main_q[name]}
        prov_by_label = {q["diff_label"]: q for q in prov_diffs[name]}
        seq = []
        for n in cfg["shidi"]:
            if n not in shared_by_num:
                raise ValueError(f"执法{name}: 找不到市地题 {n}")
            q = copy.deepcopy(shared_by_num[n])
            q["provenance"]["role"] = "shared_with_shidi"
            q["provenance"]["from_paper"] = "shidi"
            q["provenance"]["from_number"] = n
            q["provenance"]["raw_note"] = "执法与市地共享"
            seq.append(q)
        for lab in cfg["shengji_labels"]:
            if lab not in prov_by_label:
                raise ValueError(f"执法{name}: 找不到省级差异标签 {lab}")
            q = copy.deepcopy(prov_by_label[lab])
            q["provenance"]["role"] = "shared"
            q["provenance"]["from_paper"] = "shengji"
            q["provenance"]["from_number"] = None
            q["provenance"]["diff_label"] = lab
            q["provenance"]["raw_note"] = "执法与省级共享"
            seq.append(q)
        for q in xzzf_diffs.get(name, []):
            qq = copy.deepcopy(q)
            qq["provenance"]["role"] = "diff_book"
            qq["provenance"]["from_paper"] = "xingzhengzhifa"
            qq["provenance"]["from_number"] = None
            qq["provenance"]["raw_note"] = "执法独有"
            seq.append(qq)
        if len(seq) != mod["count"]:
            raise ValueError(f"执法{name}: 题量 {len(seq)} != {mod['count']}")
        start = mod["start"]
        for i, q in enumerate(seq):
            q["number"] = start + i
        xzzf[name] = seq

    # 落盘
    papers_dir = Y23 / "papers"
    papers_dir.mkdir(exist_ok=True)
    material_pool = load_material_pool()
    papers = {
        "shengji": build_paper(shengji, MODULES_SHENGJI, "省级", 135, material_pool, notes_extra="2023 省级卷 135 题：市地共享49 + 省级独有86。"),
        "shidi": build_paper(shidi, MODULES_SHIDI, "市地级", 130, material_pool, notes_extra="2023 市地级主卷 130 题（无独立政治理论模块）。"),
        "xingzhengzhifa": build_paper(xzzf, MODULES_XZZF, "行政执法类", 130, material_pool, notes_extra="2023 执法卷 130 题：市地共享 + 省级共享 + 执法独有；执法数量省级共享4题按推断取（待核）。"),
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
        "notes": "2023 三卷合并（shengji/shidi/xingzhengzhifa）。",
    }
    (papers_dir / "all_merged.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  wrote all_merged.json")

    # diff_map.json：机器可读差异题映射表（CONFIRM_LOG Q3 交付物）
    diff_map = {
        "schema_version": 2,
        "exam_year": YEAR,
        "generated_by": "assemble_2023.py",
        "note": "省级卷共享题号=市地号+offset(判断/资料+5,其余+0)；执法卷按 市地→省级→独有 顺序连续编号。",
        "mapping": {
            "shengji": {
                name: {
                    "shared_from_shidi": SHENGJI_SHARED[name],
                    "province_only_count": prov_count[name],
                } for name in [m["name"] for m in MODULES_SHENGJI]
            },
            "xingzhengzhifa": {
                name: {
                    "shared_from_shidi": cfg["shidi"],
                    "shared_from_shengji_labels": cfg["shengji_labels"],
                    "diff_book_count": len(xzzf_diffs.get(name, [])),
                    **({"note": cfg["shengji_note"]} if cfg.get("shengji_note") else {}),
                } for name, cfg in XZZF_SHARED.items()
            },
        },
    }
    (EX / "diff_map.json").write_text(
        json.dumps(diff_map, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  wrote diff_map.json")


if __name__ == "__main__":
    assemble()
