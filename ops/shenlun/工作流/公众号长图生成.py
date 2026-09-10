# -*- coding: utf-8 -*-
"""
公众号长图生成器（方案A · 长图发布 · v2.18 平行产出增强）
【v2.18 增强（2026-09-05，向后兼容）】v2.18 公众号 HTML 含 8 个 h2（考题定位/骨架/规范词/
论证/语录/句式/迁移/速记），原 4 片切点会让末片塞 6 个区块（实测 536 万像素逼近微信
600 万上限）；新增 n>=8 分支均衡切点：头部+立意 / 规范词+论证 / 语录+句式 / 迁移+速记+行动
（实测 156~246 万像素/片）。旧 6 h2 HTML 走原切点，行为不变。
将公众号 HTML 渲染成手机宽度长图（100% 还原样式，微信编辑器无法剥离图片样式）。
「原文链接」文字与「往期回顾」区块（上一篇/下一篇）不进长图（图片内不可点击），
并在渲染时剔除；输出 `原文链接.txt`（原文 URL，供公众号后台「原文链接」字段填写，
2026-08-29 用户定：发布文本.md 取消，正文下方不再放出处/往期）。

用法：
  python 公众号长图生成.py <文章标题> --date 2026-08-28 [--width 375] [--scale 2]
  # 输入：物料/<date>/<文章标题>/公众号/<标题>_公众号.html
  # 输出：物料/<date>/<文章标题>/公众号/发布长图_<标题>.png
  #      物料/<date>/<文章标题>/公众号/原文链接.txt
"""
import os, sys, argparse, re
from playwright.sync_api import sync_playwright
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, ".."))

def extract_prevnext(html_path):
    """从 HTML 中提取「往期回顾」区块文本（上一篇/下一篇），供长图下方单独贴文本"""
    html = open(html_path, encoding="utf-8").read()
    m = re.search(r'<!-- 往期回顾 -->(.*?)</p>\s*</div>', html, re.S)
    texts = []
    if m:
        seg = m.group(1)
        # 提取 <a> 链接文本
        for a in re.findall(r'<a[^>]*>(.*?)</a>', seg, re.S):
            t = re.sub(r'<[^>]+>', '', a).strip()
            if t:
                texts.append(t)
    return texts

def extract_source_info(html_path, title):
    """提取原文出处信息（标题/落款版次日期/链接），供长图下方「原文出处」引用块"""
    html = open(html_path, encoding="utf-8").read()
    link = ""
    m = re.search(r'<a href="(http[^"]*)"[^>]*>.*?点击查看人民日报原文</a>', html, re.S)
    if m:
        link = m.group(1)
    credit = ""
    m = re.search(r'——人民日报\s*([^<\s]+(?:\s*[^<\s]+)*)', html)
    if m:
        credit = m.group(1).strip()
    # 栏目：从标题括号提取（如 《xx（“三农”观察）》）
    col = ""
    m = re.search(r'（(.+?)）', title)
    if m:
        col = m.group(1)
    return {"title": title, "credit": credit, "link": link, "column": col}

