#!/usr/bin/env python3
"""D6a: 2025 三卷真题可自动化缺陷修复。

修复内容：
1. 执法卷（xingzhengzhifa）卷内内容错配标记：
   - Q68/Q71（数量关系区，正确）移除 duplicate_in_paper flag
   - Q100/Q101（判断推理区，内容错配）保留 section_type_mismatch，
     新增 content_mismatch_needs_source，stem 前加 [内容待回源核实] 前缀
2. 材料 m106_110 补提取（三卷均有）：
   - 从 20252447.pdf 第11-12页提取逻辑分析材料文本
   - 每卷顶层新增 materials 字段
   - 移除对应题目的 material_ref_dangling flag

硬约束：不改动 answer/explanation；JSON ensure_ascii=False indent=2。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DATA_REPO = Path("/Users/dnn/Projects/zhixing-gongkao/xingce-structured-data")
PAPERS_DIR = DATA_REPO / "2025" / "xingce" / "papers"

# ── m106_110 材料文本（从 20252447.pdf p11-12 提取）──
M106_110_CONTENT = (
    "某科研机构今年拟举办甲、乙、丙、丁、戊、己、庚、辛8次学术会议，"
    "每个季度最多举办3次，且各次会议举办时间不重叠。具体安排要求如下：\n"
    "(1)丁、辛安排在第二季度；\n"
    "(2)甲、戊安排在同一个季度；\n"
    "(3)丁在乙之后丙之前举办；\n"
    "(4)丙在甲之前己之后举办。"
)

MATERIALS = {
    "m106_110": {
        "id": "m106_110",
        "content": M106_110_CONTENT,
        "extraction_method": "pdf_text",
        "source_ref": {
            "file": "20252447.pdf",
            "pages": [11, 12],
            "note": "判断推理区分析推理题组材料，对应Q106-110（市地/执法卷编号）",
        },
    }
}


def load_paper(name: str) -> dict:
    path = PAPERS_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_paper(name: str, data: dict) -> None:
    path = PAPERS_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def find_question(data: dict, number: int) -> dict | None:
    for section in data.get("sections", []):
        for q in section.get("questions", []):
            if q.get("number") == number:
                return q
    return None


def remove_flag(q: dict, flag: str) -> bool:
    flags = q.get("flags", [])
    if flag in flags:
        flags.remove(flag)
        q["flags"] = flags
        return True
    return False


def add_flag(q: dict, flag: str) -> bool:
    flags = q.get("flags", [])
    if flag not in flags:
        flags.append(flag)
        q["flags"] = flags
        return True
    return False


# ═══════════════════════════════════════════════════════════
# 缺陷1：执法卷内容错配标记
# ═══════════════════════════════════════════════════════════
def fix_defect_1() -> dict[str, int]:
    """修复执法卷 Q68/Q71/Q100/Q101 标记。返回变更统计。"""
    stats = {"q68_flag_removed": 0, "q71_flag_removed": 0,
             "q100_flag_added": 0, "q101_flag_added": 0,
             "q100_prefix_added": 0, "q101_prefix_added": 0}

    data = load_paper("xingzhengzhifa")

    # Q68: 移除 duplicate_in_paper
    q68 = find_question(data, 68)
    if q68 and remove_flag(q68, "duplicate_in_paper"):
        stats["q68_flag_removed"] = 1

    # Q71: 移除 duplicate_in_paper
    q71 = find_question(data, 71)
    if q71 and remove_flag(q71, "duplicate_in_paper"):
        stats["q71_flag_removed"] = 1

    # Q100: 新增 content_mismatch_needs_source，加前缀
    q100 = find_question(data, 100)
    if q100:
        if add_flag(q100, "content_mismatch_needs_source"):
            stats["q100_flag_added"] = 1
        prefix = "[内容待回源核实] "
        if not q100["stem"].startswith(prefix):
            q100["stem"] = prefix + q100["stem"]
            stats["q100_prefix_added"] = 1

    # Q101: 新增 content_mismatch_needs_source，加前缀
    q101 = find_question(data, 101)
    if q101:
        if add_flag(q101, "content_mismatch_needs_source"):
            stats["q101_flag_added"] = 1
        prefix = "[内容待回源核实] "
        if not q101["stem"].startswith(prefix):
            q101["stem"] = prefix + q101["stem"]
            stats["q101_prefix_added"] = 1

    save_paper("xingzhengzhifa", data)
    return stats


# ═══════════════════════════════════════════════════════════
# 缺陷2：材料 m106_110 补提取
# ═══════════════════════════════════════════════════════════
def fix_defect_2() -> dict[str, int]:
    """三卷新增 materials 字段，移除 material_ref_dangling flag。"""
    stats = {}
    for name in ["shengji", "shidi", "xingzhengzhifa"]:
        data = load_paper(name)

        # 新增 materials 字段（若不存在）
        if "materials" not in data:
            data["materials"] = {}
        data["materials"]["m106_110"] = MATERIALS["m106_110"]

        # 移除 material_ref_dangling flag
        dangling_removed = 0
        for section in data.get("sections", []):
            for q in section.get("questions", []):
                if "m106_110" in q.get("material_ids", []):
                    if remove_flag(q, "material_ref_dangling"):
                        dangling_removed += 1

        save_paper(name, data)
        stats[name] = {"materials_added": 1, "dangling_removed": dangling_removed}

    return stats


# ═══════════════════════════════════════════════════════════
# 验证：答案/解析未变、题量未变
# ═══════════════════════════════════════════════════════════
def verify_integrity() -> None:
    """对比备份，确认 answer/explanation 字段未变、题量未变。"""
    bak_dir = PAPERS_DIR.parent / "papers.bak_d6a"
    issues = []

    for name in ["shengji", "shidi", "xingzhengzhifa"]:
        with open(bak_dir / f"{name}.json", encoding="utf-8") as f:
            old = json.load(f)
        with open(PAPERS_DIR / f"{name}.json", encoding="utf-8") as f:
            new = json.load(f)

        # 题量
        old_count = sum(len(s.get("questions", [])) for s in old.get("sections", []))
        new_count = sum(len(s.get("questions", [])) for s in new.get("sections", []))
        if old_count != new_count:
            issues.append(f"{name}: 题量变化 {old_count}→{new_count}")

        # answer/explanation 逐题对比
        old_answers = {}
        new_answers = {}
        for section in old.get("sections", []):
            for q in section.get("questions", []):
                old_answers[q["number"]] = (q.get("answer"), q.get("explanation"))
        for section in new.get("sections", []):
            for q in section.get("questions", []):
                new_answers[q["number"]] = (q.get("answer"), q.get("explanation"))

        for num in old_answers:
            if num in new_answers and old_answers[num] != new_answers[num]:
                issues.append(f"{name} Q{num}: answer/explanation 被改动")

    if issues:
        print("❌ 完整性校验失败：")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    else:
        total = sum(
            sum(len(s.get("questions", [])) for s in load_paper(n).get("sections", []))
            for n in ["shengji", "shidi", "xingzhengzhifa"]
        )
        print(f"✅ 完整性校验通过：答案/解析未变，三卷总题量 {total}")


def main() -> int:
    print("=" * 60)
    print("D6a: 2025 可自动化缺陷修复")
    print("=" * 60)

    print("\n[1/3] 缺陷1：执法卷内容错配标记...")
    s1 = fix_defect_1()
    for k, v in s1.items():
        print(f"  {k}: {v}")

    print("\n[2/3] 缺陷2：材料 m106_110 补提取...")
    s2 = fix_defect_2()
    for paper, st in s2.items():
        print(f"  {paper}: {st}")

    print("\n[3/3] 完整性校验...")
    verify_integrity()

    print("\n✅ 全部修复完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
