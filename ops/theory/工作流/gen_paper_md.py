#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_paper_md.py — 单篇文章题目JSON → 后台导入格式套题MD

把一篇理论文章的 20题.json 转为 zhixing 后台可导入的套题 MD 文档
（parse_questions_markdown 格式：题干 **粗体** + A．B．C．D．选项 +
> **答案：** / > **原文依据：** / > **解析：** / > **技巧点拨：**）。

用法:
  python3 gen_paper_md.py --date YYYY-MM-DD --title "文章标题"
  python3 gen_paper_md.py --json <题目.json路径> [--title 标题]

输出: 文章目录/题目/人民日报<date>_<title>_20题_后台导入.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ICLOUD_ROOT = Path("/Users/dnn/Library/Mobile Documents/com~apple~CloudDocs/政治理论")


def flatten(s) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def tip_from_distractors(ds) -> str:
    if not ds:
        return ""
    parts = []
    for d in ds:
        t = d.get("type", "") if isinstance(d, dict) else ""
        ep = d.get("error_path", "") if isinstance(d, dict) else ""
        parts.append(f"{t}（{ep}）" if ep else t)
    return "；".join(parts)


def gen_md(meta: dict, questions: list[dict]) -> str:
    td = meta["type_distribution"]
    lines = [
        f"# {meta['title']}",
        "",
        f"> **来源：** {meta['source_ref']}",
        f"> **题量：** {meta['total']} 题（直接判断 {td.get('直接判断', 0)} / 组合题 {td.get('组合题', 0)} / 计数题 {td.get('计数题', 0)}）",
        f"> **价值分：** {meta['value_score']}/100（{meta['value_label']}）",
        f"> **原文链接：** {meta['material_anchor']}",
        f"> **说明：** 由本篇理论文章 20 题生成，可直接粘贴至管理后台「文章题目导入」。",
        "",
        "---",
        "",
        f"## 第一部分：单选题（共 {meta['total']} 题）",
        "",
    ]
    for i, q in enumerate(questions, 1):
        lines.append(f"**{i}. {flatten(q['stem'])}**")
        lines.append("")
        for k in ("A", "B", "C", "D"):
            if k in q.get("options", {}):
                lines.append(f"{k}．{q['options'][k]}")
        lines.append("")
        lines.append(f"> **答案：{q['answer']}**")
        src = flatten(q.get("source_ref"))
        if src:
            lines.append(f"> **原文依据：** {src}")
        ana = flatten(q.get("explanation"))
        if ana:
            lines.append(f"> **解析：** {ana}")
        tip = tip_from_distractors(q.get("distractors"))
        if tip:
            lines.append(f"> **技巧点拨：** {tip}")
        lines += ["", "---", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="单篇文章题目JSON → 后台导入格式套题MD")
    ap.add_argument("--date", default="", help="日期 YYYY-MM-DD（与 --title 联用自动定位文章目录）")
    ap.add_argument("--title", default="", help="文章标题")
    ap.add_argument("--json", default="", help="题目JSON路径（优先级最高）")
    args = ap.parse_args()

    if args.json:
        json_path = Path(args.json)
    elif args.date and args.title:
        base = ICLOUD_ROOT / "物料"
        matches = sorted(base.glob(f"{args.date}_*"))
        if not matches:
            print(f"❌ 未找到文章目录: 物料/{args.date}_*")
            sys.exit(1)
        date_dir = matches[0]
        json_path = date_dir / "题目" / f"人民日报{args.date}_{args.title}_20题.json"
        if not json_path.exists():
            # 标题可能不含标点，尝试模糊匹配
            cands = sorted((date_dir / "题目").glob(f"人民日报{args.date}_*_20题.json"))
            if not cands:
                print(f"❌ 题目JSON不存在: {json_path}")
                sys.exit(1)
            json_path = cands[0]
    else:
        print("❌ 需提供 --json，或 --date + --title")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    questions = data["questions"]
    td = Counter(q.get("subtype", "直接判断") for q in questions)
    vs = data.get("value_score", 92)
    value_score = vs.get("total", 92) if isinstance(vs, dict) else (vs if isinstance(vs, (int, float)) else 92)
    date_str = args.date or (json_path.parent.parent.name[:10] if len(json_path.parent.parent.name) >= 10 else "")
    title = args.title or data.get("article", "") or json_path.stem
    meta = {
        "title": f"《{title}》政治理论 20 题",
        "source_ref": data.get("source", "人民日报"),
        "total": len(questions),
        "type_distribution": dict(td),
        "value_score": value_score,
        "value_label": data.get("value_label", ""),
        "material_anchor": data.get("material_anchor", ""),
    }
    md = gen_md(meta, questions)
    out_path = json_path.parent / f"{json_path.stem}_后台导入.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"✅ 套题MD已生成: {out_path} ({len(md)/1024:.0f}KB, {len(questions)}题)")


if __name__ == "__main__":
    main()
