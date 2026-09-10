#!/usr/bin/env python3
"""结构化文章 MD → 三刀样式展示 HTML（通用渲染器，供每日自动化任务与手动使用）

用法:
  python3 gen_structure_html.py --md <结构化MD路径> --title "标题" \
      --source "人民日报2026-09-10 头版" --date "2026-09-10" \
      [--link "https://..." ] [--tags "思想建设,理论武装"] [--category "思想理论"] \
      [--subtitle "三章结构精读"] [--out 输出路径]

输入 MD 规范（见 物料模板/文章转MD结构化文档经验总结.md）:
  文首引用可含：> 标签：…    > 分类：…   （知行导入抽取；节末【关键词】不是文章标签）
  ## 第X章 ×××          → 章标题（红字+下划线）
  ### 第X节 ×××          → 节标题（红徽章+标题）
  > 原文内容             → 连续灰卡引用（小节名 **…** 渲染为红色加粗，段间紧凑）
  > **小节名。** 内容    → 同上，小节名红色加粗
  **【关键词】** a / b / c → 浅红卡文本流（· 分隔）

输出: 与 --md 同目录同名 _结构化HTML.html（全内联样式，兼容 H5 iframe 与小程序 rich-text）
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def q_to_html(q: str) -> str:
    """引用段内 **小节名** → 红色加粗 span"""
    parts = re.split(r"(\*\*.+?\*\*)", q)
    out = []
    for p in parts:
        if p.startswith("**") and p.endswith("**") and len(p) > 4:
            out.append(f'<b style="color:#D0021B;">{esc(p[2:-2])}</b>')
        else:
            out.append(esc(p))
    return "".join(out)


def split_labels(value: str) -> list[str]:
    parts = re.split(r"[·,，、/]", value or "")
    return [p.strip() for p in parts if p.strip()][:8]


def parse_front_meta(text: str) -> tuple[list[str], str]:
    """文首 > 标签： / > 分类： （出现 ## 章标题之前）"""
    tags: list[str] = []
    category = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            break
        body = line.lstrip(">").strip()
        if body.startswith("标签："):
            tags = split_labels(body[3:])
        elif body.startswith("分类："):
            items = split_labels(body[3:])
            category = items[0] if items else body[3:].strip()
    return tags, category


def parse_md(text: str):
    """解析规范 MD → [(章标题, [(节标题, [引用段], 节序号), ...]), ...]"""
    chapters = []
    cur_ch = None
    cur_sec = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("## "):
            if cur_sec:
                cur_ch[1].append(cur_sec)
                cur_sec = None
            if cur_ch:
                chapters.append(cur_ch)
            cur_ch = [line[3:].strip(), []]
        elif line.startswith("### "):
            if cur_sec:
                cur_ch[1].append(cur_sec)
            m = re.match(r"### 第([\u4e00-\u9fff]+)节\s*(.*)", line)
            cur_sec = [m.group(2) if m else line[4:].strip(), [], m.group(1) if m else ""]
        elif line.startswith(">") and cur_sec:
            cur_sec[1].append(line[1:].strip())
        elif "【关键词】" in line and cur_sec:
            cur_sec[1].append(line.strip())  # 追加到引用列表（含标记），渲染时过滤提取
    if cur_sec:
        cur_ch[1].append(cur_sec)
    if cur_ch:
        chapters.append(cur_ch)
    return chapters


