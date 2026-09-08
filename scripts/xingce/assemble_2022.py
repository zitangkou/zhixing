#!/usr/bin/env python3
"""2022 国考行测三卷组装脚本（省级/市地级/行政执法类）。

2022 特殊点：主卷源图为省级卷（135题，数量15/判断从76/资料从116），
与 2023 主卷=市地 相反。组装方向反向：
  省级卷（135）= 主卷直接
  市地卷（130）= 省级共享(offset映射) + 市地差异题按顺序填空位
  执法卷（130）= 省级共享 + 市地共享 + 执法独有，按顺序编号

输入（2022/xingce/_extract/）：
  主卷 5 模块：changshi.json, yuyan.json, shuliang.json, panduan.json, ziliao.json（省级底版）
  市地差异：shidi_diff_{changshi,yuyan,shuliang,panduan,ziliao}.json
  执法差异：xzzf_diff_a.json（常识+言语）, xzzf_diff_b.json（判断+资料）

用法：python3 scripts/xingce/assemble_2022.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "xingce-structured-data"
Y22 = DATA / "2022" / "xingce"
EX = Y22 / "_extract"

YEAR = 2022
EXAM_NAME = "2022年度国家公务员考试"

# 模块定义
# 省级（主卷）：常1-20/言21-60/数61-75/判76-115/资116-135（135题）
MODULES_SHENGJI = [
    {"name": "常识判断", "count": 20, "start": 1},
    {"name": "言语理解与表达", "count": 40, "start": 21},
    {"name": "数量关系", "count": 15, "start": 61},
    {"name": "判断推理", "count": 40, "start": 76},
    {"name": "资料分析", "count": 20, "start": 116},
]
# 市地：常1-20/言21-60/数61-70/判71-110/资111-130（130题）
MODULES_SHIDI = [
    {"name": "常识判断", "count": 20, "start": 1},
    {"name": "言语理解与表达", "count": 40, "start": 21},
    {"name": "数量关系", "count": 10, "start": 61},
    {"name": "判断推理", "count": 40, "start": 71},
    {"name": "资料分析", "count": 20, "start": 111},
]
MODULES_XZZF = MODULES_SHIDI  # 执法模块范围与市地相同

# 市地各模块：共享省级题号（市地号 = 省级号 + offset）
SHIDI_SHARED_FROM_SHENGJI = {
    "常识判断": [6, 7, 9, 11, 12, 13, 15, 17, 18, 19, 20],
    "言语理解与表达": [21, 22, 24, 25, 31, 32, 33, 34, 35, 37, 41, 42, 46, 47, 50],
    "数量关系": [63, 66, 67, 69, 70, 72],
    "判断推理": [77, 78, 79, 81, 82, 83, 84, 86, 87, 88, 90, 92, 95, 97, 99, 100, 101, 105, 106, 110, 112],
    "资料分析": [121, 122, 123, 124, 125, 131, 132, 133, 134, 135],
}

# 执法各模块：省级共享题号 + 市地共享差异标签 + 执法独有
XZZF_SHARED = {
    "常识判断": {
        "shengji": [2, 3, 8, 11, 12, 17, 19, 20],
        "shidi_labels": ["②", "④", "⑥", "⑦", "⑨"],
    },
    "言语理解与表达": {
        "shengji": [21, 24, 26, 27, 29, 32, 38, 39, 42, 43, 44, 47],
        "shidi_labels": ["⑩", "⑪", "⑫", "⑬", "⑭", "⑮", "⑰", "⑳", "㉑", "㉒", "㉓", "㉔", "㉚", "㉛", "㉜", "㉝", "㉞"],
        "note": "执法言语40=省级12+市地17+独有11。原文OCR'㉓~㉔'疑为'㉛~㉞'(31~34)，按题量40推算取17题共享。",
    },
    "数量关系": {
        "shengji": [65, 68, 70, 72, 73, 75],
        "shidi_labels": ["㉟", "㊱", "㊲", "㊳"],
        "note": "执法数量10题全部为省级+市地共享，无执法独有题。市地共享标签原文OCR显示'㉕~㉘'，按市地数量差异仅4题(㉟㊱㊲㊳)推断。",
    },
    "判断推理": {
        "shengji": [76, 82, 84, 85, 86, 90, 93, 94, 97, 98, 100, 102, 104, 105, 110, 113, 114],
        "shidi_labels": ["㊴", "㊵", "㊶", "㊷", "㊸", "㊹", "㊺", "㊼", "㊽", "㊾", "㊿", "53", "54", "55", "56", "57"],
        "note": "执法判断市地共享16题：排除㊻(类比)、51/52(独立逻辑)。原文OCR圈号残缺，按题量推算取16题，待核。",
    },
    "资料分析": {
        "shengji": [],
        "shidi_labels": ["58", "59", "60", "61", "62", "63", "64", "65", "66", "67"],
        "note": "执法资料20题 = 市地资料差异10题(58~67) + 执法独有10题，无省级共享。",
    },
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_main_questions():
    """主卷 5 模块 → {module_name: [question,...]}，保留文件内省级题号。"""
    out = {}
    for mod in MODULES_SHENGJI:
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


def load_shidi_diffs():
    """市地差异 → {module_name: [q,...]}（按差异册顺序）。"""
    out = {}
    files = [
        ("常识判断", "shidi_diff_changshi.json"),
        ("言语理解与表达", "shidi_diff_yuyan.json"),
        ("数量关系", "shidi_diff_shuliang.json"),
        ("判断推理", "shidi_diff_panduan.json"),
        ("资料分析", "shidi_diff_ziliao.json"),
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
    """主卷+市地差异+执法差异的顶层 materials 合并为材料池。"""
    pool = {}
    for fname in ("changshi.json", "yuyan.json", "shuliang.json", "panduan.json", "ziliao.json"):
        data = load_json(EX / fname)
        mats = data.get("materials") or {}
        if isinstance(mats, dict):
            pool.update(mats)
    for fname in ("shidi_diff_panduan.json", "shidi_diff_ziliao.json", "xzzf_diff_b.json"):
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
        mats = []
        seen = set()
        for q in qs:
            for mid in q.get("material_ids") or []:
                if mid in seen or mid not in material_pool:
                    continue
                seen.add(mid)
                content = material_pool[mid]
                cstr = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                mats.append({
                    "id": mid,
                    "title": (content.get("title", "") if isinstance(content, dict) else cstr.split("\n")[0][:60]),
                    "kind": "text",
                    "number_range": [],
                    "content": cstr,
                    "table_data": None,
                    "media": [],
                    "note": content.get("note", "") if isinstance(content, dict) else "",
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
        "notes": notes_extra or "2022 组装：主卷=省级135；市地130=省级共享+市地差异；执法130=省级共享+市地共享+执法独有。答案待接入。",
        "media_index": {},
        "sections": sections,
    }


def assemble():
    main_q = load_main_questions()
    shidi_diffs = load_shidi_diffs()
    xzzf_diffs = load_xzzf_diffs()
    shidi_diff_count = {name: len(qs) for name, qs in shidi_diffs.items()}

    # ---------- 省级卷 = 主卷直接 ----------
    shengji = {}
    for mod in MODULES_SHENGJI:
        name = mod["name"]
        qs = []
        for q in main_q[name]:
            qq = copy.deepcopy(q)
            qq["provenance"]["role"] = "main"
            qq["provenance"]["raw_note"] = "省级主卷"
            qs.append(qq)
        shengji[name] = qs

    # ---------- 市地卷 = 省级共享(offset) + 市地差异填空位 ----------
    shidi = {}
    shengji_start_of = {m["name"]: m["start"] for m in MODULES_SHENGJI}
    shidi_start_of = {m["name"]: m["start"] for m in MODULES_SHIDI}
    for mod in MODULES_SHIDI:
        name = mod["name"]
        shared_nums = SHIDI_SHARED_FROM_SHENGJI[name]
        offset = shidi_start_of[name] - shengji_start_of[name]
        shared_by_num = {q["number"]: q for q in main_q[name]}
        shidi_start = mod["start"]
        shidi_end = shidi_start + mod["count"] - 1
        target_map = {}
        overflow = []  # 越界共享题（如省级数量72→超出市地61-70）
        for n in shared_nums:
            if n not in shared_by_num:
                raise ValueError(f"市地{name}: 找不到省级题 {n}")
            q = copy.deepcopy(shared_by_num[n])
            new_n = n + offset
            q["provenance"]["role"] = "shared"
            q["provenance"]["from_paper"] = "shengji"
            q["provenance"]["from_number"] = n
            q["provenance"]["raw_note"] = "市地与省级共享"
            if shidi_start <= new_n <= shidi_end:
                q["number"] = new_n
                target_map[new_n] = q
            else:
                q["number"] = None  # 待分配
                overflow.append(q)
        diffs = shidi_diffs[name]
        free = [n for n in range(shidi_start, shidi_end + 1) if n not in target_map]
        # 越界共享题先填，再填差异题
        fillers = overflow + diffs
        if len(free) != len(fillers):
            raise ValueError(f"市地{name}: 空位 {len(free)} != 待填题 {len(fillers)} (free={free}, overflow={len(overflow)}, diffs={len(diffs)})")
        for n, q in zip(free, fillers):
            qq = copy.deepcopy(q)
            qq["number"] = n
            if qq["provenance"]["role"] == "shared":
                pass  # 越界共享题，role已设
            else:
                qq["provenance"]["role"] = "diff_book"
                qq["provenance"]["from_paper"] = "shidi"
                qq["provenance"]["from_number"] = n
                qq["provenance"]["raw_note"] = "市地独有"
            target_map[n] = qq
        shidi[name] = [target_map[n] for n in range(shidi_start, shidi_end + 1)]

    # ---------- 执法卷 = 省级共享 + 市地共享 + 执法独有 ----------
    xzzf = {}
    for mod in MODULES_XZZF:
        name = mod["name"]
        cfg = XZZF_SHARED[name]
        shared_by_num = {q["number"]: q for q in main_q[name]}
        shidi_by_label = {q["diff_label"]: q for q in shidi_diffs[name]}
        seq = []
        # 省级共享
        for n in cfg["shengji"]:
            if n not in shared_by_num:
                raise ValueError(f"执法{name}: 找不到省级题 {n}")
            q = copy.deepcopy(shared_by_num[n])
            q["provenance"]["role"] = "shared"
            q["provenance"]["from_paper"] = "shengji"
            q["provenance"]["from_number"] = n
            q["provenance"]["raw_note"] = "执法与省级共享"
            seq.append(q)
        # 市地共享
        for lab in cfg["shidi_labels"]:
            if lab not in shidi_by_label:
                raise ValueError(f"执法{name}: 找不到市地差异标签 {lab}")
            q = copy.deepcopy(shidi_by_label[lab])
            q["provenance"]["role"] = "shared_with_shidi"
            q["provenance"]["from_paper"] = "shidi"
            q["provenance"]["from_number"] = None
            q["provenance"]["diff_label"] = lab
            q["provenance"]["raw_note"] = "执法与市地共享"
            seq.append(q)
        # 执法独有
        for q in xzzf_diffs.get(name, []):
            qq = copy.deepcopy(q)
            qq["provenance"]["role"] = "diff_book"
            qq["provenance"]["from_paper"] = "xingzhengzhifa"
            qq["provenance"]["from_number"] = None
            qq["provenance"]["raw_note"] = "执法独有"
            seq.append(qq)
        if len(seq) != mod["count"]:
            raise ValueError(f"执法{name}: 题量 {len(seq)} != {mod['count']} (省级{len(cfg['shengji'])}+市地{len(cfg['shidi_labels'])}+独有{len(xzzf_diffs.get(name, []))})")
        start = mod["start"]
        for i, q in enumerate(seq):
            q["number"] = start + i
        xzzf[name] = seq

    # 落盘
    papers_dir = Y22 / "papers"
    papers_dir.mkdir(exist_ok=True)
    material_pool = load_material_pool()
    papers = {
        "shengji": build_paper(shengji, MODULES_SHENGJI, "省级", 135, material_pool,
                                notes_extra="2022 省级卷 135 题（主卷直接）。常识第4题扫描件缺失，以占位题记录。"),
        "shidi": build_paper(shidi, MODULES_SHIDI, "市地级", 130, material_pool,
                              notes_extra="2022 市地级卷 130 题：省级共享63题 + 市地差异67题。"),
        "xingzhengzhifa": build_paper(xzzf, MODULES_XZZF, "行政执法类", 130, material_pool,
                                       notes_extra="2022 执法卷 130 题：省级共享43题 + 市地共享47题 + 执法独有35题 + 数量无独有。执法判断市地共享16题按题量推断，待核。"),
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
        "notes": "2022 三卷合并（shengji/shidi/xingzhengzhifa）。",
    }
    (papers_dir / "all_merged.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  wrote all_merged.json")

    # diff_map.json
    diff_map = {
        "schema_version": 2,
        "exam_year": YEAR,
        "generated_by": "assemble_2022.py",
        "note": "2022主卷=省级。市地卷共享题号=省级号+offset(判断/资料-5,其余+0)；执法卷按 省级→市地→独有 顺序连续编号。",
        "mapping": {
            "shidi": {
                name: {
                    "shared_from_shengji": SHIDI_SHARED_FROM_SHENGJI[name],
                    "shidi_only_count": shidi_diff_count[name],
                } for name in [m["name"] for m in MODULES_SHIDI]
            },
            "xingzhengzhifa": {
                name: {
                    "shared_from_shengji": cfg["shengji"],
                    "shared_from_shidi_labels": cfg["shidi_labels"],
                    "xzzf_only_count": len(xzzf_diffs.get(name, [])),
                    **({"note": cfg["note"]} if cfg.get("note") else {}),
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
