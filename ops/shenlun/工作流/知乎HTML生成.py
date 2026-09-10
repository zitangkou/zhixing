# -*- coding: utf-8 -*-
"""
知乎 HTML 生成器

以公众号 HTML（A 套）为底，补充两处（2026-09-04 用户定）：
  1. 来源引用卡：去掉顶部开篇引导区里那行弱化的「📄 点击查看人民日报原文」文字链接，
     改为文末一张灰底「本文来源」引用卡（人民日报 版次日期《标题》 + 红色可点原文链接）。
  2. 上一篇/下一篇导航：文末追加相邻文章标题文字 + 占位链接（href="#"），
     发布知乎后由用户手动替换为真实知乎链接。

上一篇/下一篇判定：扫描 物料/ 下全部标准日期目录（YYYY-MM-DD），按日期排序、
同日按 状态.json 的 selected_articles 顺序，拼成全局系列，取目标文章的前/后一篇。

用法：
  python 知乎HTML生成.py --date 2026-09-04            # 处理当天全部文章（读状态.json）
  python 知乎HTML生成.py <文章标题> --date 2026-09-04  # 只处理单篇

输入：物料/<日期>/<文章>/公众号/<标题>_公众号.html（A 套，排除「备选」）
输出：物料/<日期>/<文章>/知乎/<标题>_知乎.html
"""
import os
import re
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def find_gzh_html(art_dir):
    """定位公众号 A 套 HTML（排除备选手账）。"""
    gzh = os.path.join(art_dir, "公众号")
    if not os.path.isdir(gzh):
        return None
    for f in sorted(os.listdir(gzh)):
        if f.endswith(".html") and "备选" not in f:
            return os.path.join(gzh, f)
    return None


def extract_source(html):
    """提取原文 URL 与版次日期落款。"""
    url = ""
    m = re.search(r'<a href="(http[^"]*)"[^>]*>.*?点击查看人民日报原文</a>', html, re.S)
    if m:
        url = m.group(1)
    credit = ""
    m = re.search(r'——人民日报\s*([^<]+)', html)
    if m:
        credit = m.group(1).strip()
    return url, credit


def scan_articles(ddir):
    """扫描某日期目录下的文章目录标题（回退用）。
    口径与规则自检一致：仅收录含 解剖/公众号/小红书/知乎/抖音 任一子目录的一级目录，
    排除早期日级直挂平台目录（如 2026-08-26 的 小红书/抖音）被误当文章名。"""
    out = []
    for name in sorted(os.listdir(ddir)):
        p = os.path.join(ddir, name)
        if os.path.isdir(p) and name not in ("原文", "筛选"):
            if any(os.path.isdir(os.path.join(p, s)) for s in ("解剖", "公众号", "小红书", "知乎", "抖音")):
                out.append(name)
    return out


def collect_all_articles():
    """扫描物料目录，返回按时间排序的全局系列 [(date, title), ...]。"""
    seq = []
    wl = os.path.join(ROOT, "物料")
    if not os.path.isdir(wl):
        return seq
    # -v18 平行目录也纳入全局序列（排序在其主日期之后），保证仅存在于 -v18 的追加文章能正确取上一篇/下一篇
    dates = sorted(d for d in os.listdir(wl) if re.match(r'^\d{4}-\d{2}-\d{2}(-v18)?$', d))
    for d in dates:
        ddir = os.path.join(wl, d)
        titles = []
        sj = os.path.join(ddir, "状态.json")
        if os.path.exists(sj):
            try:
                with open(sj, encoding="utf-8") as f:
                    data = json.load(f)
                titles = (data.get("selected_articles")
                          or data.get("source_selected_articles") or [])
            except Exception:
                titles = []
        if not titles:
            titles = scan_articles(ddir)
        for t in titles:
            seq.append((d, t))
    return seq


def build_prevnext(seq, cur_date, cur_title):
    prev_title = None
    next_title = None
    # 优先精确匹配（含 -v18 后缀），回退到归一化主日期（兼容双目录同文）
    candidates = [cur_date]
    norm = cur_date.replace('-v18', '')
    if norm not in candidates:
        candidates.append(norm)
    for cd in candidates:
        for i, (d, t) in enumerate(seq):
            if d == cd and t == cur_title:
                if i > 0:
                    prev_title = seq[i - 1][1]
                if i < len(seq) - 1:
                    next_title = seq[i + 1][1]
                return prev_title, next_title
    return prev_title, next_title


