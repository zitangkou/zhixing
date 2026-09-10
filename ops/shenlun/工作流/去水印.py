#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
去水印 v1.0 —— 页脚品牌条覆盖（无成本 / 不损质量 / 自动化）

背景：Canva generate-design 下载的图带「包含AI生成」水印（底部角落）。
方案：在图片底部叠加一条与复古油墨风融合的「页脚品牌条」，
     既覆盖水印，又成为品牌装饰（报纸页脚基因），不裁剪、不降质、不新增 AI 生成内容。

用法：
    python3 工作流/去水印.py <图片或目录> [--text "三刀解剖法 · 每天拆一篇人民日报"] [--issue 第001期] [--out 输出目录]

自适应：按图片底部亮度自动选配色（底部浅→深墨条+米白字；底部深→米白条+深墨字；中间→半透明深条+白字）
可读性：条带内文字与条带背景强对比（符合可读性铁律）
"""
import os, sys, argparse
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/System/Library/Fonts/Supplemental/Songti.ttc"
BAR_HEIGHT_RATIO = 0.062          # 条带高度 ≈ 画布高 6%
BAR_FALLBACK = 0.0                # 若底部太浅/太深，条带贴底；不偏移
MIN_BAR_H = 80

def load_font(size, index=0):
    for idx in (index, 0):
        try:
            return ImageFont.truetype(FONT_PATH, size, index=idx)
        except Exception:
            continue
    # 兜底：系统黑体
    try:
        return ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", size)
    except Exception:
        return ImageFont.load_default()

def pick_bar_color(img, bar_h):
    """按底部区域亮度选条带配色（前景=文字色, 背景=条带色, 线=分隔线色）"""
    w, h = img.size
    region = img.convert("L").crop((0, h - bar_h, w, h))
    px = list(region.get_flattened_data() if hasattr(region, "get_flattened_data") else region.getdata())
    mean = sum(px) / len(px)
    if mean > 150:      # 底部偏亮 → 深墨条 + 米白字
        return dict(bg=(26, 26, 26, 255), fg=(243, 234, 211, 255), line=(184, 134, 11, 255), name="深墨条/米白字")
    if mean < 80:       # 底部偏暗 → 米白条 + 深墨字
        return dict(bg=(243, 234, 211, 255), fg=(26, 26, 26, 255), line=(184, 134, 11, 255), name="米白条/深墨字")
    # 中间 → 半透明深条 + 白字（覆盖更干净）
    return dict(bg=(26, 26, 26, 200), fg=(255, 252, 245, 255), line=(200, 160, 60, 255), name="半透明深条/白字")

def process(img_path, text="三刀解剖法 · 每天拆一篇人民日报", issue="", out_path=None):
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    bar_h = max(MIN_BAR_H, int(h * BAR_HEIGHT_RATIO))
    c = pick_bar_color(img, bar_h)
    # 底部叠加条带
    overlay = Image.new("RGBA", (w, bar_h), c["bg"])
    img.paste(overlay, (0, h - bar_h), overlay)
    # 顶部细线（报纸栏线）
    d = ImageDraw.Draw(img)
    d.line([(0, h - bar_h), (w, h - bar_h)], fill=c["line"], width=3)
    # 文字
    fs_main = max(24, int(bar_h * 0.34))
    fs_issue = max(22, int(bar_h * 0.30))
    f_main = load_font(fs_main)
    f_issue = load_font(fs_issue)
    pad = 28
    d.text((pad, h - bar_h + (bar_h - fs_main) / 2 - 2), text, font=f_main, fill=c["fg"])
    if issue:
        # 右对齐期号
        tw = d.textlength(issue, font=f_issue)
        d.text((w - pad - tw, h - bar_h + (bar_h - fs_issue) / 2 - 2), issue, font=f_issue, fill=c["fg"])
    if out_path is None:
        out_path = img_path
    img.save(out_path, "PNG")
    return c["name"], bar_h

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="图片或目录")
    ap.add_argument("--text", default="三刀解剖法 · 每天拆一篇人民日报")
    ap.add_argument("--issue", default="")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if os.path.isdir(a.target):
        files = []
        for root, _, fs in os.walk(a.target):
            for f in sorted(fs):
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    files.append(os.path.join(root, f))
    else:
        files = [a.target]
    if not files:
        print("未找到图片"); return 1
    for f in files:
        out = None
        if a.out:
            os.makedirs(a.out, exist_ok=True)
            out = os.path.join(a.out, os.path.basename(f))
        try:
            name, bar_h = process(f, text=a.text, issue=a.issue, out_path=out)
            print(f"✅ {os.path.basename(f)}  条带{bar_h}px（{name}）")
        except Exception as e:
            print(f"❌ {os.path.basename(f)}: {e}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
