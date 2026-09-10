#!/usr/bin/env python3
"""
时政考点模拟题 → 公众号 HTML + 小红书单题卡片 生成器

数据源：iCloud 云盘 政治理论/物料/2026-09-04/题目/*.json（20题）
产出：
  1. 公众号 HTML（仿人民日报内容运营「时评精拆」系列风格，中国红 #D0021B）
  2. 小红书单题卡片 20 张（1242×1660 PNG）
     - 每张卡片开头放置「上一题答案 + 简短解析」（第1题无上一题，直接题干）
     - 最后一张答案速查卡汇总全部答案

用法：
  python3 scripts/xingce/gen_rmrb_card_html.py
"""
import json
import os
import re
import subprocess
import sys
import argparse
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────
ICLOUD_ROOT = Path("/Users/dnn/Library/Mobile Documents/com~apple~CloudDocs/政治理论")
DATE_STR = "2026-09-04"
COVER_SUB = "时政考点 · 精读一练"
G_VALUE_TXT = "92/100"
G_SOURCE = "人民日报"
G_ANCHOR = ""
ARTICLE_TITLE = "携手各国发展振兴，改革完善全球治理"
DATE_DIR = ICLOUD_ROOT / "物料" / DATE_STR
JSON_PATH = DATE_DIR / "题目" / f"人民日报{DATE_STR}_{ARTICLE_TITLE}_20题.json"
GZH_DIR = DATE_DIR / "公众号"
XHS_DIR = DATE_DIR / "小红书" / "图片"

GZH_HTML = GZH_DIR / f"人民日报{DATE_STR}_{ARTICLE_TITLE}_20题_公众号.html"

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BRAND_RED = "#D0021B"
PINK_BG = "#FFF5F6"
CREAM_BG = "#FAF9F5"
DARK = "#333333"
MID = "#666666"
W, H = 1242, 1660

DIFF_LABEL = {1: "简单", 2: "中等", 3: "较难", 4: "困难", 5: "挑战"}


# ══════════════════════════════════════════════════════
# 1. 公众号 HTML
# ══════════════════════════════════════════════════════

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def short_answer_line(q):
    """生成简短的上一题答案说明（用于答案速查卡等紧凑场景）"""
    ans = q["answer"]
    if q.get("answer_short"):
        return ans, q["answer_short"]
    m = re.search(r"【正确项】([^\n]+)", q["explanation"])
    core = m.group(1).strip() if m else ""
    core = re.sub(rf"^{ans}：", "", core)
    return ans, core


def medium_answer_block(q):
    """生成中等长度的上一题答案解析块（用于小红书卡片顶部，利用留白）。
    包含：正确项解释 + 前2个干扰项手法分析。
    """
    ans = q["answer"]
    parsed = parse_explanation(q)
    lines = []

    # 正确项
    correct = parsed["correct"]
    correct = re.sub(rf"^{ans}[:：]\s*", "", correct)
    if correct:
        if len(correct) > 80:
            correct = correct[:77] + "…"
        lines.append(f'<div style="font-size:26px;color:#1A1A1A;line-height:1.55;margin-bottom:8px;"><span style="color:#2E7D32;font-weight:bold;">正确项：</span>{esc(correct)}</div>')

    # 干扰项（最多2个）
    for d in parsed["distractors"][:2]:
        text = d["text"]
        if len(text) > 70:
            text = text[:67] + "…"
        lines.append(f'<div style="font-size:24px;color:#555;line-height:1.5;margin-bottom:4px;"><span style="color:{BRAND_RED};font-weight:600;">▸ {d["opt"]}项（{d["type"]}）：</span>{esc(text)}</div>')

    return ans, "\n".join(lines) if lines else f'<div style="font-size:26px;color:#333;">详见完整解析</div>'


def parse_explanation(q):
    """把 explanation 拆成 正确项/干扰项 便于展示"""
    txt = q["explanation"]
    out = {"origin": "", "correct": "", "distractors": [], "conclusion": ""}
    m = re.search(r"【出处】([^\n]*)", txt)
    out["origin"] = m.group(1).strip() if m else ""
    m = re.search(r"【正确项】([^\n]*)", txt)
    out["correct"] = m.group(1).strip() if m else ""
    m = re.search(r"【结论】(故本题选[^\n]*)", txt)
    out["conclusion"] = m.group(1).strip() if m else ""
    # 干扰项行：形如 "  X项（手法）：..."
    for line in txt.split("\n"):
        line = line.strip()
        mm = re.match(r"([A-D])项（([^）]+)）[:：](.*)", line)
        if mm:
            out["distractors"].append({"opt": mm.group(1), "type": mm.group(2), "text": mm.group(3).strip()})
    return out