def transform(html, url, credit, title, prev_title, next_title):
    # 1) 去掉顶部开篇引导区里的弱链接（连同其前导 <br>）
    html = re.sub(r'<br\s*/?>\s*<a href="[^"]*"[^>]*>.*?点击查看人民日报原文</a>',
                  '', html, flags=re.S)

    # 2) 来源引用卡
    src_disp = f"人民日报 {credit}《{title}》" if credit else f"人民日报《{title}》"
    link_html = (f'<a href="{url}" style="display:inline-block;color:#D0021B;'
                 f'font-size:14px;font-weight:bold;text-decoration:none;">查看人民日报原文 →</a>'
                 if url else '<span style="color:#D0021B;font-size:14px;font-weight:bold;">查看人民日报原文</span>')
    source_card = f'''<!-- 来源引用 -->
<div style="background:#F5F5F5;border:1px solid #E5E5E5;border-radius:8px;padding:16px 18px;margin-bottom:20px;">
  <p style="margin:0 0 6px;font-size:12px;color:#999;letter-spacing:1px;">本文来源</p>
  <p style="margin:0 0 12px;font-size:15px;color:#333;font-weight:bold;line-height:1.6;">{src_disp}</p>
  {link_html}
</div>'''

    # 3) 上一篇/下一篇导航（占位链接，发布后替换 href）
    prev_line = (f'<a href="#" style="display:block;color:#666;font-size:14px;'
                 f'text-decoration:none;margin-bottom:10px;">上一篇：{prev_title}</a>'
                 if prev_title else '')
    next_disp = next_title if next_title else "持续更新中"
    next_line = (f'<a href="#" style="display:block;color:#666;font-size:14px;'
                 f'text-decoration:none;">下一篇：{next_disp}</a>')
    nav = f'''<!-- 上一篇/下一篇（发布知乎后替换 href="#" 为真实链接） -->
<div style="border-top:1px solid #E5E5E5;margin-top:20px;padding-top:16px;margin-bottom:8px;">
  {prev_line}
  {next_line}
</div>'''

    # 4) 插入到最外层容器 </div>（</body> 前）之内
    block = source_card + "\n" + nav
    body_idx = html.rfind('</body>')
    div_idx = html.rfind('</div>', 0, body_idx) if body_idx != -1 else -1
    if div_idx != -1:
        html = html[:div_idx] + block + html[div_idx:]
    else:
        html = html.replace('</body>', block + '</body>')
    return html


def gen_one(article, date_str, seq):
    art_dir = os.path.join(ROOT, "物料", date_str, article)
    if not os.path.isdir(art_dir):
        print(f"⚠️ 未找到文章目录: {article}"); return False
    html_path = find_gzh_html(art_dir)
    if not html_path:
        print(f"⚠️ 未找到公众号 A 套 HTML: {article}"); return False
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    url, credit = extract_source(html)
    prev_title, next_title = build_prevnext(seq, date_str, article)
    out = transform(html, url, credit, article, prev_title, next_title)

    zh_dir = os.path.join(art_dir, "知乎")
    os.makedirs(zh_dir, exist_ok=True)
    out_path = os.path.join(zh_dir, f"{article}_知乎.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"✅ {article} → 知乎/{article}_知乎.html"
          f"（上：{prev_title or '—'}｜下：{next_title or '持续更新中'}）")
    return True


def main():
    ap = argparse.ArgumentParser(description="知乎 HTML 生成器")
    ap.add_argument("title", nargs="?", help="文章标题（缺省则处理当天全部）")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    date_str = args.date
    ddir = os.path.join(ROOT, "物料", date_str)
    if not os.path.isdir(ddir):
        print(f"❌ 未找到日期目录: {date_str}"); return 1

    seq = collect_all_articles()

    if args.title:
        articles = [args.title]
    else:
        articles = []
        sj = os.path.join(ddir, "状态.json")
        if os.path.exists(sj):
            try:
                with open(sj, encoding="utf-8") as f:
                    data = json.load(f)
                articles = data.get("selected_articles") or []
            except Exception:
                articles = []
        if not articles:
            articles = scan_articles(ddir)

    if not articles:
        print("⚠️ 未找到文章，退出"); return 1

    ok = 0
    for a in articles:
        if gen_one(a, date_str, seq):
            ok += 1
    print(f"完成：{ok}/{len(articles)}")
    return 0 if ok == len(articles) else 1


if __name__ == "__main__":
    sys.exit(main())