def build_long_image(html_path, out_png, width=375, scale=2, segment=True):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(
            viewport={"width": width, "height": 800},
            device_scale_factor=scale,
        )
        # 注入：移除「原文链接」文字（链接进图=图片不可点击，须剔除，留到下方文本区）+「往期回顾」区块
        page.goto("file://" + os.path.abspath(html_path))
        page.wait_for_load_state("load")
        page.evaluate("""() => {
            // 1) 剔除「点击查看人民日报原文」链接元素（连同其前导 <br>，避免留空行）
            document.querySelectorAll('a').forEach(a => {
                if (/点击查看人民日报原文/.test(a.textContent)) {
                    let n = a.previousSibling;
                    while (n) {
                        if (n.nodeType === 1 && n.tagName === 'BR') { n.remove(); break; }
                        if (n.nodeType === 3 && n.textContent.trim() === '') { n = n.previousSibling; continue; }
                        break;
                    }
                    a.remove();
                }
            });
            // 2) 删除「往期回顾」区块（上一篇/下一篇，不进长图）
            document.querySelectorAll('p').forEach(p => {
                if (/上一篇/.test(p.textContent) || /下一篇预告/.test(p.textContent)) p.remove();
            });
        }""")
        # 读取 h2 章节边界 Y 坐标（CSS 像素，scale 前），用于分段裁剪
        tops = page.evaluate("""() => Array.from(document.querySelectorAll('h2')).map(h => Math.round(h.getBoundingClientRect().top + window.scrollY))""")
        # 全页截图（整图，保留）
        page.screenshot(path=out_png, full_page=True)
        browser.close()

    if not segment:
        return True

    # PIL 按章节切 4 段：头部 / 骨架+规范词 / 论证骨架(单独) / 句式+速记
    # 论证骨架是内容最重的章节，单独成一张，避免某张过高（章节不足时退化为尽量均匀）
    im = Image.open(out_png)
    W, H = im.size

    def c(y):
        return max(0, min(H, int(round(y * scale))))

    n = len(tops)
    if n >= 8:
        # v2.18 平行产出：8 个 h2 场景均衡 4 片（头部+立意 / 规范词+论证 / 语录+句式 / 迁移+速记+行动）
        segs = [(0, tops[2]), (tops[2], tops[4]), (tops[4], tops[6]), (tops[6], None)]
    elif n >= 5:
        segs = [(0, tops[0]), (tops[0], tops[2]), (tops[2], tops[3]), (tops[3], None)]
    elif n >= 3:
        segs = [(0, tops[0]), (tops[0], tops[1]), (tops[1], tops[-1]), (tops[-1], None)]
    elif n >= 1:
        segs = [(0, tops[0]), (tops[0], None), (None, None), (None, None)]
    else:
        segs = [(0, None), (None, None), (None, None), (None, None)]

    for i, (a, b) in enumerate(segs):
        y0 = c(a if a is not None else 0)
        y1 = H if b is None else c(b)
        if y1 - y0 < 5:  # 跳过空段（兜底场景）
            continue
        seg = im.crop((0, y0, W, y1))
        seg_png = out_png.replace(".png", f"_{i+1:02d}.png")
        seg.save(seg_png)
        print(f"✅ 分片{i+1}: {os.path.basename(seg_png)} ({W}x{y1-y0}px)")
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("title", help="文章标题")
    ap.add_argument("--date", default="")
    ap.add_argument("--width", type=int, default=375)
    ap.add_argument("--scale", type=int, default=2)
    a = ap.parse_args()

    if a.date:
        art_dir = os.path.join(ROOT, "物料", a.date, a.title)
    else:
        # 无日期则取最新物料目录下的同名文章
        dates = sorted([d for d in os.listdir(os.path.join(ROOT, "物料")) if d.startswith("20")], reverse=True)
        art_dir = None
        for d in dates:
            cand = os.path.join(ROOT, "物料", d, a.title)
            if os.path.isdir(cand):
                art_dir = cand
                a.date = d
                break
    if not art_dir or not os.path.isdir(art_dir):
        print("❌ 未找到文章目录:", a.title); return 1

    gzh_dir = os.path.join(art_dir, "公众号")
    html_candidates = [f for f in os.listdir(gzh_dir) if f.endswith(".html") and "备选" not in f] if os.path.isdir(gzh_dir) else []
    if not html_candidates:
        print("❌ 未找到公众号 HTML"); return 1
    html_path = os.path.join(gzh_dir, html_candidates[0])

    out_png = os.path.join(gzh_dir, f"发布长图_{a.title}.png")
    build_long_image(html_path, out_png, a.width, a.scale)

    # 原文链接（公众号后台「原文链接」字段用，2026-08-29 用户定：发布文本.md 取消）
    src = extract_source_info(html_path, a.title)
    out_txt = os.path.join(gzh_dir, "原文链接.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(src["link"] + "\n")
        if src["credit"]:
            f.write(f"# 原文：人民日报 {src['credit']}《{src['title']}》\n")
    print(f"✅ 长图: {out_png}")
    print(f"✅ 原文链接: {out_txt}  {src['link']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