def to_html(chapters, title, source, date, link, subtitle, tags=None, category=""):
    h = []
    h.append('<div style="max-width:680px;margin:0 auto;padding:20px;background:#FFFFFF;font-family:-apple-system,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;color:#333;box-sizing:border-box;">')

    # 报头（对齐三刀解剖 displayHtml）
    h.append('<div style="text-align:center;border-bottom:3px solid #D0021B;padding-bottom:12px;margin-bottom:20px;">')
    h.append('<div style="font-size:12px;color:#D0021B;letter-spacing:6px;margin-bottom:4px;">人民时评 · 精读系列</div>')
    h.append(f'<div style="font-size:26px;font-weight:bold;color:#D0021B;letter-spacing:2px;">{esc(title)}</div>')
    h.append(f'<div style="font-size:12px;color:#999;margin-top:6px;">{esc(subtitle)}</div>')
    h.append('</div>')

    # 引导卡（浅红底 + 左侧红条）
    total_secs = sum(len(s) for _, s in chapters)
    h.append('<div style="background:#FFF5F6;padding:15px;border-radius:8px;border-left:4px solid #D0021B;margin-bottom:20px;">')
    h.append('<p style="margin:0;font-size:14px;color:#4A4A4A;line-height:1.7;">')
    h.append(f'<b>【文章精读】{esc(title)}</b><br />')
    if source:
        h.append(f'来源：{esc(source)}<br />')
    if date:
        h.append(f'日期：{esc(date)}<br />')
    tag_items = [t for t in (tags or []) if t]
    if tag_items:
        h.append(f'标签：{" · ".join(esc(t) for t in tag_items)}<br />')
    if category:
        h.append(f'分类：{esc(category)}<br />')
    h.append(f'结构：{len(chapters)} 章 · {total_secs} 节 · 原文逐字保留<br />')
    if link:
        h.append(f'<a href="{esc(link)}" style="color:#D0021B;">📄 点击查看原文</a>')
    h.append('</p></div>')

    for ch_title, secs in chapters:
        h.append(f'<h2 style="color:#D0021B;font-size:18px;border-bottom:2px solid #D0021B;padding-bottom:8px;margin:20px 0 10px;">{esc(ch_title)}</h2>')
        for sec in secs:
            sec_title, quotes, num = sec[0], sec[1], sec[2]
            # 节标题
            h.append('<div style="display:flex;align-items:center;gap:8px;margin:14px 0 8px;">')
            if num:
                h.append(f'<span style="display:inline-block;background:#D0021B;color:#fff;font-size:12px;border-radius:10px;padding:2px 10px;flex-shrink:0;">第{esc(num)}节</span>')
            h.append(f'<span style="font-size:15px;font-weight:600;color:#1A1B1C;line-height:1.5;">{esc(sec_title)}</span>')
            h.append('</div>')
            # 原文引用：整节一张连续灰卡，段间紧凑；关键词行单独提取
            body_quotes = []
            kw = None
            for q in quotes:
                if "【关键词】" in q:
                    kw = q.split("【关键词】", 1)[1].strip().strip("*").strip()
                else:
                    body_quotes.append(q)
            if body_quotes:
                h.append('<div style="background:#F8F8F8;border-radius:8px;padding:12px 14px;margin-bottom:6px;font-size:14px;line-height:1.9;color:#333;">')
                for qi, q in enumerate(body_quotes):
                    mb = "10px" if qi < len(body_quotes) - 1 else "0"
                    h.append(f'<p style="margin:0 0 {mb};">{q_to_html(q)}</p>')
                h.append('</div>')
            # 关键词：浅红底紧凑卡 + 文本流
            if kw:
                items = [k.strip() for k in kw.split("/") if k.strip()]
                h.append('<div style="background:#FFF5F6;border-radius:8px;padding:8px 12px;margin:8px 0 14px;line-height:1.9;">')
                h.append('<b style="color:#D0021B;font-size:12px;">关键词</b>')
                h.append(f'<span style="font-size:13px;color:#4A4A4A;margin-left:8px;">{" · ".join(esc(k) for k in items)}</span>')
                h.append('</div>')

    h.append('</div>')
    return "\n".join(h)


def main():
    ap = argparse.ArgumentParser(description="结构化 MD → 三刀样式展示 HTML")
    ap.add_argument("--md", required=True, help="结构化 MD 文件路径（规范格式见脚本头注释）")
    ap.add_argument("--title", required=True, help="文档标题（报头主标题）")
    ap.add_argument("--source", default="", help="来源（引导卡显示）")
    ap.add_argument("--date", default="", help="日期（引导卡显示）")
    ap.add_argument("--link", default="", help="原文链接（引导卡显示，可选）")
    ap.add_argument("--tags", default="", help="文章标签，逗号分隔（覆盖 MD 文首「标签：」；知行导入用）")
    ap.add_argument("--category", default="", help="后台分类中文名，如思想理论（覆盖 MD 文首「分类：」）")
    ap.add_argument("--subtitle", default="三章结构精读", help="报头副标题")
    ap.add_argument("--out", default=None, help="输出路径（默认与 md 同目录 _结构化HTML.html）")
    args = ap.parse_args()

    md_path = Path(args.md)
    if not md_path.is_file():
        print(f"❌ MD 文件不存在: {md_path}")
        return 1
    md_text = md_path.read_text(encoding="utf-8")
    chapters = parse_md(md_text)
    if not chapters:
        print("❌ 未解析到章节（需 ## 章标题）")
        return 1

    md_tags, md_category = parse_front_meta(md_text)
    tags = split_labels(args.tags) or md_tags or ["政治理论"]
    category = (args.category or "").strip() or md_category or "思想理论"
    html = to_html(chapters, args.title, args.source, args.date, args.link, args.subtitle, tags, category)
    out = Path(args.out) if args.out else md_path.with_name(md_path.stem + "_结构化HTML.html")
    out.write_text(html, encoding="utf-8")

    total_secs = sum(len(s) for _, s in chapters)
    print(f"✅ 章 {len(chapters)} / 节 {total_secs} → {out} ({len(html)} 字符)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
