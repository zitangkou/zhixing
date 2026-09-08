#!/usr/bin/env python3
"""S1 真题规律统计：从 xingce-structured-data 6 年真题 JSON 现算三层统计。

用法：
    python3 scripts/xingce/compute_patterns.py
    python3 scripts/xingce/compute_patterns.py --json   # 输出 JSON 供程序消费

所有数字从 JSON 现算，不编造。仅依赖标准库 json/collections/re。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "xingce-structured-data"
YEARS = ["2020", "2021", "2022", "2023", "2024", "2025"]
PAPERS = ["shengji", "shidi", "xingzhengzhifa"]
PAPER_LABEL = {"shengji": "省级", "shidi": "市地", "xingzhengzhifa": "行政执法"}

# 标准六模块（2025 起）；2020-2024 无独立政治理论，政治并入常识
STANDARD_MODULES = ["政治理论", "常识判断", "言语理解与表达", "数量关系", "判断推理", "资料分析"]

# 设问关键词（按模块分组，用于 stem 末尾匹配）
QUESTION_PATTERNS = {
    "常识判断": [
        "下列说法正确的是", "下列说法错误的是", "下列说法不正确的是",
        "下列表述正确的是", "下列表述错误的是", "下列与……有关的是",
        "下列关于……的说法正确的是", "下列关于……说法错误的是",
        "下列对应正确的是", "下列对应错误的是",
        "下列排序正确的是", "下列排序错误的是",
        "下列诗句与……对应正确的是", "下列历史事件按时间先后排序正确的是",
        "下列关于……的表述正确的是", "下列关于……的表述错误的是",
        "下列说法符合……的是", "下列说法不符合……的是",
        "下列有关……的说法正确的是", "下列有关……的说法错误的是",
        "下列哪一情形", "下列哪一选项", "下列哪项",
        "下列做法正确的是", "下列做法错误的是",
        "下列关于……正确的是", "下列关于……错误的是",
    ],
    "政治理论": [
        "下列说法正确的是", "下列说法错误的是", "下列说法不正确的是",
        "下列表述正确的是", "下列表述错误的是",
        "下列理解正确的是", "下列理解错误的是",
        "下列认识正确的是", "下列认识错误的是",
        "下列观点正确的是", "下列观点错误的是",
        "下列说法与这一论述相符的有", "下列说法与材料相符的是",
        "下列对……理解正确的是", "下列对……理解错误的是",
        "下列关于……的说法正确的是", "下列关于……的说法错误的是",
        "下列哪一选项", "下列哪项",
    ],
    "言语理解与表达": [
        "意在说明", "意在强调", "主要介绍", "主要说明", "主要强调",
        "概括最准确的是", "概括最恰当的是", "对这段文字概括最准确的是",
        "这段文字意在说明", "这段文字意在强调", "这段文字主要介绍",
        "这段文字主要说明", "这段文字主要强调", "这段文字的主旨是",
        "这段文字旨在说明", "这段文字旨在强调",
        "填入画横线部分最恰当的一项是", "依次填入画横线部分最恰当的一项是",
        "填入横线处最恰当的是", "依次填入横线处最恰当的是",
        "最适合做这段文字标题的是", "最适合做本段文字标题的是",
        "将以上几个句子重新排列，语序正确的是", "将以上句子重新排列，语序正确的是",
        "接下来最可能讲的是", "接下来最可能讲述的是", "接下来最有可能讲的是",
        "可以推出", "由此可以推出", "根据这段文字可以推出",
        "下列说法与原文相符的是", "下列说法与原文不符的是",
        "下列说法正确的是", "下列说法错误的是",
        "作者接下来最可能讲述的是", "作者意在说明",
        "这段文字没有论及的是", "这段文字未提及的是",
        "对这段文字理解正确的是", "对这段文字理解错误的是",
    ],
    "数量关系": [
        "问该", "问共有", "问最多", "问最少", "问至少", "问至多",
        "问需要", "问应", "问这", "问其", "问甲", "问乙",
        "则该", "则共有", "则最多", "则最少", "则至少", "则至多",
        "的值为", "结果是", "等于",
        "下列哪项", "下列哪一",
    ],
    "判断推理": [
        "以下哪项如果为真，最能削弱", "以下哪项如果为真，最能质疑",
        "以下哪项如果为真，最能加强", "以下哪项如果为真，最能支持",
        "以下哪项如果为真，最能解释", "以下哪项如果为真，最不能削弱",
        "以下哪项如果为真，最不能加强", "以下哪项如果为真，最不能质疑",
        "由此可以推出", "由此不能推出", "可以推出", "不能推出",
        "以下哪项与上述论证方式最为相似", "以下哪项与题干推理形式相同",
        "以下哪项最能揭示上述论证的漏洞", "以下哪项最为恰当地指出了上述论证的漏洞",
        "以下哪项是上述论证所必须假设的", "以下哪项是上述论证的前提",
        "以下哪项如果为真，最能评价", "以下各项如果为真，都能削弱上述论证，除了",
        "以下各项都能加强上述论证，除了",
        "下列哪项如果为真，最能削弱", "下列哪项如果为真，最能加强",
        "下列哪项最能质疑", "下列哪项最能支持",
        "最适合做这段文字标题的是",
        "填入画横线部分最恰当的一项是",
    ],
    "资料分析": [
        "下列说法正确的是", "下列说法错误的是", "下列说法不正确的是",
        "能够从上述资料中推出的是", "不能从上述资料中推出的是",
        "以下说法正确的是", "以下说法错误的是",
        "下列指标中", "下列哪项", "下列哪一",
        "约为", "同比增长", "环比增长", "占比", "比重",
        "平均", "增速", "增长率", "增长量",
    ],
}

# 设错手法关键词（从 explanation 中匹配）
ERROR_TECHNIQUES = [
    "偷换概念", "偷换时态", "偷换逻辑", "偷换范围", "偷换主语",
    "以偏概全", "无中生有", "因果倒置", "强加因果", "因果混乱",
    "绝对化", "说法绝对", "过于绝对",
    "时态错误", "混淆时态", "已然未然",
    "范围扩大", "范围缩小", "扩大范围", "缩小范围",
    "张冠李戴", "答非所问", "曲解文意", "过度推断",
    "表述错误", "与原文不符", "与文意不符", "不符合原文",
    "正反混淆", "是非颠倒",
    "成分残缺", "搭配不当", "语序不当",
    "概念混淆", "信息错位",
]


def load_paper(year: str, paper: str) -> dict | None:
    f = DATA / year / "xingce" / "papers" / f"{paper}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def iter_questions(doc: dict):
    """yield (section_name, question_dict)"""
    for s in doc.get("sections", []):
        name = s.get("name", "")
        for q in s.get("questions", []):
            yield name, q


def normalize_stem(stem: str) -> str:
    """归一化题干用于跨卷去重匹配：去空白、去标点、统一全半角。"""
    s = re.sub(r"\s+", "", stem or "")
    s = re.sub(r"[，。、；：？！,.;:?!…—\-\"'\"'（）()【】\[\]《》<>]", "", s)
    return s


# ═══════════════════════════════════════════════════════════════
# 第一层：结构层（6 年全量题干）
# ═══════════════════════════════════════════════════════════════

def compute_structure() -> dict:
    result = {}

    # 1.1 年×卷题量矩阵
    matrix = {}
    total_by_year = {}
    for year in YEARS:
        matrix[year] = {}
        year_total = 0
        for paper in PAPERS:
            doc = load_paper(year, paper)
            if doc is None:
                matrix[year][paper] = None
                continue
            cnt = sum(len(s.get("questions", [])) for s in doc.get("sections", []))
            matrix[year][paper] = cnt
            year_total += cnt
        total_by_year[year] = year_total
    result["year_paper_matrix"] = matrix
    result["total_by_year"] = total_by_year
    result["grand_total"] = sum(total_by_year.values())

    # 1.2 各模块题量占比，按年趋势
    # 2020-2024 无政治理论模块；统一按"政治理论+常识判断"合并展示，同时单列
    module_by_year = {}
    for year in YEARS:
        module_by_year[year] = Counter()
        for paper in PAPERS:
            doc = load_paper(year, paper)
            if doc is None:
                continue
            for sec_name, q in iter_questions(doc):
                module_by_year[year][sec_name] += 1
    result["module_by_year"] = {y: dict(c) for y, c in module_by_year.items()}

    # 1.3 材料-题组关系
    material_stats = {"with_material_ids": 0, "total": 0, "per_material_dist": Counter(),
                      "by_module": defaultdict(Counter)}
    ziliao_material_groups = []  # 资料分析模块的材料组结构
    for year in YEARS:
        for paper in PAPERS:
            doc = load_paper(year, paper)
            if doc is None:
                continue
            for s in doc.get("sections", []):
                sec_name = s.get("name", "")
                materials_in_sec = {m.get("id") for m in (s.get("materials") or [])}
                # 按 material_id 分组统计题数
                mid_to_qs = defaultdict(list)
                for q in s.get("questions", []):
                    material_stats["total"] += 1
                    mids = q.get("material_ids") or []
                    if mids:
                        material_stats["with_material_ids"] += 1
                        material_stats["by_module"][sec_name]["with_material"] += 1
                    material_stats["by_module"][sec_name]["total"] += 1
                    for mid in mids:
                        mid_to_qs[mid].append(q.get("number"))
                for mid, qnums in mid_to_qs.items():
                    material_stats["per_material_dist"][len(qnums)] += 1
                if sec_name == "资料分析":
                    ziliao_material_groups.append({
                        "year": year, "paper": paper,
                        "material_count": len(mid_to_qs),
                        "groups": {mid: len(qs) for mid, qs in mid_to_qs.items()},
                    })
    result["material_stats"] = {
        "with_material_ids": material_stats["with_material_ids"],
        "total": material_stats["total"],
        "per_material_dist": dict(material_stats["per_material_dist"]),
        "by_module": {k: dict(v) for k, v in material_stats["by_module"].items()},
    }
    result["ziliao_material_groups"] = ziliao_material_groups

    # 1.4 跨年共享题分布（基于 provenance.role）
    role_by_year = {}
    for year in YEARS:
        role_by_year[year] = Counter()
        for paper in PAPERS:
            doc = load_paper(year, paper)
            if doc is None:
                continue
            for sec_name, q in iter_questions(doc):
                prov = q.get("provenance") or {}
                role = prov.get("role", "unknown")
                role_by_year[year][role] += 1
    result["role_by_year"] = {y: dict(c) for y, c in role_by_year.items()}

    # 2025 三卷间共享率（基于题干归一化匹配）
    docs_2025 = {}
    for paper in PAPERS:
        doc = load_paper("2025", paper)
        if doc:
            docs_2025[paper] = [(normalize_stem(q.get("stem", "")), q) for _, q in iter_questions(doc)]

    sharing_2025 = {}
    for i, p1 in enumerate(PAPERS):
        for p2 in PAPERS[i + 1:]:
            if p1 not in docs_2025 or p2 not in docs_2025:
                continue
            set1 = {s for s, _ in docs_2025[p1] if s}
            set2 = {s for s, _ in docs_2025[p2] if s}
            shared = set1 & set2
            sharing_2025[f"{p1}_vs_{p2}"] = {
                "shared": len(shared),
                f"{p1}_total": len(set1),
                f"{p2}_total": len(set2),
                f"{p1}_share_rate": len(shared) / len(set1) if set1 else 0,
                f"{p2}_share_rate": len(shared) / len(set2) if set2 else 0,
            }
    # 三卷全共享
    if all(p in docs_2025 for p in PAPERS):
        sets = [{s for s, _ in docs_2025[p] if s} for p in PAPERS]
        all_shared = sets[0] & sets[1] & sets[2]
        sharing_2025["all_three_shared"] = len(all_shared)
        sharing_2025["all_three_total_union"] = len(sets[0] | sets[1] | sets[2])
    result["sharing_2025"] = sharing_2025

    return result


# ═══════════════════════════════════════════════════════════════
# 第二层：答案层（仅 2025 三卷）
# ═══════════════════════════════════════════════════════════════

def compute_answers() -> dict:
    result = {}
    all_2025 = []  # (year, paper, section, q)
    for paper in PAPERS:
        doc = load_paper("2025", paper)
        if doc is None:
            continue
        for sec_name, q in iter_questions(doc):
            all_2025.append(("2025", paper, sec_name, q))

    result["total_2025"] = len(all_2025)

    # 2.1 正确项位置分布（单选，answer 单字母）
    answer_dist = Counter()
    answer_by_module = defaultdict(Counter)
    answer_by_paper = defaultdict(Counter)
    multi_letter = 0
    no_answer = 0
    for _, paper, sec, q in all_2025:
        ans = (q.get("answer") or "").strip()
        if not ans:
            no_answer += 1
            continue
        if len(ans) == 1 and ans in "ABCD":
            answer_dist[ans] += 1
            answer_by_module[sec][ans] += 1
            answer_by_paper[paper][ans] += 1
        else:
            multi_letter += 1
    result["answer_distribution"] = dict(answer_dist)
    result["answer_by_module"] = {k: dict(v) for k, v in answer_by_module.items()}
    result["answer_by_paper"] = {k: dict(v) for k, v in answer_by_paper.items()}
    result["multi_letter_answer"] = multi_letter
    result["no_answer"] = no_answer

    # 2.2 多选/组合题（items 非空）
    items_count = 0
    items_by_module = Counter()
    items_by_paper = Counter()
    for _, paper, sec, q in all_2025:
        if q.get("items"):
            items_count += 1
            items_by_module[sec] += 1
            items_by_paper[paper] += 1
    result["items_questions"] = {
        "total": items_count,
        "by_module": dict(items_by_module),
        "by_paper": dict(items_by_paper),
        "ratio": items_count / len(all_2025) if all_2025 else 0,
    }

    # 2.3 三卷共享率（题干归一化，与结构层一致但单独算答案层）
    docs = {}
    for paper in PAPERS:
        doc = load_paper("2025", paper)
        if doc:
            docs[paper] = [(normalize_stem(q.get("stem", "")), q) for _, q in iter_questions(doc)]
    sharing = {}
    for i, p1 in enumerate(PAPERS):
        for p2 in PAPERS[i + 1:]:
            if p1 not in docs or p2 not in docs:
                continue
            s1 = {s for s, _ in docs[p1] if s}
            s2 = {s for s, _ in docs[p2] if s}
            shared = s1 & s2
            sharing[f"{PAPER_LABEL[p1]}_vs_{PAPER_LABEL[p2]}"] = {
                "shared_count": len(shared),
                f"{PAPER_LABEL[p1]}_total": len(s1),
                f"{PAPER_LABEL[p2]}_total": len(s2),
            }
    if all(p in docs for p in PAPERS):
        sets = [{s for s, _ in docs[p] if s} for p in PAPERS]
        sharing["三卷全共享"] = len(sets[0] & sets[1] & sets[2])
        sharing["三卷并集"] = len(sets[0] | sets[1] | sets[2])
    result["cross_paper_sharing"] = sharing

    return result


# ═══════════════════════════════════════════════════════════════
# 第三层：命题手法层
# ═══════════════════════════════════════════════════════════════

def extract_question_pattern(stem: str) -> str | None:
    """从题干末尾提取设问句式关键词。返回匹配到的模式，未匹配返回 None。"""
    if not stem:
        return None
    # 取题干最后 80 字（设问通常在末尾）
    tail = stem[-80:] if len(stem) > 80 else stem
    # 通用模式：以"下列/以下/这/该/问/则/由此/根据"等开头的设问短语
    # 优先匹配已知模式库
    for module, patterns in QUESTION_PATTERNS.items():
        for pat in patterns:
            if pat in tail:
                return pat
    # 通用兜底：提取"下列……的是"句式
    m = re.search(r"(下列[^，。]{0,20}的是)", tail)
    if m:
        return m.group(1)
    m = re.search(r"(以下[^，。]{0,20}的是)", tail)
    if m:
        return m.group(1)
    m = re.search(r"(这段文字[^，。]{0,15})", tail)
    if m:
        return m.group(1)
    m = re.search(r"(依次填入[^，。]{0,15})", tail)
    if m:
        return m.group(1)
    m = re.search(r"(填入[^，。]{0,15})", tail)
    if m:
        return m.group(1)
    m = re.search(r"(最适合[^，。]{0,15})", tail)
    if m:
        return m.group(1)
    m = re.search(r"(由此[^，。]{0,10})", tail)
    if m:
        return m.group(1)
    m = re.search(r"(可以[^，。]{0,10})", tail)
    if m:
        return m.group(1)
    return None


def compute_techniques() -> dict:
    result = {}

    # 3.1 设问句式频次（全量 6 年，按模块）
    pattern_by_module = defaultdict(Counter)
    pattern_unmatched = Counter()
    total_by_module = Counter()
    for year in YEARS:
        for paper in PAPERS:
            doc = load_paper(year, paper)
            if doc is None:
                continue
            for sec_name, q in iter_questions(doc):
                total_by_module[sec_name] += 1
                pat = extract_question_pattern(q.get("stem", ""))
                if pat:
                    pattern_by_module[sec_name][pat] += 1
                else:
                    pattern_unmatched[sec_name] += 1
    result["question_patterns"] = {
        k: dict(v.most_common(15)) for k, v in pattern_by_module.items()
    }
    result["pattern_unmatched"] = dict(pattern_unmatched)
    result["pattern_total_by_module"] = dict(total_by_module)

    # 3.2 选项长度（全量 6 年，按模块）
    option_len_by_module = defaultdict(list)
    for year in YEARS:
        for paper in PAPERS:
            doc = load_paper(year, paper)
            if doc is None:
                continue
            for sec_name, q in iter_questions(doc):
                opts = q.get("options")
                if not isinstance(opts, dict):
                    continue
                for letter in "ABCD":
                    val = opts.get(letter)
                    if isinstance(val, str) and val.strip():
                        option_len_by_module[sec_name].append(len(val.strip()))
    option_stats = {}
    for mod, lengths in option_len_by_module.items():
        if lengths:
            option_stats[mod] = {
                "count": len(lengths),
                "avg": round(sum(lengths) / len(lengths), 1),
                "max": max(lengths),
                "min": min(lengths),
            }
    result["option_length_stats"] = option_stats

    # 3.3 设错手法（仅 2025 解析）
    error_tech = Counter()
    error_by_module = defaultdict(Counter)
    explanation_count = 0
    for paper in PAPERS:
        doc = load_paper("2025", paper)
        if doc is None:
            continue
        for sec_name, q in iter_questions(doc):
            exp = q.get("explanation") or ""
            if exp.strip():
                explanation_count += 1
            for tech in ERROR_TECHNIQUES:
                if tech in exp:
                    error_tech[tech] += 1
                    error_by_module[sec_name][tech] += 1
    result["error_techniques"] = {
        "total_explanations": explanation_count,
        "overall": dict(error_tech.most_common()),
        "by_module": {k: dict(v.most_common(10)) for k, v in error_by_module.items()},
    }

    return result


# ═══════════════════════════════════════════════════════════════
# 输出
# ═══════════════════════════════════════════════════════════════

def print_text_report(data: dict) -> None:
    """打印人类可读的统计摘要。"""
    print("=" * 70)
    print("S1 真题规律统计 — 现算输出")
    print("=" * 70)

    struct = data["structure"]
    print(f"\n【总题量】6 年合计 {struct['grand_total']} 题")
    for y in YEARS:
        papers = struct["year_paper_matrix"][y]
        parts = []
        for p in PAPERS:
            v = papers[p]
            parts.append(f"{PAPER_LABEL[p]}={v if v is not None else '—'}")
        print(f"  {y}: {' | '.join(parts)} | 年合计 {struct['total_by_year'][y]}")

    print("\n【模块题量按年】")
    for y in YEARS:
        mods = struct["module_by_year"][y]
        total = sum(mods.values())
        parts = []
        for m in STANDARD_MODULES:
            v = mods.get(m, 0)
            if v:
                parts.append(f"{m}={v}({v/total:.0%})")
        print(f"  {y} (N={total}): {' | '.join(parts)}")

    ms = struct["material_stats"]
    print(f"\n【材料-题组】material_ids 非空 {ms['with_material_ids']}/{ms['total']} "
          f"({ms['with_material_ids']/ms['total']:.1%})")
    print(f"  每材料关联题数分布: {ms['per_material_dist']}")
    print("  按模块:")
    for mod, vals in ms["by_module"].items():
        wm = vals.get("with_material", 0)
        tot = vals.get("total", 0)
        print(f"    {mod}: {wm}/{tot} ({wm/tot:.1%})" if tot else f"    {mod}: 0")

    print("\n【provenance.role 按年】")
    for y in YEARS:
        roles = struct["role_by_year"][y]
        total = sum(roles.values())
        shared_like = roles.get("shared", 0) + roles.get("shared_with_shidi", 0)
        print(f"  {y} (N={total}): shared={roles.get('shared',0)} "
              f"shared_with_shidi={roles.get('shared_with_shidi',0)} "
              f"main={roles.get('main',0)} province_only={roles.get('province_only',0)} "
              f"diff_book={roles.get('diff_book',0)} "
              f"共享类占比={shared_like/total:.1%}")

    print("\n【2025 三卷共享率（题干归一化匹配）】")
    for k, v in struct["sharing_2025"].items():
        if isinstance(v, dict):
            print(f"  {k}: shared={v.get('shared')} "
                  f"(rate1={v.get(list(v.keys())[3], 'N/A')}, "
                  f"rate2={v.get(list(v.keys())[4], 'N/A')})")
        else:
            print(f"  {k}: {v}")

    # 答案层
    ans = data["answers"]
    print(f"\n{'=' * 70}")
    print(f"【答案层】仅 2025，N={ans['total_2025']}")
    ad = ans["answer_distribution"]
    total_ans = sum(ad.values())
    print(f"  正确项分布: A={ad.get('A',0)}({ad.get('A',0)/total_ans:.1%}) "
          f"B={ad.get('B',0)}({ad.get('B',0)/total_ans:.1%}) "
          f"C={ad.get('C',0)}({ad.get('C',0)/total_ans:.1%}) "
          f"D={ad.get('D',0)}({ad.get('D',0)/total_ans:.1%})")
    print("  按模块:")
    for mod in STANDARD_MODULES:
        vals = ans["answer_by_module"].get(mod, {})
        t = sum(vals.values())
        if t:
            print(f"    {mod} (N={t}): " + " ".join(
                f"{k}={v}({v/t:.0%})" for k, v in sorted(vals.items())))
    print("  按卷:")
    for p in PAPERS:
        vals = ans["answer_by_paper"].get(p, {})
        t = sum(vals.values())
        if t:
            print(f"    {PAPER_LABEL[p]} (N={t}): " + " ".join(
                f"{k}={v}({v/t:.0%})" for k, v in sorted(vals.items())))

    iq = ans["items_questions"]
    print(f"\n  多选/组合题(items非空): {iq['total']} ({iq['ratio']:.1%})")
    print(f"    按模块: {iq['by_module']}")
    print(f"    按卷: {iq['by_paper']}")
    print(f"  多字母答案: {ans['multi_letter_answer']}, 无答案: {ans['no_answer']}")

    print("\n  三卷共享:")
    for k, v in ans["cross_paper_sharing"].items():
        print(f"    {k}: {v}")

    # 命题手法层
    tech = data["techniques"]
    print(f"\n{'=' * 70}")
    print("【命题手法层】")
    print("\n  设问句式 Top（按模块）:")
    for mod in STANDARD_MODULES:
        pats = tech["question_patterns"].get(mod, {})
        if pats:
            top5 = list(pats.items())[:5]
            print(f"    {mod}: " + " | ".join(f"{k}({v})" for k, v in top5))
    unmatched = tech["pattern_unmatched"]
    total_mod = tech["pattern_total_by_module"]
    print(f"\n  设问未匹配数: {sum(unmatched.values())}/{sum(total_mod.values())}")
    for mod in STANDARD_MODULES:
        u = unmatched.get(mod, 0)
        t = total_mod.get(mod, 0)
        if t:
            print(f"    {mod}: {u}/{t} ({u/t:.1%})")

    print("\n  选项长度统计（按模块）:")
    for mod in STANDARD_MODULES:
        s = tech["option_length_stats"].get(mod)
        if s:
            print(f"    {mod}: avg={s['avg']}字 max={s['max']} min={s['min']} (N={s['count']})")

    et = tech["error_techniques"]
    print(f"\n  设错手法（2025 解析，N={et['total_explanations']}）:")
    for k, v in et["overall"].items():
        print(f"    {k}: {v}")
    print("  按模块 Top:")
    for mod in STANDARD_MODULES:
        vals = et["by_module"].get(mod, {})
        if vals:
            top3 = list(vals.items())[:3]
            print(f"    {mod}: " + " | ".join(f"{k}({v})" for k, v in top3))

    print(f"\n{'=' * 70}")
    print("统计完成。所有数字从 JSON 现算。")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = ap.parse_args()

    data = {
        "structure": compute_structure(),
        "answers": compute_answers(),
        "techniques": compute_techniques(),
    }

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        print_text_report(data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
