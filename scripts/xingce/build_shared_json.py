#!/usr/bin/env python3
"""
D10: 2025 三卷去重 shared.json — 共享题抽实体 + 卷位引用

将 2025 三卷（省级/市地/行政执法）中的共享题抽取为逻辑实体，
各卷保存引用+题号，复用 provenance 信息而非只靠 hash。

产出:
  xingce-structured-data/2025/xingce/shared.json
  xingce-structured-data/2025/xingce/_extract/shared_map.json

共享判定策略（优先级从高到低）:
  1. provenance.role = "shared"           — 三卷共享
  2. provenance.role = "shared_with_shidi" — 省级与市地共享
  3. provenance.role = "diff_book"         — 差异册题（非共享）
  4. canonical_hash 匹配                    — 辅助判定
  5. 答案一致性校验                          — hash 匹配但 answer 不同 → 冲突

硬约束:
  - 不修改原卷 JSON
  - 高风险题（content_mismatch_needs_source, section_type_mismatch）不参与合并
  - 答案冲突题不自动合并
  - JSON ensure_ascii=False, indent=2
"""

import json
import hashlib
import re
import os
from collections import defaultdict
from datetime import date

# ── 配置 ──────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAPERS_DIR = os.path.join(BASE, "xingce-structured-data", "2025", "xingce", "papers")
OUTPUT_SHARED = os.path.join(BASE, "xingce-structured-data", "2025", "xingce", "shared.json")
OUTPUT_MAP = os.path.join(BASE, "xingce-structured-data", "2025", "xingce", "_extract", "shared_map.json")

PAPERS = ["shengji", "shidi", "xingzhengzhifa"]
PAPER_LABEL = {
    "shengji": "省级",
    "shidi": "市地",
    "xingzhengzhifa": "行政执法",
}
HIGH_RISK_FLAGS = {"content_mismatch_needs_source", "section_type_mismatch"}

# 图形推理通用模板题干（不能只靠 stem 匹配）
GRAPHIC_TEMPLATE_PATTERNS = [
    "从所给的四个选项中",
    "选择最合适的一个填入问号处",
    "使之呈现一定的规律性",
]


# ── 工具函数 ───────────────────────────────────────────────────────
_PUNCT_MAP = {
    "\uff0c": ",",  # ，
    "\u3002": ".",  # 。
    "\uff01": "!",  # ！
    "\uff1f": "?",  # ？
    "\uff1b": ";",  # ；
    "\uff1a": ":",  # ：
    "\u201c": '"',  # "
    "\u201d": '"',  # "
    "\u2018": "'",  # '
    "\u2019": "'",  # '
    "\uff08": "(",  # （
    "\uff09": ")",  # ）
    "\u3010": "[",  # 【
    "\u3011": "]",  # 】
    "\u300a": "<",  # 《
    "\u300b": ">",  # 》
    "\u3001": ",",  # 、
}


def normalize_text(text: str) -> str:
    """标准化文本：去空白、统一标点、全角转半角。"""
    if not text:
        return ""
    # 全角转半角（用 dict 避免引号转义问题）
    for full, half in _PUNCT_MAP.items():
        text = text.replace(full, half)
    # 去所有空白
    text = re.sub(r"\s+", "", text)
    # 统一常见变体
    text = text.replace("\u2014", "-").replace("\u2013", "-").replace("\uff0d", "-")
    # 圈号数字
    circled = "\u2460\u2461\u2462\u2463\u2464\u2465\u2466\u2467\u2468\u2469"
    for i, ch in enumerate(circled, 1):
        text = text.replace(ch, str(i))
    return text.lower()


def is_graphic_template_stem(stem: str) -> bool:
    """判断是否为图形推理通用模板题干。"""
    if not stem:
        return False
    norm = normalize_text(stem)
    return any(p in norm for p in ["从所给的四个选项中", "选择最合适的一个填入问号处"])


