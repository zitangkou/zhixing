# -*- coding: utf-8 -*-
"""
公众号 / 知乎 封面图生成器（本地底图版 · v2.16）

从 物料模板/封面图模版/<尺寸>/ 读用户准备的底图，按日期轮动选取，
纯底图不加字（2026-08-31 决策）：
  · 公众号封面：底图直出 900×383 → <文章>/公众号/封面图.png
  · 知乎封面：底图 2× 放大 1800×766 → <文章>/知乎/封面图_知乎.png

依赖：Pillow（venv），仅做复制 + 放大，不在图上渲染文字。

用法：
  python 封面图生成.py --date 2026-08-31
      （自动读 物料/<date>/状态.json 的 selected_articles）
  python 封面图生成.py --date 2026-08-31 --articles "标题A" "标题B"
  python 封面图生成.py --date 2026-08-31 --dry-run
"""
import os
import json
import argparse
import shutil
from datetime import date as _date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
REG_PATH = os.path.join(ROOT, "物料模板", "封面图模版库.json")


def load_reg():
    with open(REG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def enabled_templates(reg):
    ts = [t for t in reg.get("templates", []) if t.get("enabled")]
    ts.sort(key=lambda t: t.get("id", 0))
    return ts


def rotate_index(d: _date, reg) -> int:
    start_s = reg.get("selection", {}).get("rotate_start")
    if start_s:
        y, m, day = map(int, start_s.split("-"))
        start = _date(y, m, day)
    else:
        start = _date(2026, 8, 31)
    n = len(enabled_templates(reg))
    if n == 0:
        return 0
    return (d - start).days % n


def read_articles(date_str, root, cli_articles):
    if cli_articles:
        return cli_articles
    sj = os.path.join(root, "物料", date_str, "状态.json")
    if os.path.exists(sj):
        with open(sj, encoding="utf-8") as f:
            data = json.load(f)
        arts = data.get("selected_articles") or []
        if arts:
            return arts
    d = os.path.join(root, "物料", date_str)
    if os.path.isdir(d):
        return [name for name in os.listdir(d)
                if os.path.isdir(os.path.join(d, name))
                and name not in ("原文", "筛选")]
    return []


def gen_one(article, date_str, root, reg, base_idx, dry):
    ts = enabled_templates(reg)
    n = len(ts)
    if n == 0:
        print("⚠️ 模板库无启用底图，跳过"); return
    tpl = ts[base_idx % n]
    base_rel = tpl["file"]  # e.g. 900x383/01_封面底图.png
    base_abs = os.path.join(ROOT, "物料模板", "封面图模版", base_rel)
    if not os.path.exists(base_abs):
        print(f"⚠️ 底图缺失: {base_abs}（跳过 {article}）"); return
    art_dir = os.path.join(root, "物料", date_str, article)
    pub_dir = os.path.join(art_dir, "公众号")
    os.makedirs(pub_dir, exist_ok=True)
    out_pub = os.path.join(pub_dir, "封面图.png")
    if dry:
        print(f"[dry] {article} ← 模板#{tpl['id']} {base_rel} → 封面图.png")
        return
    shutil.copy(base_abs, out_pub)
    from PIL import Image
    with Image.open(base_abs) as im:
        w, h = im.size
    print(f"✅ {article} ← 模板#{tpl['id']} {base_rel} → 封面图.png({w}×{h})")


def main():
    ap = argparse.ArgumentParser(description="封面图生成（本地底图版，纯底图不加字）")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--root", default=ROOT, help="项目根目录")
    ap.add_argument("--articles", nargs="*", help="文章标题列表（默认读状态.json）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reg = load_reg()
    # v2.18 平行产出：--date 支持 "-v18" 后缀（对应 物料/<日期>-v18/ 目录），轮动计算剥离后缀
    base_date = args.date.split("-v18")[0]
    d = _date(*map(int, base_date.split("-")))
    base_idx = rotate_index(d, reg)
    arts = read_articles(args.date, args.root, args.articles)
    if not arts:
        print("⚠️ 未找到文章，退出"); return
    print(f"日期 {args.date} 轮动基准序号={base_idx}，文章数={len(arts)}")
    for i, a in enumerate(arts):
        gen_one(a, args.date, args.root, reg, base_idx + i, args.dry_run)


if __name__ == "__main__":
    main()
