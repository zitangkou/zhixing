#!/usr/bin/env python3
"""答案合并脚本：锚点校验 → 写入 papers → 覆盖率报告。

用法：
    python3 scripts/merge_answers.py --year 2025
    python3 scripts/merge_answers.py --year 2025 --dry-run   # 只校验不写入
    python3 scripts/merge_answers.py --year 2022 --answer-source answer_book_2026-09

自动检测 papers/ 目录下的卷种（shidi/shengji/xingzhengzhifa），
读取对应 _extract/answers_{shidi,shengji,xzzf}.json，逐题：
  1. 答案格式校验（单选∈options键、多选≥2升序、判断∈{正确,错误}）
  2. 锚点校验（题干归一化后与解析模糊比对）
  3. 写入 answer/explanation/answer_source/subtype，清 answer_missing flag
  4. 输出覆盖率报告 + pending_review 清单（dry-run 模式不写报告文件）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "xingce-structured-data"
DEFAULT_ANSWER_SOURCE = "answer_book_2026-09"

# 卷种名 → 答案文件名约定
ANSWER_FILE_MAP = {
    "shidi": "answers_shidi.json",
    "shengji": "answers_shengji.json",
    "xingzhengzhifa": "answers_xzzf.json",
}

# ── 文本归一化 ──────────────────────────────────────────────
_PUNCT_RE = re.compile(
    r"[\s，。、；：？！…—·\"\"''（）《》【】〈〉「」『』"
    r"\-\.,;:!?\(\)\[\]{}\"'<>/\\|~`@#\$%\^&\*_=\+]"
)


def normalize(text: str) -> str:
    """移除所有标点空格，返回纯文本串。"""
    if not text:
        return ""
    return _PUNCT_RE.sub("", str(text))


# ── 锚点校验 ────────────────────────────────────────────────
def anchor_match(
    paper_stem: str,
    anchor_stem: str,
    explanation: str,
    threshold: float = 0.35,
) -> tuple[bool, float, str]:
    """模糊锚点校验。

    策略（逐级放宽）：
      1. 题干前 N 字（归一化）是否出现在 anchor 或 explanation 中（N=20/15/12/8）
      2. 题干前 20 字与 explanation 滑动窗口的字符级相似度 ≥ threshold
      3. 题干关键词（前4个2-gram）是否有 ≥2 个出现在 explanation 中

    返回 (matched, score, detail)。
    """
    norm_stem = normalize(paper_stem)
    norm_anchor = normalize(anchor_stem)
    norm_expl = normalize(explanation)[:500]

    if not norm_stem:
        return False, 0.0, "paper stem empty"
    if not norm_expl and not norm_anchor:
        return False, 0.0, "explanation empty"

    combined = norm_anchor + norm_expl

    # 策略1：题干前缀子串匹配
    for n in (20, 15, 12, 8):
        frag = norm_stem[:n]
        if len(frag) >= 4 and frag in combined:
            return True, 1.0, f"stem[:{n}] substring match"

    # 策略2：滑动窗口字符相似度
    stem20 = norm_stem[:20]
    best_score = 0.0
    if len(stem20) >= 4 and combined:
        step = max(1, len(stem20) // 2)
        for i in range(0, max(1, len(combined) - len(stem20)), step):
            window = combined[i : i + len(stem20)]
            if len(window) < 4:
                continue
            common = sum(1 for a, b in zip(stem20, window) if a == b)
            score = common / len(stem20)
            if score > best_score:
                best_score = score
        if best_score >= threshold:
            return True, best_score, f"sliding similarity={best_score:.2f}"

    # 策略3：关键词 2-gram 重叠
    if len(norm_stem) >= 6:
        bigrams = {norm_stem[i : i + 2] for i in range(min(8, len(norm_stem) - 1))}
        hit = sum(1 for g in bigrams if g in combined)
        if bigrams and hit / len(bigrams) >= 0.4:
            return True, hit / len(bigrams), f"bigram overlap={hit}/{len(bigrams)}"

    return False, best_score, f"best similarity={best_score:.2f} below threshold"


# ── 答案校验 ────────────────────────────────────────────────
def validate_answer(answer: str, question: dict) -> tuple[bool, str]:
    """校验答案合法性。返回 (valid, detail)。"""
    if not answer or not str(answer).strip():
        return False, "empty answer"

    answer = str(answer).strip()
    options = question.get("options")

    # 判断题
    if answer in ("正确", "错误"):
        return True, "judgment"

    # 图形题 options=None / options_in_media=True
    if options is None:
        if re.fullmatch(r"[A-D]+", answer):
            return True, "graph_question"
        return False, f"invalid answer for graph question: {answer!r}"

    # 有 options dict 的题
    if isinstance(options, dict):
        valid_keys = set(options.keys())
        letters = list(answer)
        if not all(c in valid_keys for c in letters):
            return False, f"answer contains letters not in options keys: {answer!r}"
        if len(letters) == 1:
            return True, "single_choice"
        if len(letters) >= 2:
            if letters != sorted(letters):
                return False, f"multi-select answer not in ascending order: {answer!r}"
            return True, f"multi_select_{len(letters)}"
        return False, f"answer has zero letters: {answer!r}"

    return False, f"unknown options type: {type(options).__name__}"


# ── 主流程 ──────────────────────────────────────────────────
def merge_paper(
    paper_name: str,
    answer_file: str,
    base: Path,
    dry_run: bool,
    answer_source: str = DEFAULT_ANSWER_SOURCE,
) -> dict:
    """合并单卷答案。返回统计 dict。"""
    paper_path = base / "papers" / f"{paper_name}.json"
    answer_path = base / "_extract" / answer_file

    result = {
        "paper": paper_name,
        "total": 0,
        "answered": 0,
        "pending": 0,
        "rejected": 0,
        "coverage": "",
        "pending_list": [],
    }

    if not answer_path.exists():
        result["error"] = f"answer file not found: {answer_path}"
        return result

    paper = json.loads(paper_path.read_text(encoding="utf-8"))
    answers = json.loads(answer_path.read_text(encoding="utf-8"))
    # 兼容两种格式：直接 list 或 {"questions": [...]}
    if isinstance(answers, dict) and "questions" in answers:
        answers = answers["questions"]

    # 题号索引
    q_by_num: dict[int, dict] = {}
    for s in paper["sections"]:
        for q in s["questions"]:
            q_by_num[q["number"]] = q

    total = len(q_by_num)
    result["total"] = total

    for ans in answers:
        num = ans.get("number")
        if num is None or num not in q_by_num:
            result["rejected"] += 1
            result["pending_list"].append(
                {"number": num, "reason": "question number not found in paper"}
            )
            continue

        q = q_by_num[num]

        # 1. 答案格式校验
        valid, vdetail = validate_answer(ans.get("answer", ""), q)
        if not valid:
            result["rejected"] += 1
            result["pending_list"].append(
                {
                    "number": num,
                    "reason": f"answer validation failed: {vdetail}",
                    "answer": ans.get("answer"),
                }
            )
            continue

        # 2. 锚点校验
        matched, score, adetail = anchor_match(
            q.get("stem", ""),
            ans.get("anchor_stem", ""),
            ans.get("explanation", ""),
        )

        if not matched:
            result["pending"] += 1
            result["pending_list"].append(
                {
                    "number": num,
                    "reason": f"anchor mismatch: {adetail}",
                    "answer": ans.get("answer"),
                    "paper_stem_head": normalize(q.get("stem", ""))[:25],
                    "anchor_head": normalize(ans.get("anchor_stem", ""))[:25],
                }
            )
            # 锚点不匹配仍写入（题号映射可信），但标记待复核
            # 若需严格拒绝，取消下面注释
            # continue

        # 3. 写入
        q["answer"] = ans["answer"]
        q["explanation"] = ans.get("explanation", "")
        q["answer_source"] = answer_source
        if ans.get("subtype"):
            q["subtype"] = ans["subtype"]

        # flags 管理
        flags = set(q.get("flags") or [])
        flags.discard("answer_missing")
        if not matched:
            flags.add("anchor_pending")
        q["flags"] = sorted(flags)

        result["answered"] += 1

    # 4. 保存
    if not dry_run:
        paper_path.write_text(
            json.dumps(paper, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    result["coverage"] = (
        f"{result['answered']}/{total} "
        f"({result['answered'] / total * 100:.1f}%)"
        if total
        else "N/A"
    )
    return result


def detect_papers(base: Path) -> dict[str, str]:
    """自动检测 papers/ 目录下存在的卷种，返回 {paper_name: answer_file}。"""
    papers_dir = base / "papers"
    if not papers_dir.exists():
        return {}
    found = {}
    for pname in ANSWER_FILE_MAP:
        if (papers_dir / f"{pname}.json").exists():
            found[pname] = ANSWER_FILE_MAP[pname]
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="合并行测真题答案到 papers")
    parser.add_argument("--year", type=str, default="2025", help="考试年份")
    parser.add_argument(
        "--dry-run", action="store_true", help="只校验不写入文件"
    )
    parser.add_argument(
        "--answer-source",
        type=str,
        default=DEFAULT_ANSWER_SOURCE,
        help=f"答案来源标记（默认 {DEFAULT_ANSWER_SOURCE}）",
    )
    args = parser.parse_args()

    base = DATA / args.year / "xingce"
    if not base.exists():
        print(f"ERROR: year directory not found: {base}", file=sys.stderr)
        sys.exit(1)

    # 自动检测卷种（兼容 2 卷/3 卷年份）
    paper_files = detect_papers(base)
    if not paper_files:
        print(f"ERROR: no paper files found in {base / 'papers'}", file=sys.stderr)
        sys.exit(1)

    print(f"{'[DRY-RUN] ' if args.dry_run else ''}合并 {args.year} 行测答案")
    print(f"  检测到卷种: {', '.join(paper_files.keys())}")
    print(f"  答案来源: {args.answer_source}\n")

    all_pending = []
    total_q = 0
    total_ans = 0
    report = {"year": args.year, "dry_run": args.dry_run, "papers": {}}

    for paper_name, answer_file in paper_files.items():
        r = merge_paper(paper_name, answer_file, base, args.dry_run, args.answer_source)
        report["papers"][paper_name] = {
            k: v for k, v in r.items() if k != "pending_list"
        }
        total_q += r["total"]
        total_ans += r["answered"]
        for p in r["pending_list"]:
            p["paper"] = paper_name
            all_pending.append(p)

        status = r.get("error", f"{r['coverage']}  pending={r['pending']} rejected={r['rejected']}")
        print(f"  {paper_name:16s}: {status}")

    report["total_questions"] = total_q
    report["total_answered"] = total_ans
    report["total_coverage"] = (
        f"{total_ans}/{total_q} ({total_ans / total_q * 100:.1f}%)"
        if total_q
        else "N/A"
    )
    report["pending_review"] = all_pending

    print(f"\n  总计覆盖率: {report['total_coverage']}")
    print(f"  待复核项: {len(all_pending)}")
    for p in all_pending:
        print(f"    [{p['paper']}] Q{p['number']}: {p['reason']}")

    # dry-run 不写报告文件，避免污染 _extract/ 目录
    if not args.dry_run:
        report_path = base / "_extract" / "merge_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n  报告已写入: {report_path}")
    else:
        print("\n  [DRY-RUN] 未写入报告文件")


if __name__ == "__main__":
    main()
