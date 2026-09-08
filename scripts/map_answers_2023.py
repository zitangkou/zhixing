#!/usr/bin/env python3
"""2023 答案映射：三卷合一答案 → 省级/市地/执法三卷。

策略：
  1. 市地：主卷 Q1-130 直接映射
  2. 省级：
     a. shared (49题) → by from_number 映射市地答案
     b. province_only (86题) → 内容匹配省级差异题 (85题)
  3. 执法：
     a. shared_with_shidi (64题) → by from_number 映射市地答案
     b. shared (30题) → 内容匹配省级差异题（与省级共享但非市地）
     c. diff_book (36题) → 内容匹配行政执法差异题 (36题)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "xingce-structured-data"
BASE = DATA / "2023" / "xingce"
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
    """两个题干的相似度（归一化后，前80字）。"""
    n1 = normalize(s1)[:80]
    n2 = normalize(s2)[:80]
    if not n1 or not n2:
        return 0.0
    # 前缀匹配
    for n in (60, 50, 40, 30, 20, 15):
        if n1[:n] == n2[:n] and len(n1[:n]) >= 4:
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
    """题干与答案解析的匹配度（增强版：多策略）。"""
    norm_stem = normalize(paper_stem)
    combined = normalize(ans.get("anchor_stem", "")) + normalize(ans.get("explanation", ""))[:800]
    if not norm_stem or not combined:
        return 0.0

    # 策略1：题干前缀子串（从长到短）
    for n in (30, 25, 20, 15, 12, 10, 8):
        if len(norm_stem[:n]) >= 4 and norm_stem[:n] in combined:
            return 1.0

    # 策略2：题干任意位置的有意义子串（跳过前10字的引语部分）
    # 检查 stem[10:] 中的多个窗口
    best_sub = 0.0
    for start in range(0, max(1, len(norm_stem) - 12), 3):
        frag = norm_stem[start:start+12]
        if len(frag) >= 6 and frag in combined:
            best_sub = 1.0
            break
        frag8 = norm_stem[start:start+8]
        if len(frag8) >= 6 and frag8 in combined:
            best_sub = max(best_sub, 0.8)
    if best_sub >= 0.8:
        return best_sub

    # 策略3：滑动窗口字符相似度（stem 中段，避免引语）
    stem_mid = norm_stem[5:30] if len(norm_stem) > 30 else norm_stem[:20]
    best = 0.0
    if len(stem_mid) >= 4:
        step = max(1, len(stem_mid) // 2)
        for i in range(0, max(1, len(combined) - len(stem_mid)), step):
            w = combined[i : i + len(stem_mid)]
            if len(w) < 4:
                continue
            common = sum(1 for a, b in zip(stem_mid, w) if a == b)
            s = common / len(stem_mid)
            if s > best:
                best = s

    # 策略4：关键词匹配 - 从题干中提取4字以上的词，检查在combined中的命中率
    keywords = set()
    for i in range(len(norm_stem) - 3):
        kw = norm_stem[i:i+4]
        # 过滤纯数字/常见词
        if not kw.isdigit() and len(kw) == 4:
            keywords.add(kw)
    if keywords:
        hit = sum(1 for kw in keywords if kw in combined)
        kw_score = hit / len(keywords)
        if kw_score >= 0.3:
            best = max(best, kw_score * 0.9)

    # 策略5：2-gram 重叠
    if len(norm_stem) >= 6:
        bigrams = {norm_stem[i : i + 2] for i in range(min(15, len(norm_stem) - 1))}
        hit = sum(1 for g in bigrams if g in combined)
        if bigrams and hit / len(bigrams) >= 0.4:
            best = max(best, hit / len(bigrams) * 0.6)

    return best


def load_raw() -> tuple[list[dict], list[dict], list[dict]]:
    """加载 raw_2023.json，返回 (main_answers, province_diff, xzzf_diff)。"""
    data = json.loads((EXTRACT / "raw_2023.json").read_text(encoding="utf-8"))
    main = []
    p_diff = []
    x_diff = []
    for q in data:
        if q.get("diff_type") == "province_diff":
            p_diff.append(q)
        elif q.get("diff_type") == "xzzf_diff":
            x_diff.append(q)
        else:
            main.append(q)
    main.sort(key=lambda x: x["number"])
    return main, p_diff, x_diff


def load_paper(name: str) -> dict:
    return json.loads((PAPERS / f"{name}.json").read_text(encoding="utf-8"))


def all_questions(paper: dict) -> list[dict]:
    qs = []
    for s in paper["sections"]:
        qs.extend(s["questions"])
    return qs


def make_answer(q: dict, method: str = "", source: str = "") -> dict:
    return {
        "number": q["number"],
        "answer": q["answer"],
        "explanation": q.get("explanation", ""),
        "subtype": q.get("subtype"),
        "anchor_stem": q.get("anchor_stem", ""),
        "_method": method,
        "_source": source,
    }


def greedy_match(
    paper_qs: list[dict],
    answer_pool: list[dict],
    threshold: float = 0.20,
) -> tuple[list[dict], list[dict]]:
    """全局贪心匹配：计算所有分数，按分数降序分配。返回 (matched, unmatched)。"""
    used_ans: set[int] = set()
    used_q: set[int] = set()
    matched = []

    # Compute all pairwise scores
    all_scores = []
    for pq in paper_qs:
        # Combine stem + options for richer matching text
        match_text = pq.get("stem", "")
        opts = pq.get("options", {})
        if isinstance(opts, dict):
            match_text += " " + " ".join(str(v) for v in opts.values())
        elif isinstance(opts, list):
            match_text += " " + " ".join(str(v) for v in opts)

        for idx, ans in enumerate(answer_pool):
            s1 = stem_similarity(match_text, ans.get("anchor_stem", ""))
            s2 = explanation_match(match_text, ans)
            score = max(s1, s2)
            if score >= threshold * 0.5:  # pre-filter very low scores
                all_scores.append((score, pq["number"], idx))

    # Sort by score descending
    all_scores.sort(key=lambda x: -x[0])

    # Greedy assignment
    for score, qnum, ans_idx in all_scores:
        if qnum in used_q or ans_idx in used_ans:
            continue
        if score < threshold:
            break
        used_q.add(qnum)
        used_ans.add(ans_idx)
        ans = answer_pool[ans_idx]
        pq = next(q for q in paper_qs if q["number"] == qnum)
        matched.append(make_answer(
            {**pq, "answer": ans["answer"], "explanation": ans.get("explanation", ""),
             "anchor_stem": ans.get("anchor_stem", "")},
            method=f"content[{score:.2f}]",
            source=f"diff_idx{ans_idx}",
        ))

    # Find unmatched
    unmatched = []
    for pq in paper_qs:
        if pq["number"] not in used_q:
            # Find best score for this question
            best = 0.0
            match_text = pq.get("stem", "")
            opts = pq.get("options", {})
            if isinstance(opts, dict):
                match_text += " " + " ".join(str(v) for v in opts.values())
            for ans in answer_pool:
                s = max(stem_similarity(match_text, ans.get("anchor_stem", "")),
                        explanation_match(match_text, ans))
                best = max(best, s)
            unmatched.append({
                "number": pq["number"],
                "section": pq.get("section", ""),
                "stem_head": normalize(pq.get("stem", ""))[:30],
                "best_score": best,
            })

    matched.sort(key=lambda x: x["number"])
    return matched, unmatched


def main():
    print("加载原始提取...")
    main_ans, p_diff, x_diff = load_raw()
    print(f"  主卷答案: {len(main_ans)}, 省级差异题: {len(p_diff)}, 行政执法差异题: {len(x_diff)}")

    # Build main answer index
    main_by_num = {q["number"]: q for q in main_ans}

    # ── 市地：直接映射 ──
    print("\n=== 市地映射 ===")
    shidi_paper = load_paper("shidi")
    shidi_qs = all_questions(shidi_paper)
    shidi_answers = []
    shidi_missing = []
    for q in shidi_qs:
        n = q["number"]
        if n in main_by_num:
            shidi_answers.append(make_answer(main_by_num[n], method="direct"))
        else:
            shidi_missing.append(n)
    clean = [{k: v for k, v in a.items() if not k.startswith("_")} for a in shidi_answers]
    (EXTRACT / "answers_shidi.json").write_text(
        json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  → {len(shidi_answers)}/130, missing: {shidi_missing}")

    # ── 省级映射 ──
    print("\n=== 省级映射 ===")
    sj_paper = load_paper("shengji")
    sj_qs = all_questions(sj_paper)

    # a. shared → by from_number
    sj_shared = []
    sj_province_only = []
    for q in sj_qs:
        role = q.get("provenance", {}).get("role", "")
        if role == "shared":
            sj_shared.append(q)
        else:
            sj_province_only.append(q)

    sj_answers = []
    for q in sj_shared:
        from_num = q.get("provenance", {}).get("from_number")
        if from_num and from_num in main_by_num:
            sj_answers.append(make_answer(
                {**main_by_num[from_num], "number": q["number"]},
                method=f"shared_from_shidi_Q{from_num}",
            ))
        else:
            print(f"  WARNING: 省级 shared Q{q['number']} has no valid from_number={from_num}")

    print(f"  shared mapped: {len(sj_answers)}/{len(sj_shared)}")

    # b. province_only → content match to 省级差异题
    sj_po_matched, sj_po_unmatched = greedy_match(sj_province_only, p_diff, threshold=0.20)
    sj_answers.extend(sj_po_matched)

    methods = {}
    for a in sj_answers:
        m = a.get("_method", "?").split("[")[0].split("_from")[0]
        methods[m] = methods.get(m, 0) + 1
    print(f"  province_only matched: {len(sj_po_matched)}/{len(sj_province_only)}, unmatched: {len(sj_po_unmatched)}")
    print(f"  方法分布: {methods}")

    if sj_po_unmatched:
        print("  未匹配题:")
        for u in sj_po_unmatched[:10]:
            print(f"    Q{u['number']}({u['section']}): {u['stem_head']} best={u['best_score']:.2f}")

    sj_answers.sort(key=lambda x: x["number"])
    clean = [{k: v for k, v in a.items() if not k.startswith("_")} for a in sj_answers]
    (EXTRACT / "answers_shengji.json").write_text(
        json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  省级总计: {len(sj_answers)}/135")

    # ── 执法映射 ──
    print("\n=== 执法映射 ===")
    xz_paper = load_paper("xingzhengzhifa")
    xz_qs = all_questions(xz_paper)

    xz_shidi = []
    xz_shared_sj = []
    xz_diff = []
    for q in xz_qs:
        role = q.get("provenance", {}).get("role", "")
        if role == "shared_with_shidi":
            xz_shidi.append(q)
        elif role == "shared":
            xz_shared_sj.append(q)
        else:
            xz_diff.append(q)

    xz_answers = []

    # a. shared_with_shidi → by from_number
    for q in xz_shidi:
        from_num = q.get("provenance", {}).get("from_number")
        if from_num and from_num in main_by_num:
            xz_answers.append(make_answer(
                {**main_by_num[from_num], "number": q["number"]},
                method=f"shared_from_shidi_Q{from_num}",
            ))
        else:
            print(f"  WARNING: 执法 shared_with_shidi Q{q['number']} has no valid from_number={from_num}")

    print(f"  shared_with_shidi mapped: {len(xz_answers)}/{len(xz_shidi)}")

    # b. shared (with 省级) → content match to 省级差异题
    xz_sj_matched, xz_sj_unmatched = greedy_match(xz_shared_sj, p_diff, threshold=0.20)
    xz_answers.extend(xz_sj_matched)
    print(f"  shared(with 省级) matched: {len(xz_sj_matched)}/{len(xz_shared_sj)}, unmatched: {len(xz_sj_unmatched)}")

    # c. diff_book → content match to 行政执法差异题
    xz_diff_matched, xz_diff_unmatched = greedy_match(xz_diff, x_diff, threshold=0.20)
    xz_answers.extend(xz_diff_matched)
    print(f"  diff_book matched: {len(xz_diff_matched)}/{len(xz_diff)}, unmatched: {len(xz_diff_unmatched)}")

    if xz_sj_unmatched:
        print("  shared(with 省级) 未匹配:")
        for u in xz_sj_unmatched[:5]:
            print(f"    Q{u['number']}({u['section']}): {u['stem_head']} best={u['best_score']:.2f}")
    if xz_diff_unmatched:
        print("  diff_book 未匹配:")
        for u in xz_diff_unmatched[:5]:
            print(f"    Q{u['number']}({u['section']}): {u['stem_head']} best={u['best_score']:.2f}")

    xz_answers.sort(key=lambda x: x["number"])
    clean = [{k: v for k, v in a.items() if not k.startswith("_")} for a in xz_answers]
    (EXTRACT / "answers_xzzf.json").write_text(
        json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    methods = {}
    for a in xz_answers:
        m = a.get("_method", "?").split("[")[0].split("_from")[0]
        methods[m] = methods.get(m, 0) + 1
    print(f"  执法总计: {len(xz_answers)}/130, 方法: {methods}")

    # ── 未匹配报告 ──
    report = {
        "shengji_unmatched": sj_po_unmatched,
        "xingzhengzhifa_unmatched": {
            "shared_with_shengji": xz_sj_unmatched,
            "diff_book": xz_diff_unmatched,
        },
    }
    (EXTRACT / "mapping_unmatched.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n{'='*50}")
    print(f"市地: {len(shidi_answers)}/130")
    print(f"省级: {len(sj_answers)}/135 (未匹配 {len(sj_po_unmatched)})")
    print(f"执法: {len(xz_answers)}/130 (未匹配 {len(xz_sj_unmatched) + len(xz_diff_unmatched)})")


if __name__ == "__main__":
    main()
