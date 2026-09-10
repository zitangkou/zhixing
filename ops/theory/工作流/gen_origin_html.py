#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_origin_html.py — 原文全文 → 三刀样式 HTML（汇总原文展示版）

用于把一篇文章的完整原文（.txt/.md 纯文本）渲染为三刀解剖样式 HTML：
报头红字三段 / 引导卡浅红底红左条 / 章节目录锚点 / 篇-章-节标题层级 / 正文段落。
视觉风格与 gen_structure_html.py 产物保持一致（背景 #FAF9F5、主红 #D0021B、全内联样式）。

用法:
  python gen_origin_html.py --txt <原文.txt> --title <标题> --subtitle <副题> \
      --source <来源> --meta <元信息行，可多个> --out <输出.html> [--kind gangyao|jianyi|auto]
"""
import argparse
import html as H
import re
import sys

BG = "#FAF9F5"
RED = "#D0021B"
TXT = "#1A1A1A"
GRAY = "#666666"
CARD = "#FFF5F6"
GRAY_CARD = "#F8F8F8"

# 篇/章/节 标题识别（中文数字）
CN_NUM = "一二三四五六七八九十百千万"
RE_PIAN = re.compile(rf"^第[{CN_NUM}]+篇[\s　]*(.*)$")
RE_ZHANG = re.compile(rf"^第[{CN_NUM}]+章[\s　]*(.*)$")
RE_JIE = re.compile(rf"^第[{CN_NUM}]+节[\s　]*(.*)$")
RE_DASHENG = re.compile(r"^<strong>([\s\S]*?)</strong>\s*$")


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def esc(s: str) -> str:
    return H.escape(s)


def find_body_start(lines, kind):
    """去掉电头/标题/目录，返回正文起始行。"""
    if kind == "gangyao":
        # 正文起点 = 第二次出现"第一篇"（第一次在目录里）
        idxs = [i for i, l in enumerate(lines) if l.strip().startswith("第一篇")]
        if len(idxs) > 1:
            return idxs[1]
        if idxs:
            return idxs[0]
        # 退化：找"目录"后第一个"第X篇"
        for i, l in enumerate(lines):
            if l.strip() == "目录":
                for j in range(i + 1, len(lines)):
                    if RE_PIAN.match(lines[j].strip()):
                        return j
        return 0
    if kind == "jianyi":
        # 建议文：跳过标题行（含"建议"的粗标题/日期行），从正文开始
        for i, l in enumerate(lines):
            s = l.strip()
            if s and not s.startswith("中共中央关于") and not s.startswith("（二〇"):
                return i
        return 0
    return 0


def render(txt_path, out_path, title, subtitle, source, metas, kind):
    raw = open(txt_path, encoding="utf-8").read()
    lines = raw.split("\n")
    start = find_body_start(lines, kind)
    body = lines[start:]

    # ---- 解析结构 ----
    pian = []      # (name, anchor)
    zhang = []     # (pian_idx, name, anchor)
    cur_pian = -1
    seq = {"p": 0, "z": 0, "j": 0}

    def aid(k):
        seq[k] += 1
        return f"{k}{seq[k]}"

    parsed = []    # (type, text, anchor)
    for raw_l in body:
        line = raw_l.strip()
        if not line:
            continue
        if kind == "jianyi":
            m = RE_DASHENG.match(line)
            if m:
                t = strip_tags(m.group(1)).strip("　 ")
                parsed.append(("zhang", t, aid("z")))
                continue
            # 普通段落，去除残留标签
            t = strip_tags(line)
            if t:
                parsed.append(("p", t, ""))
            continue
        # 纲要
        m = RE_PIAN.match(line)
        if m:
            t = (m.group(1) or "").strip("　 ")
            a = aid("p")
            pian.append((t, a))
            cur_pian = len(pian) - 1
            parsed.append(("pian", t, a))
            continue
        m = RE_ZHANG.match(line)
        if m:
            t = (m.group(1) or "").strip("　 ")
            a = aid("z")
            zhang.append((cur_pian, t, a))
            parsed.append(("zhang", t, a))
            continue
        m = RE_JIE.match(line)
        if m:
            t = (m.group(1) or "").strip("　 ")
            parsed.append(("jie", t, aid("j")))
            continue
        parsed.append(("p", line, ""))

    # ---- 组装 HTML ----
    h = []
    h.append('<html style="margin:0;padding:0;">')
    h.append(f'<body style="margin:0;padding:0;background:{BG};font-family:-apple-system,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;color:{TXT};">')
    h.append(f'<div style="max-width:760px;margin:0 auto;padding:0 16px 48px;box-sizing:border-box;">')

    # 报头
    h.append(f'<div style="padding:28px 2px 14px;">')
    h.append(f'<div style="color:{RED};font-size:13px;letter-spacing:6px;font-weight:600;">原文精读 · 完整收录</div>')
    h.append(f'<div style="font-size:27px;font-weight:bold;color:{RED};margin-top:10px;line-height:1.4;">{esc(title)}</div>')
    if subtitle:
        h.append(f'<div style="font-size:13px;color:{GRAY};margin-top:8px;">{esc(subtitle)}</div>')
    h.append(f'<div style="height:3px;background:{RED};margin-top:14px;"></div>')
    h.append(f'</div>')

    # 引导卡
    h.append(f'<div style="background:{CARD};border-left:4px solid {RED};border-radius:8px;padding:12px 14px;margin:16px 0;font-size:13px;color:#4A4A4A;line-height:1.9;">')
    h.append(f'<b style="color:{RED};">来源：</b>{esc(source)}')
    for m in metas:
        h.append(f'<br/><b style="color:{RED};">{esc(m.split("：")[0])}：</b>{esc(m.split("：",1)[1] if "：" in m else m)}')
    h.append(f'<br/><b style="color:{RED};">说明：</b>本页为原文全文汇总展示版，内容逐字保留原文，可用于 H5 学习与检索。')
    h.append(f'</div>')

    # 章节目录
    if zhang or pian:
        h.append(f'<div style="background:{GRAY_CARD};border-radius:8px;padding:14px 16px;margin:14px 0 20px;font-size:13px;">')
        h.append(f'<div style="color:{RED};font-weight:bold;font-size:14px;margin-bottom:8px;">📑 全文目录（点击跳转）</div>')
        if not pian and zhang:
            for _, t, a in zhang:
                h.append(f'<div style="padding:2px 0;"><a href="#{a}" style="color:#333;text-decoration:none;">{esc(t)}</a></div>')
        else:
            for i, (t, a) in enumerate(pian):
                h.append(f'<div style="padding:3px 0;font-weight:600;color:#222;"><a href="#{a}" style="color:#222;text-decoration:none;">第{["一","二","三","四","五","六","七","八","九","十","十一","十二","十三","十四","十五","十六","十七","十八","十九","二十"][i] if i < 20 else i+1}篇 {esc(t)}</a></div>')
                for pi, zt, za in zhang:
                    if pi == i:
                        h.append(f'<div style="padding:1px 0 1px 18px;"><a href="#{za}" style="color:#555;text-decoration:none;">{esc(zt)}</a></div>')
        h.append(f'</div>')

    # 正文
    for typ, t, a in parsed:
        if typ == "pian":
            h.append(f'<div id="{a}" style="font-size:20px;font-weight:bold;color:{RED};margin:30px 0 10px;padding-bottom:6px;border-bottom:2px solid {RED};">{esc(t)}</div>')
        elif typ == "zhang":
            h.append(f'<div id="{a}" style="font-size:16px;font-weight:bold;color:{RED};margin:22px 0 8px;">{esc(t)}</div>')
        elif typ == "jie":
            h.append(f'<div style="display:inline-block;background:{RED};color:#fff;font-size:13px;font-weight:600;padding:2px 10px;border-radius:4px;margin:18px 0 6px;">{esc(t)}</div>')
        else:
            h.append(f'<p style="margin:0 0 10px;font-size:14px;line-height:1.9;color:{TXT};">{esc(t)}</p>')

    h.append(f'</div>')
    h.append(f'</body>')
    h.append(f'</html>')

    html_str = "\n".join(h)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_str)
    print(f"✅ 已生成: {out_path} ({len(html_str)/1024:.0f}KB, 篇{len(pian)} 章{len(zhang)} 正文段{sum(1 for x in parsed if x[0]=='p')})")


def main():
    ap = argparse.ArgumentParser(description="原文全文 → 三刀样式 HTML")
    ap.add_argument("--txt", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="原文全文汇总 · 逐字保留")
    ap.add_argument("--source", default="")
    ap.add_argument("--meta", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--kind", default="auto", choices=["auto", "gangyao", "jianyi"])
    args = ap.parse_args()

    kind = args.kind
    if kind == "auto":
        s = open(args.txt, encoding="utf-8").read()
        kind = "jianyi" if "<strong>" in s else "gangyao"
    render(args.txt, args.out, args.title, args.subtitle, args.source, args.meta, kind)


if __name__ == "__main__":
    main()
