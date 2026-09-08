#!/usr/bin/env python3
"""2025 答案映射 v2：跨卷题干匹配 + 差异题匹配。

策略：
  1. 市地：主卷 Q1-130 直接映射
  2. 省级/执法：
     a. 先拿 paper 题干与市地题干做高相似度匹配 → 共享题直接用市地答案
     b. 未匹配到市地的 → 在差异题答案池中匹配（用解析内容）
     c. provenance role 作为先验：shared/mapped 优先搜市地，province_only/diff_book 优先搜差异
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "xingce-structured-data"
BASE = DATA / "2025" / "xingce"
EXTRACT = BASE / "_extract"
PAPERS = BASE / "papers"

_PUNCT_RE = re.compile(
    r"[\s，。、；：？！…—·\"\"''（）《》【】〈〉「」『』"
    r"\-\.,;:!?\(\)\[\]{}\"'<>/\\|~`@#\$%\^&\*_=\+]"
)


def normalize(text: str) -> str:
    if not text:
        return ""
    return _PUNCT_RE.sub("", str(text))


def stem_similarity(s1: str, s2: str) -> float:
    """两个题干的相似度（归一化后，前60字）。"""
    n1 = normalize(s1)[:60]
    n2 = normalize(s2)[:60]
    if not n1 or not n2:
        return 0.0
    # 前缀匹配
    for n in (50, 40, 30, 20, 15):
        if n1[:n] == n2[:n]:
            return 1.0
    # 滑动窗口
    short, long = (n1, n2) if len(n1) <= len(n2) else (n2, n1)
    best = 0.0
    step = max(1, len(short) // 3)
    for i in range(0, max(1, len(long) - len(short)), step):
        w = long[i : i + len(short)]
        common = sum(1 for a, b in zip(short, w) if a == b)
        s = common / len(short)
        if s > best:
            best = s
    return best


def explanation_match(paper_stem: str, ans: dict) -> float:
    """题干与答案解析的匹配度。"""
    norm_stem = normalize(paper_stem)
    combined = normalize(ans.get("anchor_stem", "")) + normalize(ans.get("explanation", ""))[:500]
    if not norm_stem or not combined:
        return 0.0
    # 前缀子串
    for n in (25, 20, 15, 12, 8):
        if norm_stem[:n] in combined and len(norm_stem[:n]) >= 4:
            return 1.0
    # 滑动窗口
    stem20 = norm_stem[:20]
    best = 0.0
    if len(stem20) >= 4:
        step = max(1, len(stem20) // 2)
        for i in range(0, max(1, len(combined) - len(stem20)), step):
            w = combined[i : i + len(stem20)]
            if len(w) < 4:
                continue
            common = sum(1 for a, b in zip(stem20, w) if a == b)
            s = common / len(stem20)
            if s > best:
                best = s
    # 2-gram
    if len(norm_stem) >= 6:
        bigrams = {norm_stem[i : i + 2] for i in range(min(10, len(norm_stem) - 1))}
        hit = sum(1 for g in bigrams if g in combined)
        if bigrams and hit / len(bigrams) >= 0.5:
            best = max(best, hit / len(bigrams) * 0.7)
    return best


def load_raw() -> tuple[list[dict], list[dict]]:
    main: list[dict] = []
    diff: dict[int, dict] = {}
    for fname in ("raw_20250124.json", "raw_20252548.json", "raw_20254972.json", "raw_20257377.json"):
        path = EXTRACT / fname
        if not path.exists():
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        qs = d.get("questions", d) if isinstance(d, dict) else d
        for q in qs:
            if q.get("is_difference"):
                num = q["number"]
                if num in diff:
                    old = diff[num]
                    if len(q.get("explanation", "")) > len(old.get("explanation", "")):
                        if q.get("explanation", "")[:20] not in old.get("explanation", ""):
                            q["explanation"] = old.get("explanation", "") + q.get("explanation", "")
                            q["pending"] = False
                        diff[num] = q
                else:
                    diff[num] = q
            else:
                main.append(q)
    main.sort(key=lambda x: x["number"])
    return main, [diff[k] for k in sorted(diff.keys())]


def build_shidi(main: list[dict]) -> list[dict]:
    return [{
        "number": q["number"],
        "answer": q["answer"],
        "explanation": q.get("explanation", ""),
        "subtype": q.get("subtype"),
        "anchor_stem": q.get("anchor_stem", ""),
    } for q in main]


def match_paper(
    paper_name: str,
    shidi_answers: list[dict],
    shidi_stems: list[tuple[int, str]],
    diff_answers: list[dict],
    direct_map: dict[int, dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """匹配某卷答案。返回 (answers, unmatched)。"""
    paper = json.loads((PAPERS / f"{paper_name}.json").read_text(encoding="utf-8"))
    all_q = []
    for s in paper["sections"]:
        all_q.extend(s["questions"])

    used_shidi: set[int] = set()
    used_diff: set[int] = set()
    answers: list[dict] = []
    unmatched: list[dict] = []

    # 直接映射
    direct_nums = set()
    if direct_map:
        for num, ans in direct_map.items():
            answers.append({
                "number": num, "answer": ans["answer"],
                "explanation": ans.get("explanation", ""),
                "subtype": ans.get("subtype"),
                "anchor_stem": ans.get("anchor_stem", ""),
                "_method": "direct",
            })
            direct_nums.add(num)

    for q in all_q:
        num = q["number"]
        if num in direct_nums:
            continue
        stem = q.get("stem", "")
        role = q.get("provenance", {}).get("role", "")

        # ── 第一步：匹配市地题干（共享题）──
        best_shidi = None
        best_shidi_score = 0.0
        best_shidi_num = 0
        for snum, sstem in shidi_stems:
            if snum in used_shidi:
                continue
            score = stem_similarity(stem, sstem)
            if score > best_shidi_score:
                best_shidi_score = score
                best_shidi_num = snum
                best_shidi = shidi_answers[snum - 1]  # shidi answers are 1-indexed sequential

        # ── 第二步：匹配差异题 ──
        best_diff = None
        best_diff_score = 0.0
        best_diff_idx = -1
        for idx, dans in enumerate(diff_answers):
            if idx in used_diff:
                continue
            score = explanation_match(stem, dans)
            if score > best_diff_score:
                best_diff_score = score
                best_diff = dans
                best_diff_idx = idx

        # ── 决策 ──
        # 市地题干匹配阈值低（共享题题干应高度相似）
        if best_shidi and best_shidi_score >= 0.45:
            used_shidi.add(best_shidi_num)
            answers.append({
                "number": num, "answer": best_shidi["answer"],
                "explanation": best_shidi.get("explanation", ""),
                "subtype": best_shidi.get("subtype"),
                "anchor_stem": best_shidi.get("anchor_stem", ""),
                "_method": f"shidi_stem[{best_shidi_score:.2f}]",
                "_source": f"shidi_Q{best_shidi_num}",
            })
        elif best_diff and best_diff_score >= 0.30:
            used_diff.add(best_diff_idx)
            answers.append({
                "number": num, "answer": best_diff["answer"],
                "explanation": best_diff.get("explanation", ""),
                "subtype": best_diff.get("subtype"),
                "anchor_stem": best_diff.get("anchor_stem", ""),
                "_method": f"diff[{best_diff_score:.2f}]",
                "_source": f"diff_Q{best_diff['number']}",
            })
        else:
            unmatched.append({
                "number": num, "role": role,
                "stem_head": normalize(stem)[:30],
                "best_shidi": best_shidi_score,
                "best_diff": best_diff_score,
            })

    answers.sort(key=lambda x: x["number"])
    return answers, unmatched


def main():
    print("加载原始提取...")
    main_ans, diff_ans = load_raw()
    print(f"  主卷: {len(main_ans)} 题, 差异: {len(diff_ans)} 题")

    # 市地
    shidi_answers = build_shidi(main_ans)
    shidi_paper = json.loads((PAPERS / "shidi.json").read_text(encoding="utf-8"))
    shidi_stems = []
    for s in shidi_paper["sections"]:
        for q in s["questions"]:
            shidi_stems.append((q["number"], q.get("stem", "")))
    shidi_stems.sort(key=lambda x: x[0])

    (EXTRACT / "answers_shidi.json").write_text(
        json.dumps(shidi_answers, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n市地: {len(shidi_answers)}/130 (direct)")

    # 省级：Q1-75 直接映射
    direct_sj = {}
    for a in main_ans:
        if 1 <= a["number"] <= 75:
            direct_sj[a["number"]] = a

    print("\n省级匹配中...")
    sj_answers, sj_unmatched = match_paper(
        "shengji", shidi_answers, shidi_stems, diff_ans, direct_map=direct_sj
    )
    clean = [{k: v for k, v in a.items() if not k.startswith("_")} for a in sj_answers]
    (EXTRACT / "answers_shengji.json").write_text(
        json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    methods = {}
    for a in sj_answers:
        m = a.get("_method", "direct").split("[")[0]
        methods[m] = methods.get(m, 0) + 1
    print(f"  → {len(sj_answers)}/135, 未匹配 {len(sj_unmatched)}, 方法: {methods}")

    # 执法
    print("\n执法匹配中...")
    xz_answers, xz_unmatched = match_paper(
        "xingzhengzhifa", shidi_answers, shidi_stems, diff_ans
    )
    clean = [{k: v for k, v in a.items() if not k.startswith("_")} for a in xz_answers]
    (EXTRACT / "answers_xzzf.json").write_text(
        json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    methods = {}
    for a in xz_answers:
        m = a.get("_method", "direct").split("[")[0]
        methods[m] = methods.get(m, 0) + 1
    print(f"  → {len(xz_answers)}/130, 未匹配 {len(xz_unmatched)}, 方法: {methods}")

    # 未匹配清单
    report = {"shengji": sj_unmatched, "xingzhengzhifa": xz_unmatched}
    (EXTRACT / "mapping_unmatched.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n{'='*50}")
    print(f"市地: {len(shidi_answers)}/130")
    print(f"省级: {len(sj_answers)}/135 (未匹配 {len(sj_unmatched)})")
    print(f"执法: {len(xz_answers)}/130 (未匹配 {len(xz_unmatched)})")
    if sj_unmatched:
        print("\n省级未匹配:")
        for u in sj_unmatched[:15]:
            print(f"  Q{u['number']}({u['role']}): {u['stem_head']} shidi={u['best_shidi']:.2f} diff={u['best_diff']:.2f}")
    if xz_unmatched:
        print("\n执法未匹配:")
        for u in xz_unmatched[:15]:
            print(f"  Q{u['number']}({u['role']}): {u['stem_head']} shidi={u['best_shidi']:.2f} diff={u['best_diff']:.2f}")


if __name__ == "__main__":
    main()