def gen_gzh_html(questions):
    """生成公众号风格 HTML（完整20题 + 答案 + 解析）"""
    parts = []
    parts.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>时政考点模拟题｜__ART__</title>
<style>
  body{margin:0;padding:0;background:#FAF9F5;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;color:#333;}
</style>
</head>
<body>
<div style="max-width:680px;margin:0 auto;padding:20px;background:#FFFFFF;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;color:#333;">

  <!-- 报头 -->
  <div style="text-align:center;border-bottom:3px solid #D0021B;padding-bottom:12px;margin-bottom:20px;">
    <div style="font-size:12px;color:#D0021B;letter-spacing:6px;margin-bottom:4px;">人民时评 · 精读系列</div>
    <div style="font-size:28px;font-weight:bold;color:#D0021B;letter-spacing:2px;">时政考点模拟题</div>
    <div style="font-size:12px;color:#999;margin-top:6px;">人民日报头版文章 · 公考时政考点出题</div>
  </div>
""")

    # 开篇引导
    parts.append("""
  <!-- 开篇引导 -->
  <div style="background:#FFF5F6;padding:15px;border-radius:8px;border-left:4px solid #D0021B;margin-bottom:20px;">
    <p style="margin:0;font-size:14px;color:#4A4A4A;line-height:1.7;">
      <b>【时政考点模拟题】__DATE__ 期</b><br>
      素材：《__ART__》<br>
      主题：__SUB__<br>
      __ANCHOR_LINE__
      题量：20 题｜价值分 __VS__
    </p>
  </div>
""")

    # 逐题
    for i, q in enumerate(questions, 1):
        num = f"{i:02d}"
        expl = parse_explanation(q)
        parts.append(f"""
  <!-- 第{num}题 -->
  <h2 style="color:#D0021B;font-size:17px;border-bottom:2px solid #D0021B;padding-bottom:8px;">📌 第{num}题（{q['subtype']}｜难度{DIFF_LABEL.get(q['difficulty'], q['difficulty'])}｜答案{q['answer']}）</h2>
  <p style="font-size:14px;color:#333;line-height:1.8;margin:10px 0;"><b>考点：</b>{q['topic']} / {q['tag']}</p>
  <p style="font-size:15px;color:#1A1A1A;line-height:1.8;margin:10px 0;font-weight:500;">{esc(q['stem'])}</p>
  <table style="width:100%;border-collapse:collapse;margin:10px 0 15px;font-size:13px;">
""")
        for label in ["A", "B", "C", "D"]:
            mark = " ✅" if label == q["answer"] else ""
            bg = "#FFF5F6" if label == q["answer"] else "#FFFFFF"
            parts.append(f"""    <tr style="background:{bg};"><td style="padding:8px;border:1px solid #eee;width:28px;font-weight:bold;color:#D0021B;">{label}</td><td style="padding:8px;border:1px solid #eee;color:#333;">{esc(q['options'][label])}{mark}</td></tr>""")
        parts.append("""  </table>
  <div style="background:#FAF9F5;padding:12px 15px;border-radius:8px;margin-bottom:8px;">
    <p style="margin:0 0 6px;font-size:13px;color:#D0021B;"><b>【解析】</b></p>
""")
        if expl["origin"]:
            parts.append(f'    <p style="margin:2px 0;font-size:12px;color:#666;">📎 出处：{esc(expl["origin"])}</p>')
        if expl["correct"]:
            parts.append(f'    <p style="margin:2px 0;font-size:13px;color:#333;"><b>✓ 正确项：</b>{esc(expl["correct"])}</p>')
        if expl["distractors"]:
            parts.append('    <p style="margin:2px 0;font-size:12px;color:#666;"><b>干扰项：</b></p>')
            for d in expl["distractors"]:
                parts.append(f'    <p style="margin:2px 0 2px 14px;font-size:12px;color:#666;">· {d["opt"]}项（{d["type"]}）：{esc(d["text"])}</p>')
        parts.append(f'    <p style="margin:6px 0 0;font-size:13px;color:#D0021B;"><b>{esc(expl["conclusion"] or f"故本题选{q["answer"]}。")}</b></p>')
        parts.append("  </div>")

    # 页脚
    parts.append("""
  <!-- 页脚 -->
  <div style="text-align:center;border-top:2px solid #D0021B;padding-top:12px;margin-top:20px;">
    <div style="font-size:12px;color:#D0021B;">时政考点模拟题 · 每日一练</div>
    <div style="font-size:11px;color:#999;margin-top:4px;">素材来源：__SRC__ __DATE__ ｜ 价值分 __VS__</div>
  </div>
</div>
</body>
</html>""")
    anchor_line = (f'原文链接：<a href="{G_ANCHOR}">{G_ANCHOR}</a><br>' if G_ANCHOR else "")
    html = "\n".join(parts)
    return (html.replace("__ART__", ARTICLE_TITLE).replace("__SUB__", COVER_SUB)
                .replace("__ANCHOR_LINE__", anchor_line)
                .replace("__DATE__", DATE_STR).replace("__VS__", G_VALUE_TXT)
                .replace("__SRC__", G_SOURCE))


# ══════════════════════════════════════════════════════
# 2. 小红书单题卡片
# ══════════════════════════════════════════════════════

def gen_card_html(questions, idx):
    """生成第 idx 张卡片 HTML（idx 从 1 起）。
    布局：上一题答案+简短解析（顶部）→ 当前题干 → 选项 → 底部页码。
    """
    q = questions[idx - 1]
    total = len(questions)
    prev_html = ""
    if idx > 1:
        prev = questions[idx - 2]
        ans, detail_html = medium_answer_block(prev)
        prev_html = f"""
  <div style="background:#F3F7FB;border-left:6px solid #2E7D32;border-radius:12px;padding:24px 32px;margin-bottom:24px;">
    <div style="font-size:30px;font-weight:bold;color:#2E7D32;letter-spacing:2px;margin-bottom:12px;">上题答案 · 第{idx-1:02d}题 → {ans}</div>
    {detail_html}
  </div>"""

    # 选项列表
    opts_html = ""
    for label in ["A", "B", "C", "D"]:
        opts_html += f"""
    <div style="display:flex;align-items:flex-start;padding:22px 28px;border:2px solid #eee;border-radius:14px;margin-bottom:20px;">
      <div style="min-width:56px;height:56px;border-radius:50%;background:#F2F2F2;color:#333;font-size:30px;font-weight:bold;display:flex;align-items:center;justify-content:center;margin-right:20px;">{label}</div>
      <div style="font-size:29px;color:#333;line-height:1.55;padding-top:6px;">{esc(q['options'][label])}</div>
    </div>"""

    inner = f"""
<div style="width:{W}px;height:{H}px;background:#fff;position:relative;display:flex;flex-direction:column;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;">
  <div style="background:{PINK_BG};padding:30px 56px;display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid {BRAND_RED};">
    <span style="color:{BRAND_RED};font-size:32px;font-weight:bold;letter-spacing:5px;">时政考点打卡</span>
    <span style="color:{MID};font-size:26px;">第{idx:02d}/{total:02d}题</span>
  </div>
  <div style="background:{BRAND_RED};padding:30px 56px;">
    <span style="color:#fff;font-size:44px;font-weight:bold;letter-spacing:3px;">第{idx:02d}题 · {q['tag']}</span>
  </div>
  <div style="flex:1;padding:36px 56px;overflow:hidden;">
    {prev_html}
    <div style="font-size:32px;color:#1A1A1A;line-height:1.7;font-weight:500;margin-bottom:26px;">{esc(q['stem'])}</div>
    {opts_html}
  </div>
  <div style="padding:30px 56px;border-top:2px solid #eee;display:flex;justify-content:space-between;align-items:center;">
    <span style="color:{MID};font-size:24px;">人民日报 · 时政考点</span>
    <span style="color:{BRAND_RED};font-size:28px;font-weight:bold;">{idx}/{total}</span>
  </div>
</div>"""
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>*{{box-sizing:border-box;margin:0;padding:0;}}body{{margin:0;padding:0;background:#fff;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;}}</style>
</head><body>{inner}</body></html>"""


def gen_answer_card_html(questions):
    """答案速查卡（最后一张）：汇总全部答案 + 第20题答案"""
    total = len(questions)
    last = questions[-1]
    ans, core = short_answer_line(last)
    rows = ""
    # 4行×5列
    for i in range(0, total, 5):
        chunk = questions[i:i + 5]
        cells = ""
        for q in chunk:
            cells += f'<div style="flex:1;background:#F7F7F7;border-radius:12px;padding:20px 10px;text-align:center;margin-right:14px;"><div style="font-size:24px;color:#999;">第{q["question_id"][-3:]}题</div><div style="font-size:40px;font-weight:bold;color:{BRAND_RED};margin-top:8px;">{q["answer"]}</div></div>'
        rows += f'<div style="display:flex;margin-bottom:14px;">{cells}</div>'
    inner = f"""
<div style="width:{W}px;height:{H}px;background:#fff;position:relative;display:flex;flex-direction:column;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;">
  <div style="background:{PINK_BG};padding:30px 56px;display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid {BRAND_RED};">
    <span style="color:{BRAND_RED};font-size:32px;font-weight:bold;letter-spacing:5px;">时政考点打卡</span>
    <span style="color:{MID};font-size:26px;">答案速查</span>
  </div>
  <div style="background:{BRAND_RED};padding:30px 56px;">
    <span style="color:#fff;font-size:44px;font-weight:bold;letter-spacing:3px;">全 20 题答案速查</span>
  </div>
  <div style="flex:1;padding:40px 56px;overflow:hidden;">
    <div style="background:#F3F7FB;border-left:6px solid #2E7D32;border-radius:12px;padding:24px 30px;margin-bottom:30px;">
      <div style="font-size:30px;font-weight:bold;color:#2E7D32;letter-spacing:2px;margin-bottom:8px;">第20题答案 → {ans}</div>
      <div style="font-size:27px;color:#333;line-height:1.6;">{esc(core)}</div>
    </div>
    {rows}
    <div style="font-size:24px;color:#999;text-align:center;margin-top:26px;line-height:1.6;">答案分布 A/B/C/D 各 5 题 · 与真题一致</div>
  </div>
  <div style="padding:30px 56px;border-top:2px solid #eee;display:flex;justify-content:space-between;align-items:center;">
    <span style="color:{MID};font-size:24px;">人民日报 · 时政考点</span>
    <span style="color:{BRAND_RED};font-size:28px;font-weight:bold;">答案速查</span>
  </div>
</div>"""
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>*{{box-sizing:border-box;margin:0;padding:0;}}body{{margin:0;padding:0;background:#fff;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;}}</style>
</head><body>{inner}</body></html>"""


def render_png(html_path, png_path):
    """Chrome headless 渲染 HTML → PNG"""
    cmd = [
        CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--window-size=1242,1660",
        f"--screenshot={png_path}",
        f"file://{html_path}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(png_path) or os.path.getsize(png_path) == 0:
        raise RuntimeError(f"渲染失败: {png_path}\n{r.stderr[-500:]}")
    return png_path


def main():
    global DATE_STR, ARTICLE_TITLE, DATE_DIR, JSON_PATH, GZH_DIR, XHS_DIR, GZH_HTML
    parser = argparse.ArgumentParser(description="公众号HTML + 小红书卡片生成器")
    parser.add_argument("--date", default=DATE_STR, help="日期 YYYY-MM-DD")
    parser.add_argument("--title", default=ARTICLE_TITLE, help="文章标题")
    parser.add_argument("--json", help="题目JSON路径（模拟套题等非每日场景用；默认按 date+title 拼接）")
    parser.add_argument("--outdir", help="输出根目录（默认 物料/<date>/）")
    parser.add_argument("--prefix", help="输出文件名前缀（默认 人民日报<date>）")
    parser.add_argument("--cover-sub", dest="cover_sub", default="时政考点 · 精读一练",
                        help="封面副标题（如：十五五规划 · 备用套题）")
    args = parser.parse_args()
    DATE_STR = args.date
    ARTICLE_TITLE = args.title
    if args.json:
        JSON_PATH = Path(args.json)
        DATE_DIR = Path(args.outdir) if args.outdir else JSON_PATH.parent.parent
    else:
        base = ICLOUD_ROOT / "物料"
        _matches = sorted(base.glob(f"{DATE_STR}_*"))  # 文章聚合目录 物料/<date>_<文章名>
        if _matches:
            DATE_DIR = _matches[0]
            if len(_matches) > 1:
                print(f"⚠️ 当日存在多个文章目录，取第一个: {DATE_DIR}")
        else:
            DATE_DIR = base / DATE_STR
        JSON_PATH = DATE_DIR / "题目" / f"人民日报{DATE_STR}_{ARTICLE_TITLE}_20题.json"
    PREFIX = args.prefix or f"人民日报{DATE_STR}"
    global COVER_SUB, G_VALUE_TXT, G_SOURCE
    COVER_SUB = args.cover_sub
    GZH_DIR = DATE_DIR / "公众号"
    XHS_DIR = DATE_DIR / "小红书" / "图片"
    GZH_HTML = GZH_DIR / f"{PREFIX}_{ARTICLE_TITLE}_20题_公众号.html"

    if not JSON_PATH.exists():
        print(f"❌ 题目文件不存在: {JSON_PATH}")
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data["questions"]
    total = len(questions)
    _vs = data.get("value_score")
    G_VALUE_TXT = f"{_vs.get('total', 92)}/100" if isinstance(_vs, dict) else f"{_vs if isinstance(_vs, (int, float)) else 92}/100"
    G_SOURCE = data.get("source", "人民日报")
    global G_ANCHOR
    G_ANCHOR = data.get("material_anchor", "") or ""
    print(f"数据源: {JSON_PATH} | 共 {total} 题")

    # ── 1. 公众号 HTML ──
    GZH_DIR.mkdir(parents=True, exist_ok=True)
    html = gen_gzh_html(questions)
    GZH_HTML.write_text(html, encoding="utf-8")
    anchor_txt = GZH_DIR / "原文链接.txt"
    anchor_txt.write_text(
        f"《{ARTICLE_TITLE}》\n原文链接：{G_ANCHOR or '（本卷未登记原文链接）'}\n来源：{G_SOURCE}\n",
        encoding="utf-8")
    print(f"✅ 公众号 HTML: {GZH_HTML} ({GZH_HTML.stat().st_size} bytes)")
    print(f"✅ 原文链接TXT: {anchor_txt}")

    # ── 2. 小红书卡片 ──
    XHS_DIR.mkdir(parents=True, exist_ok=True)
    tmpdir = XHS_DIR / "_tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)

    # 封面（红底大标题，仿小红书封面A）
    _cover_lines = [x.strip() for x in ARTICLE_TITLE.split("，") if x.strip()]
    _cover_title_html = "<br>".join(_cover_lines)
    _source_label = data.get("source", "人民日报")
    _vs = data.get("value_score")
    _value_txt = f"{_vs.get('total', 92)}/100" if isinstance(_vs, dict) else f"{_vs if isinstance(_vs, (int, float)) else 92}/100"
    cover_html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>*{{box-sizing:border-box;margin:0;padding:0;}}body{{margin:0;padding:0;background:#fff;}}</style>
</head><body>
<div style="width:{W}px;height:{H}px;background:{BRAND_RED};position:relative;overflow:hidden;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;">
  <div style="position:absolute;top:110px;left:0;right:0;text-align:center;color:rgba(255,255,255,0.85);font-size:50px;letter-spacing:16px;font-weight:500;">{_source_label} · 精读一练</div>
  <div style="position:absolute;top:420px;left:0;right:0;text-align:center;color:#fff;font-size:108px;font-weight:bold;line-height:1.28;letter-spacing:3px;padding:0 60px;">
    {_cover_title_html}
  </div>
  <div style="position:absolute;top:830px;left:0;right:0;text-align:center;color:#ffd9dc;font-size:60px;line-height:1.6;padding:0 90px;font-weight:500;">{args.cover_sub}</div>
  <div style="position:absolute;bottom:175px;left:0;right:0;text-align:center;color:#fff;font-size:62px;letter-spacing:8px;font-weight:bold;">公考上岸 · 20 题</div>
  <div style="position:absolute;bottom:72px;left:0;right:0;text-align:center;color:rgba(255,255,255,0.6);font-size:34px;letter-spacing:4px;">{_source_label} {DATE_STR} · 价值分 {_value_txt}</div>
  <div style="position:absolute;top:0;left:0;width:18px;height:{H}px;background:rgba(255,255,255,0.18);"></div>
  <div style="position:absolute;top:0;right:0;width:18px;height:{H}px;background:rgba(255,255,255,0.18);"></div>
</div>
</body></html>"""
    (tmpdir / "cover.html").write_text(cover_html, encoding="utf-8")
    render_png(tmpdir / "cover.html", XHS_DIR / "00_封面.png")
    print("✅ 封面A: 00_封面.png")

    # 封面B：分色对撞（杂志期刊风，参考申论小红书封面B）
    _title_lines = ARTICLE_TITLE.replace("，", "，\n").split("\n")
    _title_html = "<br>".join(_title_lines) if len(_title_lines) > 1 else ARTICLE_TITLE
    cover_b_html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>*{{box-sizing:border-box;margin:0;padding:0;}}body{{margin:0;padding:0;background:#fff;}}</style>
</head><body>
<div style="width:{W}px;height:{H}px;position:relative;overflow:hidden;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;">
  <div style="position:absolute;top:0;left:0;right:0;height:660px;background:#1F2329;">
    <div style="position:absolute;top:80px;left:0;right:0;text-align:center;color:#D4B896;font-size:36px;letter-spacing:10px;font-weight:500;">{_source_label} · 精读系列</div>
    <div style="position:absolute;top:200px;left:0;right:0;text-align:center;color:#D4B896;font-size:130px;font-weight:bold;letter-spacing:18px;">考点精拆</div>
    <div style="position:absolute;top:440px;left:0;right:0;text-align:center;color:#D4B896;font-size:34px;letter-spacing:8px;opacity:0.85;">政治素养 · 考点 · 金句 · 每日一练</div>
  </div>
  <div style="position:absolute;top:660px;left:0;right:0;bottom:0;background:#FAF6EE;"></div>
  <div style="position:absolute;top:520px;left:50%;transform:translateX(-50%);width:280px;height:280px;border-radius:50%;background:{BRAND_RED};display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 8px 30px rgba(208,2,27,0.3);">
    <div style="color:#fff;font-size:72px;font-weight:bold;letter-spacing:4px;">行测</div>
    <div style="color:#fff;font-size:32px;letter-spacing:6px;margin-top:8px;opacity:0.9;">时政考点</div>
  </div>
  <div style="position:absolute;top:880px;left:80px;display:flex;align-items:center;">
    <div style="width:8px;height:36px;background:{BRAND_RED};margin-right:16px;"></div>
    <span style="color:{BRAND_RED};font-size:36px;font-weight:bold;letter-spacing:4px;">本期考点</span>
  </div>
  <div style="position:absolute;top:970px;left:80px;right:80px;color:#2A2A2A;font-size:72px;font-weight:bold;line-height:1.35;letter-spacing:2px;">
    {_title_html}
  </div>
  <div style="position:absolute;top:1230px;left:80px;color:#888;font-size:38px;letter-spacing:3px;">{args.cover_sub}</div>
  <div style="position:absolute;bottom:80px;left:80px;border:3px solid {BRAND_RED};border-radius:8px;padding:16px 36px;">
    <span style="color:{BRAND_RED};font-size:32px;font-weight:bold;letter-spacing:4px;">20题精拆</span>
  </div>
  <div style="position:absolute;bottom:90px;right:80px;color:#888;font-size:34px;letter-spacing:3px;">{DATE_STR}</div>
</div>
</body></html>"""
    (tmpdir / "cover_b.html").write_text(cover_b_html, encoding="utf-8")
    render_png(tmpdir / "cover_b.html", XHS_DIR / "00_封面B_分色对撞.png")
    print("✅ 封面B: 00_封面B_分色对撞.png")

    # 20 张单题卡
    for i, _ in enumerate(questions, 1):
        html = gen_card_html(questions, i)
        hp = tmpdir / f"card_{i:02d}.html"
        hp.write_text(html, encoding="utf-8")
        pp = XHS_DIR / f"{i:02d}_第{i:02d}题.png"
        render_png(hp, pp)
        print(f"✅ 卡片 {i:02d}/{total}: {pp.name}")

    # 答案速查卡
    ans_html = gen_answer_card_html(questions)
    (tmpdir / "answer.html").write_text(ans_html, encoding="utf-8")
    render_png(tmpdir / "answer.html", XHS_DIR / "21_答案速查.png")
    print("✅ 答案速查: 21_答案速查.png")

    # 清理临时文件
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n" + "=" * 50)
    print(f"完成！公众号 HTML + {total} 张单题卡 + 封面 + 答案速查卡")
    print(f"公众号: {GZH_HTML}")
    print(f"小红书: {XHS_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()
