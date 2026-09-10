# -*- coding: utf-8 -*-
"""
人民日报评论文章抓取器（固定脚本，供 automation 步骤1 调用）

修复历史 bug（2026-09-01）：
  「纵横」栏目为摘编文章，文章页标题区只有栏目名（如 <p>纵横</p>），
  真实标题在正文第一个 <p>（如「县域消费当"同质同享"」）。
  旧逻辑直接拿标题区 <p> 文本当标题，导致生成「纵横_纵横.md」垃圾文件。
  本脚本：标题区含「（栏目）」则正常解析；否则回退到正文第一个 <p> 取真实标题。

用法：
  python 抓取.py --date 2026-09-01
  # 输出：物料/<date>/原文/09版_<栏目>_<标题>.md

依赖：bs4 + lxml（venv），标准库 urllib 抓取（无需 requests）。
"""
import argparse
import os
import re
import sys
import urllib.request
from datetime import datetime

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("缺少依赖：pip install beautifulsoup4 lxml")

BASE = "http://paper.people.com.cn/rmrb/pc"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", "ignore")


def date_to_ym_dd(date_str):
    """YYYY-MM-DD -> (YYYYMM, DD)"""
    ymd = date_str.replace("-", "")
    if len(ymd) != 8:
        raise ValueError(f"日期格式错误：{date_str}")
    return ymd[:6], ymd[6:]


def find_comment_edition(ym, dd):
    """从版面导航页找评论版号；找不到则默认 05。"""
    url = f"{BASE}/layout/{ym}/{dd}/node_01.html"
    html = fetch(url)
    # 版面导航形如 node_09.html">09版：评论
    m = re.search(r'node_(\d+)\.html"[^>]*>\s*\d+版：评论', html)
    if m:
        return int(m.group(1))
    # 备用：含「评论」的版面名
    for m2 in re.finditer(r'node_(\d+)\.html"[^>]*>([^<]*评论[^<]*)', html):
        return int(m2.group(1))
    return 5


def parse_article(html):
    """从文章页 HTML 提取标题/栏目/正文。返回 dict 或 None（非评论文章）。"""
    soup = BeautifulSoup(html, "lxml")
    art = soup.find("div", class_="article")
    if not art:
        return None

    # 标题区第一个无 class 的 <p>（形如「标题（栏目）」或纯栏目名「纵横」）
    title_p_text = ""
    for p in art.find_all("p", recursive=False):
        if not p.get("class"):
            t = p.get_text(" ", strip=True)
            if t:
                title_p_text = t
                break

    # 正文 div = 第一个无 class 的 <div>（跳过 <style> 等）
    content_div = None
    for d in art.find_all("div", recursive=False):
        if not d.get("class") and d.name == "div":
            content_div = d
            break

    # 解析标题 + 栏目
    title, column = "", ""
    m = re.match(r"^(.*?)[（(](.*?)[）)]$", title_p_text)
    if m and m.group(2):
        title = m.group(1).strip()
        column = m.group(2).strip()
    else:
        # 标题区只有栏目名（摘编栏目，如「纵横」），从正文第一个 <p> 取真实标题
        column = title_p_text.strip()
        if content_div:
            first_p = content_div.find("p")
            if first_p:
                title = first_p.get_text(" ", strip=True)

    # 过滤非评论文章
    if not title or title in ("图片报道", "本版责编"):
        return None
    if not content_div:
        return None

    # 正文段落
    paras = []
    for p in content_div.find_all("p", recursive=False):
        t = p.get_text(" ", strip=True)
        if t:
            paras.append(t)
    body = "\n\n".join(paras)
    if len(body) < 200:
        return None
    return {"title": title, "column": column, "body": body}


def main():
    ap = argparse.ArgumentParser(description="人民日报评论文章抓取器")
    ap.add_argument("--date", required=True, help="日期 YYYY-MM-DD")
    ap.add_argument("--out", default="", help="输出目录（默认 物料/<date>/原文）")
    args = ap.parse_args()

    ym, dd = date_to_ym_dd(args.date)
    edition = find_comment_edition(ym, dd)
    print(f"评论版号：{edition} 版")

    # 抓版面页，提取文章链接
    layout_url = f"{BASE}/layout/{ym}/{dd}/node_{edition:02d}.html"
    layout_html = fetch(layout_url)
    cids = sorted(set(re.findall(r"content_(\d+)\.html", layout_html)))
    print(f"版面文章链接：{len(cids)} 篇")

    out_dir = args.out or os.path.join(ROOT, "物料", args.date, "原文")
    os.makedirs(out_dir, exist_ok=True)

    saved = 0
    for cid in cids:
        url = f"{BASE}/content/{ym}/{dd}/content_{cid}.html"
        try:
            info = parse_article(fetch(url))
        except Exception as e:
            print(f"⚠️ {cid} 抓取失败：{e}")
            continue
        if not info:
            continue
        title, column, body = info["title"], info["column"], info["body"]
        fname = f"{edition:02d}版_{column}_{title}.md"
        md = (
            f"# {title}\n\n"
            f"> **来源**:人民日报 {args.date} 第{edition:02d}版 评论 | 栏目:{column}\n"
            f"> **链接**: {url}\n\n"
            f"{body}\n"
        )
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(md)
        print(f"✅ {fname}  ({len(body)}字)")
        saved += 1

    print(f"\n完成：保存 {saved} 篇到 {out_dir}")


if __name__ == "__main__":
    main()