def compute_canonical_hash(q: dict) -> str:
    """
    计算标准化哈希。
    - 普通题：stem + options + items
    - 图形推理模板题：stem + options + items + media paths（必须纳入 media）
    - 资料分析题：stem + options + material_ids
    """
    parts = []

    stem = q.get("stem", "") or ""
    # 去除 [内容待回源核实] 等标记前缀
    stem_clean = re.sub(r"^\[[^\]]*\]\s*", "", stem)
    parts.append("stem:" + normalize_text(stem_clean))

    # options
    options = q.get("options")
    if options:
        opt_parts = []
        for key in sorted(options.keys()):
            opt_parts.append(f"{key}:{normalize_text(str(options[key]))}")
        parts.append("opts:" + "|".join(opt_parts))
    else:
        parts.append("opts:null")

    # items（多选题的子项）
    items = q.get("items")
    if items:
        item_parts = [normalize_text(str(it)) for it in items]
        parts.append("items:" + "|".join(item_parts))

    # media（图形推理必须纳入）
    media = q.get("media") or []
    if media or is_graphic_template_stem(stem):
        media_paths = []
        for m in media:
            if isinstance(m, dict):
                media_paths.append(m.get("path", ""))
            else:
                media_paths.append(str(m))
        parts.append("media:" + "|".join(sorted(media_paths)))

    # material_ids 不纳入哈希：不同卷对同一材料使用不同编号
    #（如 shengji m116_120 vs shidi m111_115），会导致误判为不同题。
    # stem + options 已足够区分资料分析题。

    raw = "||".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_paper(paper: str) -> list[dict]:
    """加载一卷的所有题目，展平 sections。"""
    path = os.path.join(PAPERS_DIR, f"{paper}.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = []
    for section in data.get("sections", []):
        section_name = section.get("name", "")
        for q in section.get("questions", []):
            q["_section_name"] = section_name
            q["_paper"] = paper
            questions.append(q)
    return questions


def is_high_risk(q: dict) -> list[str]:
    """返回高风险 flag 列表（空列表表示非高风险）。"""
    flags = q.get("flags") or []
    return [f for f in flags if f in HIGH_RISK_FLAGS]


def get_provenance_role(q: dict) -> str:
    prov = q.get("provenance") or {}
    return prov.get("role", "none")


def get_provenance_note(q: dict) -> str:
    prov = q.get("provenance") or {}
    return prov.get("raw_note", "") or prov.get("diff_label", "") or ""


def determine_shared_level(papers_present: set[str]) -> str:
    """根据出现的卷集确定共享层级。"""
    if papers_present == {"shengji", "shidi", "xingzhengzhifa"}:
        return "three_paper"
    elif papers_present == {"shengji", "shidi"}:
        return "shengji_shidi"
    elif papers_present == {"shengji", "xingzhengzhifa"}:
        return "shengji_xzzf"
    elif papers_present == {"shidi", "xingzhengzhifa"}:
        return "shidi_xzzf"
    elif len(papers_present) == 1:
        return "paper_unique"
    else:
        return "unknown"


def pick_canonical(position_list: list[dict]) -> dict:
    """
    选择规范卷引用：优先省级 > 市地 > 执法，
    同卷内取题号最小的。
    """
    priority = {"shengji": 0, "shidi": 1, "xingzhengzhifa": 2}
    sorted_pos = sorted(position_list, key=lambda p: (priority.get(p["paper"], 9), p["number"]))
    return {
        "canonical_paper": sorted_pos[0]["paper"],
        "canonical_number": sorted_pos[0]["number"],
    }


# ── 主流程 ─────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("D10: 2025 三卷去重 shared.json")
    print("=" * 60)

    # 1. 加载三卷
    all_questions = {}
    for p in PAPERS:
        all_questions[p] = load_paper(p)
        print(f"  加载 {PAPER_LABEL[p]}: {len(all_questions[p])} 题")

    # 2. 分离高风险题 + 计算 hash
    excluded = []
    hash_groups = defaultdict(list)  # hash -> [question, ...]
    paper_question_map = {}  # (paper, number) -> question (for shared_map)

    for p in PAPERS:
        for q in all_questions[p]:
            key = (p, q["number"])
            paper_question_map[key] = q

            hr_flags = is_high_risk(q)
            if hr_flags:
                excluded.append({
                    "paper": p,
                    "number": q["number"],
                    "section": q.get("_section_name", ""),
                    "reason": ",".join(hr_flags),
                    "role": get_provenance_role(q),
                })
                continue

            h = compute_canonical_hash(q)
            hash_groups[h].append(q)

    print(f"\n  高风险排除: {len(excluded)} 题位")
    print(f"  参与匹配: {sum(len(v) for v in hash_groups.values())} 题位")
    print(f"  唯一 hash 组: {len(hash_groups)}")

    # 3. 分组匹配，建立实体
    entities = []
    answer_conflicts = []
    entity_counter = 0
    conflict_counter = 0

    # 按 hash 组的规范题号排序，保证 entity_id 稳定
    def group_sort_key(item):
        h, qs = item
        canonical = pick_canonical([{"paper": q["_paper"], "number": q["number"]} for q in qs])
        return (canonical["canonical_paper"], canonical["canonical_number"])

    for h, qs in sorted(hash_groups.items(), key=group_sort_key):
        papers_present = set(q["_paper"] for q in qs)
        shared_level = determine_shared_level(papers_present)

        # 答案一致性校验
        answers = set()
        for q in qs:
            ans = q.get("answer")
            if ans:
                answers.add(ans)

        position_list = []
        for q in sorted(qs, key=lambda x: (PAPERS.index(x["_paper"]), x["number"])):
            position_list.append({
                "paper": q["_paper"],
                "number": q["number"],
                "section": q.get("_section_name", ""),
            })

        if len(answers) > 1:
            # 答案冲突 → 不自动合并
            conflict_counter += 1
            cid = f"E2025-C{conflict_counter:03d}"
            conflict_positions = []
            for q in sorted(qs, key=lambda x: (PAPERS.index(x["_paper"]), x["number"])):
                conflict_positions.append({
                    "paper": q["_paper"],
                    "number": q["number"],
                    "answer": q.get("answer", ""),
                    "section": q.get("_section_name", ""),
                })
            answer_conflicts.append({
                "entity_id": cid,
                "canonical_hash": h,
                "description": "hash匹配但答案不同",
                "shared_level": shared_level,
                "positions": conflict_positions,
            })
            continue

        # 正常实体
        entity_counter += 1
        eid = f"E2025-{entity_counter:04d}"

        # 取规范题的 module / subtype / answer / provenance_note
        canonical_ref = pick_canonical(position_list)
        canonical_q = None
        for q in qs:
            if q["_paper"] == canonical_ref["canonical_paper"] and q["number"] == canonical_ref["canonical_number"]:
                canonical_q = q
                break
        if canonical_q is None:
            canonical_q = qs[0]

        # provenance 汇总：收集所有位置的 role 和 note
        prov_roles = set()
        prov_notes = set()
        for q in qs:
            role = get_provenance_role(q)
            if role and role != "none":
                prov_roles.add(role)
            note = get_provenance_note(q)
            if note:
                prov_notes.add(note)

        provenance_note = "; ".join(sorted(prov_notes)) if prov_notes else ""
        if not provenance_note:
            provenance_note = ",".join(sorted(prov_roles)) if prov_roles else ""

        entity = {
            "entity_id": eid,
            "canonical_hash": h,
            "module": canonical_q.get("_section_name", "") or canonical_q.get("section", ""),
            "subtype": canonical_q.get("type"),
            "shared_level": shared_level,
            "answer": canonical_q.get("answer", ""),
            "provenance_roles": sorted(prov_roles),
            "provenance_note": provenance_note,
            "positions": position_list,
            "question_ref": canonical_ref,
        }
        entities.append(entity)

    # 4. 统计
    summary = {
        "total_unique_entities": len(entities),
        "three_paper_shared": sum(1 for e in entities if e["shared_level"] == "three_paper"),
        "shengji_shidi_shared": sum(1 for e in entities if e["shared_level"] == "shengji_shidi"),
        "shengji_xzzf_shared": sum(1 for e in entities if e["shared_level"] == "shengji_xzzf"),
        "shidi_xzzf_shared": sum(1 for e in entities if e["shared_level"] == "shidi_xzzf"),
        "paper_unique": {
            "shengji": sum(1 for e in entities if e["shared_level"] == "paper_unique"
                           and e["positions"][0]["paper"] == "shengji"),
            "shidi": sum(1 for e in entities if e["shared_level"] == "paper_unique"
                         and e["positions"][0]["paper"] == "shidi"),
            "xingzhengzhifa": sum(1 for e in entities if e["shared_level"] == "paper_unique"
                                   and e["positions"][0]["paper"] == "xingzhengzhifa"),
        },
        "answer_conflicts": len(answer_conflicts),
        "excluded_count": len(excluded),
    }

    # 5. 生成 shared.json
    output = {
        "version": "v1",
        "year": 2025,
        "generated_at": date.today().isoformat(),
        "summary": summary,
        "entities": entities,
        "answer_conflicts": answer_conflicts,
        "excluded": excluded,
    }

    os.makedirs(os.path.dirname(OUTPUT_SHARED), exist_ok=True)
    with open(OUTPUT_SHARED, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  写入 {OUTPUT_SHARED}")

    # 6. 生成 shared_map.json（每卷每题 → entity_id 或 null）
    shared_map = {}
    # 建立 (paper, number) -> entity_id 映射
    pos_to_entity = {}
    for e in entities:
        for pos in e["positions"]:
            pos_to_entity[(pos["paper"], pos["number"])] = e["entity_id"]
    # 答案冲突题也映射到 conflict entity_id
    for c in answer_conflicts:
        for pos in c["positions"]:
            pos_to_entity[(pos["paper"], pos["number"])] = c["entity_id"]

    for p in PAPERS:
        shared_map[p] = {}
        for q in all_questions[p]:
            num = q["number"]
            eid = pos_to_entity.get((p, num))
            hr = is_high_risk(q)
            entry = {
                "entity_id": eid,
                "section": q.get("_section_name", ""),
                "role": get_provenance_role(q),
            }
            if hr:
                entry["excluded"] = True
                entry["excluded_reason"] = ",".join(hr)
            shared_map[p][str(num)] = entry

    os.makedirs(os.path.dirname(OUTPUT_MAP), exist_ok=True)
    with open(OUTPUT_MAP, "w", encoding="utf-8") as f:
        json.dump(shared_map, f, ensure_ascii=False, indent=2)
    print(f"  写入 {OUTPUT_MAP}")

    # 7. 打印统计报告
    print("\n" + "=" * 60)
    print("统计报告")
    print("=" * 60)
    print(f"  唯一实体数: {summary['total_unique_entities']}")
    print(f"  三卷全共享: {summary['three_paper_shared']}")
    print(f"  省市共享:   {summary['shengji_shidi_shared']}")
    print(f"  省执法共享: {summary['shengji_xzzf_shared']}")
    print(f"  市执法共享: {summary['shidi_xzzf_shared']}")
    print(f"  卷独有:     省级={summary['paper_unique']['shengji']}, "
          f"市地={summary['paper_unique']['shidi']}, "
          f"执法={summary['paper_unique']['xingzhengzhifa']}")
    print(f"  答案冲突:   {summary['answer_conflicts']}")
    print(f"  高风险排除: {summary['excluded_count']} 题位")

    # 交叉验证
    print("\n--- 交叉验证 ---")
    # 政治理论 20 题三卷全共享
    political_three = sum(1 for e in entities
                           if e["shared_level"] == "three_paper" and e["module"] == "政治理论")
    print(f"  政治理论三卷全共享: {political_three} (期望 20)")

    # 执法卷在市地卷的覆盖率
    xzzf_matched = 0
    xzzf_total = 0
    for p in PAPERS:
        if p != "xingzhengzhifa":
            continue
        for q in all_questions[p]:
            if is_high_risk(q):
                continue
            xzzf_total += 1
            if (p, q["number"]) in pos_to_entity:
                eid = pos_to_entity[(p, q["number"])]
                # 检查该实体是否也出现在市地
                for e in entities + answer_conflicts:
                    if e["entity_id"] == eid:
                        papers_in_entity = set(pos["paper"] for pos in e["positions"])
                        if "shidi" in papers_in_entity:
                            xzzf_matched += 1
                        break
    print(f"  执法卷非高风险题在市地卷匹配率: {xzzf_matched}/{xzzf_total} "
          f"({xzzf_matched/xzzf_total*100:.1f}%)" if xzzf_total else "  执法卷匹配率: N/A")

    # 实体题位总数校验
    total_positions = sum(len(e["positions"]) for e in entities)
    total_conflict_positions = sum(len(c["positions"]) for c in answer_conflicts)
    print(f"  实体覆盖题位: {total_positions} + 冲突题位: {total_conflict_positions} "
          f"+ 排除题位: {len(excluded)} = {total_positions + total_conflict_positions + len(excluded)}")
    print(f"  三卷总题位: 395")

    print("\n完成。")


if __name__ == "__main__":
    main()
