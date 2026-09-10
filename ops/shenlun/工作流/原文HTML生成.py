#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
原文HTML生成.py — 将人民日报评论原文纯文本(md)渲染为统一版式的 HTML 文档

样式布局与「三刀解剖内容公众号模版_v2.18.html」统一：
- 品牌红 #D0021B / 浅粉 #FFF5F6 / 米白 #FAF9F5 / 浅灰 #F8F8F8
- 报头「时评精拆」三行、卡片圆角 8px、正文行高 1.7-1.9
- 页面容器 max-width:680px 白底居中

用法:
  python3 工作流/原文HTML生成.py --date <YYYY-MM-DD>    # 批量：物料/<日期>/原文/ 全部 md → 同名 _原文.html
  python3 工作流/原文HTML生成.py "<原文md路径>" [--out <输出html路径>]
  # 默认输出到 md 同目录: <同目录>/<标题>_原文.html

解析规则（与 抓取.py 产出格式一致）:
  第1行          # 标题
  引用块(>)      来源 / 链接 元信息
  全部正文段落   均写入正文
  灰块           原文中心论点段（非首段钩子）；标题下输出「主题：」供后台预览
"""
import argparse
import os
import re
import sys

THEME_PRESETS = (
    "政绩观",
    "社会治理",
    "乡村振兴",
    "县域经济",
    "高质量发展",
    "民生保障",
    "作风建设",
    "基层减负",
    "科技创新",
    "文化建设",
    "生态文明",
    "依法治国",
)
_THESIS_RE = re.compile(r"关键在于|核心在于|根本上|归根结底|必须坚持")
_HOOK_RE = re.compile(r"^(近日|日前|一段时间以来|不久前|前不久)")
_EXAMPLE_RE = re.compile(r"^某[县市区镇乡村]")


def pick_thesis(paragraphs):
    """从原文段落中选中心论点文段（不是解剖改写的总论点）。"""
    if not paragraphs:
        return ""
    for p in paragraphs:
        if _THESIS_RE.search(p):
            return p
    rest = []
    for p in paragraphs:
        if _HOOK_RE.search(p) or _EXAMPLE_RE.search(p):
            continue
        if len(p) < 40:
            continue
        rest.append(p)
    if rest:
        return rest[0]
    return paragraphs[0]


def themes_from_anatomy(md_path):
    """同文章目录 解剖/*三刀解剖.md 的「主题归类」→ 后台主题词。"""
    article_dir = os.path.dirname(os.path.dirname(os.path.abspath(md_path)))
    anatomy_dir = os.path.join(article_dir, "解剖")
    if not os.path.isdir(anatomy_dir):
        return []
    md_files = [
        f for f in os.listdir(anatomy_dir)
        if f.endswith(".md") and "三刀解剖" in f
    ]
    if not md_files:
        return []
    path = os.path.join(anatomy_dir, sorted(md_files)[0])
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []
    match = re.search(r"主题归类\s*[:：]\s*(.+)", text)
    if not match:
        return []
    raw = match.group(1).strip()
    hits = [p for p in THEME_PRESETS if p in raw]
    if hits:
        return hits
    mid = re.search(r"·([^｜|]+)", raw)
    short = (mid.group(1) if mid else raw.split("｜")[0]).split("（")[0].strip()
    return [short] if short else []


def parse_md(md_text):
    """解析原文 md，返回 dict: title/source/url/thesis/body/themes"""
    lines = md_text.splitlines()
    title = ""
    source_lines = []
    body_start = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not title and stripped.startswith("# "):
            title = stripped[2:].strip()
        elif stripped.startswith(">") and body_start is None:
            source_lines.append(stripped.lstrip(">").strip())
        elif stripped and not stripped.startswith("#"):
            body_start = i
            break

    # 元信息解析（逐行：兼容 **来源**:值 / 来源:值）
    source, url = "", ""
    for sline in source_lines:
        m = re.match(r"\**\s*(来源|链接)\s*\**\s*[:：]\s*(.*)$", sline)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "来源":
            source = val
        elif key == "链接":
            url = val

    # 标题降级：标题行过长（≥25 字，抓取脚本回退到正文第一段取标题时产生）→ 用「栏目:」字段作标题
    # 典型栏目词不视为标题（人民时评/评论员观察等）
    TYPICAL_COLUMNS = ("人民时评", "评论员观察", "金台随笔", "暖闻热评", "今日谈", "纵横",
                       "来论", "现场评论", "大家谈", "人民论坛", "微观", "连线评论员",
                       "国际观澜", "新知", "短评", "金社平", "三农观察", "要闻", "论坛综述",
                       "中国记协综合稿", "编辑手记")
    if title and len(title) >= 25 and source:
        m = re.search(r"栏目[:：]\s*([^|｜]+)", source)
        if m:
            col = m.group(1).strip()
            if col and col not in TYPICAL_COLUMNS:
                title = col

    # 正文段落
    paragraphs = []
    for line in lines[body_start:]:
        stripped = line.strip()
        if not stripped:
            continue
        paragraphs.append(stripped)

    thesis = pick_thesis(paragraphs)
    return {"title": title, "source": source, "url": url, "thesis": thesis, "body": paragraphs}


def esc(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_html(data):
    title = esc(data["title"])
    source = esc(data["source"])
    url = esc(data["url"])
    thesis = esc(data.get("thesis") or "")
    themes = [esc(t) for t in (data.get("themes") or []) if t]
    paragraphs = [esc(p) for p in data["body"]]

    # 来源展示：人民日报 YYYY年MM月DD日第XX版
    source_display = source if source else "人民日报"
    theme_line = "、".join(themes)
    theme_html = (
        f'<p style="text-align:center;font-size:13px;color:#D0021B;margin:0 0 12px;">主题：{theme_line}</p>'
        if theme_line
        else ""
    )

    head_html = "\n".join(
        f'    <p style="margin:0 0 14px;font-size:16px;line-height:1.9;color:#333;text-indent:2em;">{p}</p>'
        for p in paragraphs
    )

    link_html = (
        f'<a href="{url}" style="display:inline-block;background:#D0021B;color:#fff;'
        f'font-size:13px;padding:8px 16px;border-radius:6px;text-decoration:none;">'
        f'📄 查看人民日报原文</a>'
        if url
        else ""
    )

    return f'''<meta charset="utf-8">
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>时评精拆｜原文：《{title}》</title>
<style>
  body{{margin:0;padding:0;background:#FAF9F5;font-family:"PingFang SC","Microsoft YaHei",sans-serif;color:#333;}}
</style>
</head>
<body>

<div style="max-width:680px;margin:0 auto;padding:20px;background:#FFFFFF;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;color:#333;">

  <!-- 报头（与三刀解剖公众号模版统一） -->
  <div style="text-align:center;border-bottom:3px solid #D0021B;padding-bottom:12px;margin-bottom:20px;">
    <div style="font-size:12px;color:#D0021B;letter-spacing:6px;margin-bottom:4px;">人民时评 · 精读系列</div>
    <div style="font-size:28px;font-weight:bold;color:#D0021B;letter-spacing:2px;">时评精拆</div>
    <div style="font-size:12px;color:#999;margin-top:6px;">人民日报评论文章 · 申论素材拆解</div>
  </div>

  <!-- 原文头部：链接按钮 + 文章标题 + 元信息 -->
  <div style="text-align:center;margin-bottom:20px;">
    {link_html}
  </div>
  <h1 style="font-size:24px;font-weight:bold;color:#1A1B1C;text-align:center;line-height:1.5;margin:0 0 10px;">《{title}》</h1>
  <p style="text-align:center;font-size:13px;color:#999;margin:0 0 12px;">—— {source_display}</p>
  {theme_html}

  <!-- 中心论点（后台预览作摘要） -->
  <div style="background:#F8F8F8;padding:15px;border-radius:8px;margin-bottom:20px;">
    <p style="font-size:12px;color:#D0021B;margin:0 0 8px;">中心论点：</p>
    <p style="font-size:14px;color:#666;line-height:1.8;margin:0;font-style:italic;">{thesis}</p>
  </div>

  <!-- 正文 -->
  <div>
{head_html}
  </div>

  <!-- 底部来源卡 -->
  <div style="background:#FFF5F6;padding:15px;border-radius:8px;border-left:4px solid #D0021B;margin-top:24px;">
    <p style="margin:0;font-size:13px;color:#4A4A4A;line-height:1.7;">
      <b style="color:#D0021B;">📄 原文出处：</b>{source_display}<br>
      本文为「时评精拆」原文精读配套文档，仅供申论学习参考；版权归人民日报及原作者所有。
      {('<br><a href="' + url + '" style="color:#D0021B;">点击查看人民日报原文</a>') if url else ''}
    </p>
  </div>

</div>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(description="原文纯文本 → 统一版式 HTML")
    parser.add_argument("md_path", nargs="?", help="原文 md 文件路径（--date 模式可省略）")
    parser.add_argument("--date", help="批量模式：物料/<日期>/原文/ 全部 md → 同名 _原文.html")
    parser.add_argument("--into-articles", action="store_true",
                        help="（配合 --date）归位模式：把与文章目录同名的选中文章 md+HTML 复制/生成到 物料/<日期>/<文章标题>/原文/")
    parser.add_argument("--out", help="输出 HTML 路径（默认 md 同目录/<标题>_原文.html）")
    args = parser.parse_args()

    if args.date and not args.md_path:
        base = "物料" if os.path.isdir("物料") else "."
        src_dir = os.path.join(base, args.date, "原文")
        if not os.path.isdir(src_dir):
            print(f"[错误] 原文目录不存在: {src_dir}", file=sys.stderr)
            sys.exit(1)
        md_files = sorted(
            f for f in os.listdir(src_dir)
            if f.endswith(".md") and not f.endswith("_原文.md")
        )
        if not md_files:
            print(f"[错误] {src_dir} 下无原文 md", file=sys.stderr)
            sys.exit(1)

        if args.into_articles:
            return _sync_into_articles(base, args.date, md_files, src_dir)

        ok, fail = 0, 0
        for md_file in md_files:
            md_path = os.path.join(src_dir, md_file)
            try:
                _generate(md_path, None)
                ok += 1
            except SystemExit:
                fail += 1
            except Exception as e:  # noqa: BLE001
                print(f"[错误] {md_file}: {e}", file=sys.stderr)
                fail += 1
        print(f"[完成] 批量生成 {ok} 篇，失败 {fail} 篇（目录: {src_dir}）")
        sys.exit(1 if fail else 0)

    if not args.md_path:
        parser.error("需提供 <原文md路径> 或 --date 批量模式")

    _generate(args.md_path, args.out)


def _sync_into_articles(base, date_str, md_files, src_dir):
    """归位模式：解析日期级原文 md 的标题 → 匹配 物料/<日期>/<文章标题>/ 目录 →
    复制 md + 生成 _原文.html 到文章目录/原文/（文章物料自足成包）。"""
    import shutil

    def norm_key(s):
        """归一化匹配键：删全部引号（中英文）、零宽字符与空白，剥末尾栏目括号后缀
        （如《…》（“三农”观察）→《…》），容忍历史数据引号/栏目后缀不一致。"""
        base = (s.replace("“", "").replace("”", "")
                 .replace("‘", "").replace("’", "")
                 .replace('"', "").replace("'", "")
                 .replace("\u200d", "").replace("\u200b", "")
                 .replace(" ", "").strip())
        m = re.search(r"[（(][^）)]*[）)]$", base)
        if m:
            base = base[:m.start()]
        return base

    date_dir = os.path.join(base, date_str)
    # 扫描文章级目录（含 解剖/公众号/小红书 任一子目录），键做归一化
    article_dirs = {}
    for name in os.listdir(date_dir):
        p = os.path.join(date_dir, name)
        if not os.path.isdir(p):
            continue
        subs = [s for s in os.listdir(p) if os.path.isdir(os.path.join(p, s))]
        if any(s in ("解剖", "公众号", "小红书") for s in subs):
            article_dirs[norm_key(name)] = p

    if not article_dirs:
        print(f"[提示] {date_str} 无文章级目录（可能是 08-26 早期顶层结构），跳过归位")
        return 0

    ok, skip = 0, 0
    for md_file in md_files:
        md_path = os.path.join(src_dir, md_file)
        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        data = parse_md(md_text)
        title = data["title"]
        if not title:
            print(f"[跳过] {md_file}: 未解析到标题")
            skip += 1
            continue
        # 匹配文章目录（支持 09-09 长句标题降级后与目录同名）
        art_dir = article_dirs.get(norm_key(title))
        if not art_dir:
            skip += 1
            continue
        dest = os.path.join(art_dir, "原文")
        os.makedirs(dest, exist_ok=True)
        dest_md = os.path.join(dest, md_file)
        if not (os.path.exists(dest_md) and os.path.getsize(dest_md) == os.path.getsize(md_path)):
            shutil.copy2(md_path, dest_md)
        _generate(dest_md, None)
        ok += 1
    print(f"[完成] 归位 {ok} 篇到文章目录/原文/（无对应文章目录跳过 {skip} 篇，目录: {date_str}）")
    return 0 if ok or skip else 1


def _generate(md_path, out_path):
    if not os.path.isfile(md_path):
        print(f"[错误] 原文文件不存在: {md_path}", file=sys.stderr)
        sys.exit(1)

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    data = parse_md(md_text)
    data["themes"] = themes_from_anatomy(md_path)
    if not data["title"]:
        print("[错误] 未解析到标题（需 # 开头）", file=sys.stderr)
        sys.exit(1)

    html = build_html(data)

    if out_path:
        out = out_path
    else:
        out = os.path.join(
            os.path.dirname(os.path.abspath(md_path)), f'{data["title"]}_原文.html'
        )

    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[完成] 原文 HTML 已生成: {out}")
    print(f"       标题: {data['title']}")
    print(f"       来源: {data['source'] or '未解析到'}")
    print(f"       主题: {'、'.join(data.get('themes') or []) or '未解析到'}")
    print(f"       正文段落数: {len(data['body'])}")


if __name__ == "__main__":
    main()
