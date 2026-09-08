#!/usr/bin/env python3
"""扫描 PDF 页面渲染（PyMuPDF，不依赖 poppler）。

为 WORKFLOW §4 步骤 2 提供固定参数的渲染入口：
- 结构浏览档 scan：40 dpi，快速翻页确认模块边界与 PDF 角色
- 精读裁图档 hi  ：110 dpi，提取题干与裁剪图形

用法：
    python3 scripts/xingce/render_pdf.py ~/真题文档/2023/20230124.pdf --pages 1-6
    python3 scripts/xingce/render_pdf.py xxx.pdf --pages 10-15 --dpi hi --out /tmp/r
    python3 scripts/xingce/render_pdf.py xxx.pdf --info          # 只看页数与尺寸
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pymupdf

DPI_PRESETS = {"scan": 40, "mid": 72, "hi": 110}


def parse_range(spec: str, max_page: int) -> list[int]:
    if spec == "all":
        return list(range(1, max_page + 1))
    pages: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(part))
    bad = [p for p in pages if not 1 <= p <= max_page]
    if bad:
        sys.exit(f"页码超出范围 1–{max_page}: {bad}")
    return sorted(set(pages))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--pages", default="1-4", help="如 1-6 / 3,7,9 / all")
    ap.add_argument("--dpi", choices=list(DPI_PRESETS), default="scan",
                    help="scan=40 结构浏览 / mid=72 / hi=110 精读裁图")
    ap.add_argument("--out", type=Path, default=None, help="输出目录（默认 /tmp/render/{pdf名}/）")
    ap.add_argument("--info", action="store_true", help="只显示页数与页面尺寸")
    args = ap.parse_args()

    doc = pymupdf.open(args.pdf)
    if args.info:
        p0 = doc[0]
        print(f"{args.pdf.name}: {doc.page_count} 页 | 首页 {p0.rect.width:.0f}x{p0.rect.height:.0f} pt")
        print(f"  文字层: {'有' if p0.get_text().strip() else '无（扫描件，走渲染+视觉阅读）'}")
        return 0

    out = args.out or Path(f"/tmp/render/{args.pdf.stem}")
    out.mkdir(parents=True, exist_ok=True)
    dpi = DPI_PRESETS[args.dpi]
    zoom = dpi / 72

    for page_no in parse_range(args.pages, doc.page_count):
        page = doc[page_no - 1]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        f = out / f"p{page_no:03d}_{args.dpi}.png"
        pix.save(f)
        print(f"  {f}  ({pix.width}x{pix.height})")
    print(f"渲染完成：{len(parse_range(args.pages, doc.page_count))} 页 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
