# -*- coding: utf-8 -*-
"""
公众号封面图 · 截图导出
用 Playwright + 系统 Chrome 精确截取封面模板的 .cover 元素，导出 PNG。
默认出 2 倍高清（1800×766），符合微信封面高清规范。

用法：
  生成全部模板预览图（模板库维护用）:
    python 封面图截图.py
  单张封面 HTML → PNG（步骤5 内嵌，2 倍高清）:
    python 封面图截图.py --file "物料/.../公众号/封面图_XX.html" --out "物料/.../公众号/封面图_XX.png"
"""
from playwright.sync_api import sync_playwright
import os
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE, "..", "物料模板", "公众号封面")
TEMPLATE_DIR = os.path.abspath(TEMPLATE_DIR)
OUT_DIR = os.path.join(TEMPLATE_DIR, "预览图")
os.makedirs(OUT_DIR, exist_ok=True)

NAMES = [
    "01_中国红新闻风", "02_深红今日资讯", "03_政策解读公告",
    "04_红色资讯竖排", "05_金红头条", "06_极简大标题",
    "07_红金战报", "08_喜庆表彰", "09_几何会议", "10_商务喜报",
]

SCALE = 2  # 2 倍高清：900*2 × 383*2 = 1800×766

def shot_one(page, html_path, out_png):
    page.goto("file://" + os.path.abspath(html_path))
    page.wait_for_load_state("load")
    el = page.locator(".cover")
    el.screenshot(path=out_png)
    return out_png

def main():
    parser = argparse.ArgumentParser(description="公众号封面图截图导出")
    parser.add_argument("--file", default="", help="单个 HTML 封面文件")
    parser.add_argument("--out", default="", help="输出 PNG 路径（单文件模式必填）")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(
            viewport={"width": 900, "height": 383},
            device_scale_factor=SCALE,
        )
        if args.file:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            out = shot_one(page, args.file, os.path.abspath(args.out))
            print("截图:", os.path.basename(out))
        else:
            for i, name in enumerate(NAMES, 1):
                html_path = os.path.join(TEMPLATE_DIR, f"封面模板_{name}.html")
                out = os.path.join(OUT_DIR, f"封面_{i:02d}_{name}.png")
                shot_one(page, html_path, out)
                print("截图:", os.path.basename(out))
        browser.close()
    print("\n完成。")

if __name__ == "__main__":
    main()
