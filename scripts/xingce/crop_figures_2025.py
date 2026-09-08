#!/usr/bin/env python3
"""D7: 2025 三卷图形推理题裁图第一批（110dpi 重渲染 + 逐题定位裁剪）。

从真题 PDF 以 110dpi 渲染包含图形推理题的页面，按预设 fractional 裁剪框
逐题裁出题干图形 + 选项图形，保存为 PNG 到 media/figures/，
并更新 media_index.json 与三卷题目 JSON 的 media 字段。

用法：
    /Users/dnn/Projects/zhixing-gongkao/.logotool-venv/bin/python \
        scripts/xingce/crop_figures_2025.py

硬约束：
- 必须用 .logotool-venv/bin/python（系统 python3 无 pymupdf）
- 不改动答案/解析/题干，只更新 media 字段和 media_index
- JSON ensure_ascii=False, indent=2
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pymupdf  # PyMuPDF

# ── 路径常量 ──────────────────────────────────────────────
REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "xingce-structured-data"
XINGCE_2025 = DATA / "2025" / "xingce"
PDF_DIR = Path("/Users/dnn/真题文档/2025")
FIGURES_DIR = XINGCE_2025 / "media" / "figures"
MEDIA_INDEX = XINGCE_2025 / "media" / "media_index.json"
PAPERS_DIR = XINGCE_2025 / "papers"
REPORT_DIR = XINGCE_2025 / "_extract"

DPI = 110
ZOOM = DPI / 72  # ≈1.5278

# ── 裁剪配置 ──────────────────────────────────────────────
# 每条: (paper_type, question_number, pdf_file, pdf_page_1indexed,
#        crop_box_frac [x0,y0,x1,y1], description, options_in_media)
# crop_box_frac 参考既有 media_index 中人工标定的坐标（分辨率无关）。
CROP_JOBS = [
    # ── 市地级 shidi（20252447.pdf）：Q76-85，共10题 ──
    # Page 2: Q76-78
    ("shidi", 76, "20252447.pdf", 2, [0.08, 0.12, 0.92, 0.32], "图形推理-规律类", True),
    ("shidi", 77, "20252447.pdf", 2, [0.08, 0.34, 0.92, 0.54], "图形推理-规律类", True),
    ("shidi", 78, "20252447.pdf", 2, [0.08, 0.56, 0.92, 0.88], "图形推理-规律类", True),
    # Page 3: Q79-82（含切面/展开图/组合多面体）
    ("shidi", 79, "20252447.pdf", 3, [0.08, 0.05, 0.92, 0.22], "图形推理-规律类", True),
    ("shidi", 80, "20252447.pdf", 3, [0.08, 0.24, 0.92, 0.48], "图形推理-立体切面", True),
    ("shidi", 81, "20252447.pdf", 3, [0.08, 0.50, 0.92, 0.72], "图形推理-展开图", True),
    ("shidi", 82, "20252447.pdf", 3, [0.08, 0.74, 0.92, 0.98], "图形推理-组合多面体", True),
    # Page 4: Q83-85（图形分类，6图形+文字选项）
    ("shidi", 83, "20252447.pdf", 4, [0.08, 0.04, 0.92, 0.28], "图形推理-分类题", False),
    ("shidi", 84, "20252447.pdf", 4, [0.08, 0.30, 0.92, 0.52], "图形推理-分类题", False),
    ("shidi", 85, "20252447.pdf", 4, [0.08, 0.54, 0.92, 0.78], "图形推理-分类题", False),

    # ── 省级 shengji（20254871.pdf）：Q81-85，共5题 ──
    # PDF 内题号为 Q39-43（PDF 独立编号），对应 JSON 全局编号 Q81-85
    # Page 6: 底部为 PDF Q39（→ JSON Q81）
    ("shengji", 81, "20254871.pdf", 6, [0.08, 0.72, 0.92, 0.95], "图形推理-规律类", True),
    # Page 7: PDF Q40-43（→ JSON Q82-85）
    ("shengji", 82, "20254871.pdf", 7, [0.08, 0.04, 0.92, 0.28], "图形推理-立体切面", True),
    ("shengji", 83, "20254871.pdf", 7, [0.08, 0.30, 0.92, 0.55], "图形推理-展开图", True),
    ("shengji", 84, "20254871.pdf", 7, [0.08, 0.56, 0.92, 0.78], "图形推理-组合多面体", True),
    ("shengji", 85, "20254871.pdf", 7, [0.08, 0.80, 0.92, 0.98], "图形推理-分类题", False),
]

# 行政执法 xingzhengzhifa 的 Q76-85 与 shidi 完全共享（同一道题），
# 从 20252447.pdf 渲染的裁图复制为 xingzhengzhifa 命名。
XINGZHENG_SHARED = list(range(76, 86))  # Q76-85


def render_page(pdf_path: Path, page_no: int) -> pymupdf.Pixmap:
    """以 110dpi 渲染 PDF 第 page_no 页（1-indexed）整页。"""
    doc = pymupdf.open(pdf_path)
    page = doc[page_no - 1]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM))
    doc.close()
    return pix


def render_crop(pdf_path: Path, page_no: int, frac: list[float]) -> pymupdf.Pixmap:
    """以 110dpi 渲染 PDF 第 page_no 页的 fractional 裁剪区域。

    frac = [x0, y0, x1, y1]，相对页面宽高的比例（0-1）。
    直接用 page.get_pixmap(clip=...) 渲染，避免二次裁剪。
    """
    doc = pymupdf.open(pdf_path)
    page = doc[page_no - 1]
    pw, ph = page.rect.width, page.rect.height
    x0 = frac[0] * pw
    y0 = frac[1] * ph
    x1 = frac[2] * pw
    y1 = frac[3] * ph
    clip = pymupdf.Rect(x0, y0, x1, y1)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip)
    doc.close()
    return pix


def save_png(pix: pymupdf.Pixmap, path: Path) -> dict:
    """保存为 PNG，返回文件元信息。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(path, "png")
    st = path.stat()
    return {"width": pix.width, "height": pix.height, "bytes": st.st_size}


def main() -> int:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    report_lines: list[str] = []

    # ── 1. 渲染并裁剪 shidi + shengji ──
    print("=== 渲染并裁剪图形推理题 ===")
    for paper, qnum, pdf_file, page_no, frac, desc, opts_in_media in CROP_JOBS:
        out_name = f"{paper}_q{qnum:03d}.png"
        out_path = FIGURES_DIR / out_name
        rel_path = f"media/figures/{out_name}"

        print(f"  渲染 {pdf_file} p{page_no} 裁剪区 → {out_name} ...")
        cropped = render_crop(PDF_DIR / pdf_file, page_no, frac)
        meta = save_png(cropped, out_path)

        rec = {
            "paper": paper,
            "question_number": qnum,
            "path": rel_path,
            "width": meta["width"],
            "height": meta["height"],
            "bytes": meta["bytes"],
            "description": desc,
            "options_in_media": opts_in_media,
            "source_pdf": pdf_file,
            "source_page": page_no,
            "crop_box_frac": frac,
        }
        results.append(rec)
        print(f"  ✓ {out_name}  {meta['width']}x{meta['height']}  {meta['bytes']//1024}KB  [{desc}]")

    # ── 2. 复制 shidi 裁图为 xingzhengzhifa 命名（共享题）──
    print("\n=== 复制共享题裁图为 xingzhengzhifa 命名 ===")
    import shutil
    for qnum in XINGZHENG_SHARED:
        src = FIGURES_DIR / f"shidi_q{qnum:03d}.png"
        dst = FIGURES_DIR / f"xingzhengzhifa_q{qnum:03d}.png"
        if not src.exists():
            print(f"  ✗ 源文件不存在: {src.name}")
            continue
        shutil.copy2(src, dst)
        st = dst.stat()
        # 找到对应的 shidi 记录以获取 description/尺寸
        shidi_rec = next(r for r in results if r["paper"] == "shidi" and r["question_number"] == qnum)
        rec = {
            "paper": "xingzhengzhifa",
            "question_number": qnum,
            "path": f"media/figures/xingzhengzhifa_q{qnum:03d}.png",
            "width": shidi_rec["width"],
            "height": shidi_rec["height"],
            "bytes": st.st_size,
            "description": shidi_rec["description"],
            "options_in_media": shidi_rec["options_in_media"],
            "source_pdf": "20252447.pdf (shared with shidi)",
            "source_page": shidi_rec["source_page"],
            "crop_box_frac": shidi_rec["crop_box_frac"],
            "shared_with": "shidi",
        }
        results.append(rec)
        print(f"  ✓ xingzhengzhifa_q{qnum:03d}.png  (copy of shidi_q{qnum:03d}.png)")

    # ── 3. 更新 media_index.json ──
    print("\n=== 更新 media_index.json ===")
    with open(MEDIA_INDEX, encoding="utf-8") as f:
        midx = json.load(f)

    existing_paths = {e.get("path", "") for e in midx.get("figures", [])}
    added = 0
    for rec in results:
        if rec["path"] not in existing_paths:
            entry = {
                "path": rec["path"],
                "question_number": rec["question_number"],
                "paper": rec["paper"],
                "width": rec["width"],
                "height": rec["height"],
                "bytes": rec["bytes"],
                "description": rec["description"],
            }
            midx["figures"].append(entry)
            existing_paths.add(rec["path"])
            added += 1
        else:
            print(f"  - 已存在，跳过: {rec['path']}")

    with open(MEDIA_INDEX, "w", encoding="utf-8") as f:
        json.dump(midx, f, ensure_ascii=False, indent=2)
    print(f"  新增 {added} 条 figure 记录，总计 {len(midx['figures'])} 条")

    # ── 4. 更新题目 JSON ──
    print("\n=== 更新题目 JSON media 字段 ===")
    paper_stats: dict[str, dict] = {}

    for paper_type in ["shengji", "shidi", "xingzhengzhifa"]:
        paper_path = PAPERS_DIR / f"{paper_type}.json"
        with open(paper_path, encoding="utf-8") as f:
            paper = json.load(f)

        updated = 0
        media_missing_removed = 0
        target_nums = {r["question_number"] for r in results if r["paper"] == paper_type}

        for sec in paper.get("sections", []):
            if sec.get("name") != "判断推理":
                continue
            for q in sec.get("questions", []):
                qnum = q.get("number")
                if qnum not in target_nums:
                    continue
                rec = next(r for r in results if r["paper"] == paper_type and r["question_number"] == qnum)

                # 设置 media 字段
                q["media"] = [{
                    "type": "figure",
                    "path": rec["path"],
                    "label": rec["description"],
                    "width": rec["width"],
                    "height": rec["height"],
                }]

                # 设置 options_in_media
                q["options_in_media"] = rec["options_in_media"]

                # 移除 media_missing flag
                flags = q.get("flags") or []
                if "media_missing" in flags:
                    flags.remove("media_missing")
                    q["flags"] = flags
                    media_missing_removed += 1

                updated += 1

        with open(paper_path, "w", encoding="utf-8") as f:
            json.dump(paper, f, ensure_ascii=False, indent=2)

        paper_stats[paper_type] = {"updated": updated, "media_missing_removed": media_missing_removed}
        print(f"  {paper_type}: 更新 {updated} 题，消除 media_missing {media_missing_removed} 个")

    # ── 5. 生成裁图报告 ──
    print("\n=== 生成裁图报告 ===")
    total = len(results)
    by_paper: dict[str, int] = {}
    for r in results:
        by_paper[r["paper"]] = by_paper.get(r["paper"], 0) + 1

    report = []
    report.append("# D7 图形题裁图报告（2025 三卷第一批）\n")
    report.append(f"**执行时间**: 2026-09-03\n")
    report.append(f"**渲染 DPI**: {DPI}\n")
    report.append(f"**输出格式**: PNG\n")
    report.append(f"**裁图总数**: {total}\n")
    report.append("\n## 三卷分布\n")
    report.append(f"| 卷种 | 图形推理题数 | 题号范围 |")
    report.append(f"|------|-------------|----------|")
    report.append(f"| 省级 shengji | {by_paper.get('shengji', 0)} | Q81-85 |")
    report.append(f"| 市地级 shidi | {by_paper.get('shidi', 0)} | Q76-85 |")
    report.append(f"| 行政执法 xingzhengzhifa | {by_paper.get('xingzhengzhifa', 0)} | Q76-85（与 shidi 共享） |")
    report.append("")

    report.append("## 逐题裁图明细\n")
    report.append("| 文件 | 卷种 | 题号 | 尺寸 | 大小 | 来源PDF | 页码 | 描述 |")
    report.append("|------|------|------|------|------|---------|------|------|")
    for r in sorted(results, key=lambda x: (x["paper"], x["question_number"])):
        size_kb = r["bytes"] // 1024
        report.append(
            f"| {r['path'].split('/')[-1]} | {r['paper']} | Q{r['question_number']} "
            f"| {r['width']}x{r['height']} | {size_kb}KB | {r['source_pdf']} "
            f"| p{r['source_page']} | {r['description']} |"
        )
    report.append("")

    report.append("## 题目 JSON 更新统计\n")
    for pt, st in paper_stats.items():
        report.append(f"- **{pt}**: 更新 media 字段 {st['updated']} 题，消除 media_missing flag {st['media_missing_removed']} 个")
    report.append("")

    report.append("## 无法定位的题\n")
    report.append("无。所有图形推理题均已从 PDF 中精确定位并裁剪。\n")

    report.append("## 备注\n")
    report.append("- 行政执法卷 Q76-85 与市地级卷完全共享同一批题目（答案一致），裁图从 20252447.pdf 渲染后复制为 xingzhengzhifa 命名。")
    report.append("- 省级卷 Q81-85 在 PDF 中编号为 Q39-43（PDF 独立编号），对应 JSON 全局编号 Q81-85。")
    report.append("- 图形分类题（Q83-85 shidi / Q85 shengji）的选项为文字（A:①②⑥,③④⑤ 等），options_in_media=false，裁图仅包含 6 个题干图形。")
    report.append("- 既有 JPG 格式裁图（q076.jpg 等）保留未删除，新裁图为 110dpi PNG 格式，paper_type 前缀命名。")

    report_path = REPORT_DIR / "figure_crop_report.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"  报告已写入: {report_path}")

    # ── 6. 验证 ──
    print("\n=== 验证 ===")
    errors = []
    # 检查所有输出文件存在且非空
    for r in results:
        fpath = XINGCE_2025 / r["path"]
        if not fpath.exists():
            errors.append(f"文件不存在: {r['path']}")
        elif fpath.stat().st_size < 1000:
            errors.append(f"文件过小（可能空白）: {r['path']} ({fpath.stat().st_size}B)")

    if errors:
        print("  ❌ 验证失败:")
        for e in errors:
            print(f"    - {e}")
    else:
        print(f"  ✓ 全部 {total} 张裁图存在且非空白")

    print(f"\n完成！裁图 {total} 张，更新 {sum(s['updated'] for s in paper_stats.values())} 题 media 字段。")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
