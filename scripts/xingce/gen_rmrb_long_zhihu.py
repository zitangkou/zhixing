"""
时政考点模拟题 → 公众号长图 + 知乎HTML 生成器

核心设计：答案滞后3题——第N题的答案+精简解析放在第N+3题前面，
用户做到第4题才看到第1题答案，延迟满足感更强。

公众号长图：750px宽竖版长图（仿申论「时评精拆」风格）
知乎HTML：简洁专栏风格，适合知乎发布

用法：
  python3 scripts/xingce/gen_rmrb_long_zhihu.py
"""
import json
import re
import subprocess
import sys
import argparse
import tempfile
from pathlib import Path
from PIL import Image

# ── 路径 ──────────────────────────────────────────────
ICLOUD_ROOT = Path("/Users/dnn/Library/Mobile Documents/com~apple~CloudDocs/政治理论")
DATE_STR = "2026-09-04"
ARTICLE_TITLE = "携手各国发展振兴，改革完善全球治理"
DATE_DIR = ICLOUD_ROOT / "物料" / DATE_STR
JSON_PATH = DATE_DIR / "题目" / f"人民日报{DATE_STR}_{ARTICLE_TITLE}_20题.json"
GZH_DIR = DATE_DIR / "公众号"
ZHIHU_DIR = DATE_DIR / "知乎"

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BRAND_RED = "#D0021B"
PINK_BG = "#FFF5F6"
CREAM_BG = "#FAF9F5"
LIGHT_GRAY = "#F5F5F5"
DARK = "#333333"
MID = "#666666"
LIGHT = "#999999"
GREEN = "#2E7D32"

LONG_W = 750  # 公众号长图标准宽度


def extract_brief_explanation(explanation: str, answer: str) -> str:
    """从完整解析中提取1-2句精简解析"""
    # 提取正确项内容
    correct_match = re.search(r'【正确项】[A-D]：(.+?)(?:\n|$)', explanation)
    correct = correct_match.group(1).strip() if correct_match else ""

    # 提取第一个干扰项分析
    distractor_match = re.search(r'[A-D]项（[^）]+）：(.+?)(?:\n[A-D]项|$)', explanation)
    distractor = distractor_match.group(1).strip() if distractor_match else ""

    parts = []
    if correct:
        # 截断过长的正确项
        if len(correct) > 60:
            correct = correct[:57] + "…"
        parts.append(f"正确项为「{correct}」")
    if distractor:
        if len(distractor) > 50:
            distractor = distractor[:47] + "…"
        parts.append(f"易错：{distractor}")

    return "；".join(parts) if parts else "详见完整解析"


def load_questions():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"]


def render_png(html_path: Path, out_path: Path, width: int = LONG_W, height: int = 20000):
    """Chrome headless 截图，然后裁掉底部空白"""
    cmd = [
        CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=2",
        f"--window-size={width},{height}",
        f"--screenshot={out_path}",
        f"file://{html_path}",
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)

    # 裁掉底部空白（检测非白色行）
    img = Image.open(out_path)
    img = img.convert("RGB")
    pixels = img.load()
    w, h = img.size
    # 从底部往上找第一个非全白行
    crop_h = h
    for y in range(h - 1, -1, -1):
        row_nonwhite = False
        for x in range(0, w, 5):  # 每5像素采样
            r, g, b = pixels[x, y]
            if r < 250 or g < 250 or b < 250:
                row_nonwhite = True
                break
        if row_nonwhite:
            crop_h = y + 20
            break
    if crop_h < h:
        img = img.crop((0, 0, w, crop_h))
        img.save(out_path)
    return img.size


def gen_gzh_long_html(questions) -> str:
    """生成公众号长图HTML（750px宽，答案滞后3题）"""
    total = len(questions)

    # 顶部报头 + 引导卡
    html_parts = [f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{margin:0;padding:0;background:#fff;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;width:{LONG_W}px;}}
.container{{width:{LONG_W}px;padding:0 40px 60px;}}
</style></head><body>
<div class="container">
  <!-- 报头 -->
  <div style="text-align:center;padding-top:50px;">
    <div style="color:{BRAND_RED};font-size:22px;letter-spacing:8px;font-weight:500;">时政考点 · 每日一练</div>
    <div style="color:{BRAND_RED};font-size:56px;font-weight:bold;letter-spacing:6px;margin-top:16px;">考点精拆</div>
    <div style="color:{MID};font-size:20px;letter-spacing:3px;margin-top:12px;">人民日报权威文章 · 行测政治理论模拟题</div>
    <div style="width:120px;height:4px;background:{BRAND_RED};margin:24px auto 0;"></div>
  </div>

  <!-- 引导卡 -->
  <div style="background:{PINK_BG};border-left:6px solid {BRAND_RED};border-radius:8px;padding:28px 30px;margin-top:36px;">
    <div style="color:{BRAND_RED};font-size:20px;font-weight:bold;">【考点精拆】第{DATE_STR}期</div>
    <div style="color:{DARK};font-size:22px;margin-top:12px;line-height:1.6;">今日素材：《{ARTICLE_TITLE}》</div>
    <div style="color:{MID};font-size:18px;margin-top:10px;line-height:1.6;">题量：{total}题｜答案分布 A/B/C/D 各5题｜价值分：92/100（高可用）</div>
    <div style="color:{LIGHT};font-size:16px;margin-top:8px;">💡 答案滞后3题公布，做完再往下翻</div>
  </div>

  <!-- 使用说明 -->
  <div style="background:{LIGHT_GRAY};border-radius:8px;padding:20px 24px;margin-top:24px;">
    <div style="color:{DARK};font-size:18px;line-height:1.8;">
      📖 <b>刷题方式</b>：每题独立思考作答，答案在<b>三题之后</b>公布。全部做完后可对照末尾速查表。
    </div>
  </div>
"""]

    # 题目区：答案滞后3题
    # 第1、2、3题纯题目；第4题前放第1题答案；...第20题前放第17题答案；最后放18、19、20答案+速查
    for i, q in enumerate(questions):
        idx = i + 1  # 1-based

        # 如果 i >= 3，在本题前面放第 i-2 题的答案（滞后3题：第4题前放第1题答案）
        if i >= 3:
            prev_q = questions[i - 3]
            prev_idx = i - 2  # 答案对应的题号
            brief = extract_brief_explanation(prev_q["explanation"], prev_q["answer"])
            html_parts.append(f"""
  <!-- 第{prev_idx}题答案（滞后公布） -->
  <div style="background:#E8F5E9;border-left:6px solid {GREEN};border-radius:8px;padding:20px 24px;margin:32px 0 8px;">
    <div style="color:{GREEN};font-size:18px;font-weight:bold;">✅ 第{prev_idx:02d}题答案：{prev_q['answer']}</div>
    <div style="color:{DARK};font-size:17px;margin-top:8px;line-height:1.7;">{brief}</div>
  </div>
""")

        # 题目卡片
        opts = q["options"]
        opts_html = ""
        for letter in ["A", "B", "C", "D"]:
            if letter in opts:
                opts_html += f'<div style="padding:10px 0;font-size:19px;color:{DARK};line-height:1.6;"><b style="color:{BRAND_RED};">{letter}.</b> {opts[letter]}</div>'

        difficulty = q.get("difficulty", 2)
        diff_label = {1: "简单", 2: "中等", 3: "较难"}.get(difficulty, "中等")
        topic = q.get("topic", "")
        tag = q.get("tag", "")

        html_parts.append(f"""
  <!-- 第{idx}题 -->
  <div style="margin-top:28px;">
    <div style="display:flex;align-items:center;gap:12px;">
      <div style="background:{BRAND_RED};color:#fff;font-size:18px;font-weight:bold;padding:4px 14px;border-radius:4px;">第{idx:02d}题</div>
      <div style="color:{LIGHT};font-size:15px;">{diff_label}｜{topic}</div>
    </div>
    <div style="color:{DARK};font-size:20px;line-height:1.75;margin-top:14px;font-weight:500;">{q['stem']}</div>
    <div style="margin-top:12px;padding-left:8px;">{opts_html}</div>
  </div>
""")

    # 最后三题答案（18、19、20）
    for i in [17, 18, 19]:  # 第18、19、20题（0-based 17、18、19）
        prev_q = questions[i]
        prev_idx = i + 1
        brief = extract_brief_explanation(prev_q["explanation"], prev_q["answer"])
        html_parts.append(f"""
  <div style="background:#E8F5E9;border-left:6px solid {GREEN};border-radius:8px;padding:20px 24px;margin:32px 0 8px;">
    <div style="color:{GREEN};font-size:18px;font-weight:bold;">✅ 第{prev_idx:02d}题答案：{prev_q['answer']}</div>
    <div style="color:{DARK};font-size:17px;margin-top:8px;line-height:1.7;">{brief}</div>
  </div>
""")

    # 全部答案速查表
    answers_html = ""
    for i, q in enumerate(questions):
        idx = i + 1
        answers_html += f'<div style="display:inline-block;width:25%;text-align:center;padding:8px 0;font-size:18px;"><span style="color:{LIGHT};">{idx:02d}.</span> <b style="color:{BRAND_RED};font-size:20px;">{q["answer"]}</b></div>'

    html_parts.append(f"""
  <!-- 答案速查 -->
  <div style="margin-top:40px;">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-size:24px;">📋</span>
      <span style="color:{BRAND_RED};font-size:26px;font-weight:bold;">全部答案速查</span>
    </div>
    <div style="width:100%;height:3px;background:{BRAND_RED};margin-top:10px;"></div>
    <div style="background:{CREAM_BG};border-radius:8px;padding:20px;margin-top:16px;">
      {answers_html}
    </div>
  </div>

  <!-- 底部行动卡 -->
  <div style="background:{BRAND_RED};border-radius:12px;padding:32px;margin-top:40px;text-align:center;">
    <div style="color:#fff;font-size:24px;font-weight:bold;">📚 今日行动清单</div>
    <div style="color:rgba(255,255,255,0.9);font-size:19px;line-height:2;margin-top:16px;">
      ① 独立完成20题，记录错题<br>
      ② 对照解析理解干扰项手法<br>
      ③ 收藏本文，考前复习时政考点
    </div>
  </div>

  <div style="text-align:center;color:{LIGHT};font-size:15px;margin-top:30px;padding-bottom:20px;">
    人民日报 {DATE_STR} · 时政考点每日一练 · 价值分92
  </div>
</div>
</body></html>""")

    return "\n".join(html_parts)


def _gen_question_range_html(questions, start_i, end_i):
    """生成指定题号范围（0-based, 含start不含end）的题目HTML，含滞后3题答案。"""
    parts = []
    for i in range(start_i, end_i):
        q = questions[i]
        idx = i + 1
        if i >= 3:
            prev_q = questions[i - 3]
            prev_idx = i - 2
            brief = extract_brief_explanation(prev_q["explanation"], prev_q["answer"])
            parts.append(f"""
  <div style="background:#E8F5E9;border-left:6px solid {GREEN};border-radius:8px;padding:20px 24px;margin:32px 0 8px;">
    <div style="color:{GREEN};font-size:18px;font-weight:bold;">✅ 第{prev_idx:02d}题答案：{prev_q['answer']}</div>
    <div style="color:{DARK};font-size:17px;margin-top:8px;line-height:1.7;">{brief}</div>
  </div>
""")
        opts = q["options"]
        opts_html = ""
        for letter in ["A", "B", "C", "D"]:
            if letter in opts:
                opts_html += f'<div style="padding:10px 0;font-size:19px;color:{DARK};line-height:1.6;"><b style="color:{BRAND_RED};">{letter}.</b> {opts[letter]}</div>'
        difficulty = q.get("difficulty", 2)
        diff_label = {1: "简单", 2: "中等", 3: "较难"}.get(difficulty, "中等")
        topic = q.get("topic", "")
        parts.append(f"""
  <div style="margin-top:28px;">
    <div style="display:flex;align-items:center;gap:12px;">
      <div style="background:{BRAND_RED};color:#fff;font-size:18px;font-weight:bold;padding:4px 14px;border-radius:4px;">第{idx:02d}题</div>
      <div style="color:{LIGHT};font-size:15px;">{diff_label}｜{topic}</div>
    </div>
    <div style="color:{DARK};font-size:20px;line-height:1.75;margin-top:14px;font-weight:500;">{q['stem']}</div>
    <div style="margin-top:12px;padding-left:8px;">{opts_html}</div>
  </div>
""")
    return "\n".join(parts)


def _gen_long_footer_html(questions):
    """生成最后3题答案 + 速查表 + 底部行动卡。"""
    parts = []
    for i in [17, 18, 19]:
        prev_q = questions[i]
        prev_idx = i + 1
        brief = extract_brief_explanation(prev_q["explanation"], prev_q["answer"])
        parts.append(f"""
  <div style="background:#E8F5E9;border-left:6px solid {GREEN};border-radius:8px;padding:20px 24px;margin:32px 0 8px;">
    <div style="color:{GREEN};font-size:18px;font-weight:bold;">✅ 第{prev_idx:02d}题答案：{prev_q['answer']}</div>
    <div style="color:{DARK};font-size:17px;margin-top:8px;line-height:1.7;">{brief}</div>
  </div>
""")
    answers_html = ""
    for i, q in enumerate(questions):
        idx = i + 1
        answers_html += f'<div style="display:inline-block;width:25%;text-align:center;padding:8px 0;font-size:18px;"><span style="color:{LIGHT};">{idx:02d}.</span> <b style="color:{BRAND_RED};font-size:20px;">{q["answer"]}</b></div>'
    parts.append(f"""
  <div style="margin-top:40px;">
    <div style="display:flex;align-items:center;gap:10px;">
      <span style="font-size:24px;">📋</span>
      <span style="color:{BRAND_RED};font-size:26px;font-weight:bold;">全部答案速查</span>
    </div>
    <div style="width:100%;height:3px;background:{BRAND_RED};margin-top:10px;"></div>
    <div style="background:{CREAM_BG};border-radius:8px;padding:20px;margin-top:16px;">
      {answers_html}
    </div>
  </div>
  <div style="background:{BRAND_RED};border-radius:12px;padding:32px;margin-top:40px;text-align:center;">
    <div style="color:#fff;font-size:24px;font-weight:bold;">📚 今日行动清单</div>
    <div style="color:rgba(255,255,255,0.9);font-size:19px;line-height:2;margin-top:16px;">
      ① 独立完成20题，记录错题<br>
      ② 对照解析理解干扰项手法<br>
      ③ 收藏本文，考前复习时政考点
    </div>
  </div>
  <div style="text-align:center;color:{LIGHT};font-size:15px;margin-top:30px;padding-bottom:20px;">
    人民日报 {DATE_STR} · 时政考点每日一练 · 价值分92
  </div>
""")
    return "\n".join(parts)


def gen_long_split_html(questions, part_idx, total_parts=4):
    """生成分段长图HTML。part_idx从0起。
    第0段：完整报头+引导+第1-5题
    第1-2段：简化页眉+第6-10/11-15题
    第3段：简化页眉+第16-20题+最后答案+速查+底部
    """
    total = len(questions)
    per = total // total_parts  # 5
    start_i = part_idx * per
    end_i = (part_idx + 1) * per if part_idx < total_parts - 1 else total

    if part_idx == 0:
        # 第一段：完整报头
        header = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{margin:0;padding:0;background:#fff;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;width:{LONG_W}px;}}
.container{{width:{LONG_W}px;padding:0 40px 60px;}}
</style></head><body>
<div class="container">
  <div style="text-align:center;padding-top:50px;">
    <div style="color:{BRAND_RED};font-size:22px;letter-spacing:8px;font-weight:500;">时政考点 · 每日一练</div>
    <div style="color:{BRAND_RED};font-size:56px;font-weight:bold;letter-spacing:6px;margin-top:16px;">考点精拆</div>
    <div style="color:{MID};font-size:20px;letter-spacing:3px;margin-top:12px;">人民日报权威文章 · 行测政治理论模拟题</div>
    <div style="width:120px;height:4px;background:{BRAND_RED};margin:24px auto 0;"></div>
  </div>
  <div style="background:{PINK_BG};border-left:6px solid {BRAND_RED};border-radius:8px;padding:28px 30px;margin-top:36px;">
    <div style="color:{BRAND_RED};font-size:20px;font-weight:bold;">【考点精拆】第{DATE_STR}期</div>
    <div style="color:{DARK};font-size:22px;margin-top:12px;line-height:1.6;">今日素材：《{ARTICLE_TITLE}》</div>
    <div style="color:{MID};font-size:18px;margin-top:10px;line-height:1.6;">题量：{total}题｜答案分布 A/B/C/D 各5题｜价值分：92/100（高可用）</div>
    <div style="color:{LIGHT};font-size:16px;margin-top:8px;">💡 答案滞后3题公布，做完再往下翻（共{total_parts}张）</div>
  </div>
  <div style="background:{LIGHT_GRAY};border-radius:8px;padding:20px 24px;margin-top:24px;">
    <div style="color:{DARK};font-size:18px;line-height:1.8;">
      📖 <b>刷题方式</b>：每题独立思考作答，答案在<b>三题之后</b>公布。全部做完后可对照末尾速查表。
    </div>
  </div>
"""
    else:
        # 后续段：简化页眉
        start_q = start_i + 1
        end_q = end_i
        header = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{margin:0;padding:0;background:#fff;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;width:{LONG_W}px;}}
.container{{width:{LONG_W}px;padding:0 40px 60px;}}
</style></head><body>
<div class="container">
  <div style="display:flex;align-items:center;justify-content:space-between;padding-top:36px;padding-bottom:20px;border-bottom:3px solid {BRAND_RED};">
    <div style="color:{BRAND_RED};font-size:22px;font-weight:bold;letter-spacing:4px;">考点精拆 · 第{start_q:02d}-{end_q:02d}题</div>
    <div style="color:{LIGHT};font-size:16px;">第{DATE_STR}期 · {part_idx + 1}/{total_parts}</div>
  </div>
"""

    body = _gen_question_range_html(questions, start_i, end_i)
    footer = _gen_long_footer_html(questions) if part_idx == total_parts - 1 else ""
    return header + body + footer + "\n</div></body></html>"


def gen_zhihu_html(questions) -> str:
    """生成知乎风格HTML（简洁长文，答案滞后3题）"""
    total = len(questions)

    html_parts = [f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>时政考点每日一练｜{ARTICLE_TITLE}（20题）</title>
<style>
body{{max-width:720px;margin:0 auto;padding:40px 24px;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;color:#1a1a1a;line-height:1.8;background:#fff;}}
h1{{font-size:28px;font-weight:700;margin-bottom:8px;line-height:1.4;}}
.meta{{color:#8590a6;font-size:14px;margin-bottom:32px;padding-bottom:16px;border-bottom:1px solid #ebebeb;}}
.lead{{background:#f6f6f6;border-radius:8px;padding:16px 20px;font-size:15px;color:#646464;margin-bottom:32px;line-height:1.7;}}
.question{{margin:36px 0;}}
.q-num{{display:inline-block;background:{BRAND_RED};color:#fff;font-size:14px;font-weight:600;padding:3px 10px;border-radius:4px;margin-right:10px;}}
.q-tag{{color:#8590a6;font-size:13px;}}
.q-stem{{font-size:17px;font-weight:500;margin:12px 0;line-height:1.8;}}
.q-opt{{padding:6px 0;font-size:16px;color:#333;}}
.q-opt b{{color:{BRAND_RED};}}
.answer-block{{background:#f0fff4;border-left:4px solid #2E7D32;border-radius:4px;padding:14px 18px;margin:28px 0 8px;font-size:15px;line-height:1.7;}}
.answer-block .ans-label{{color:#2E7D32;font-weight:600;font-size:15px;}}
.answer-table{{width:100%;border-collapse:collapse;margin:24px 0;font-size:15px;}}
.answer-table td{{border:1px solid #ebebeb;padding:10px;text-align:center;}}
.answer-table .ans{{color:{BRAND_RED};font-weight:700;font-size:18px;}}
h2{{font-size:22px;font-weight:700;margin:40px 0 16px;padding-bottom:8px;border-bottom:2px solid {BRAND_RED};}}
.footer{{margin-top:48px;padding-top:20px;border-top:1px solid #ebebeb;color:#8590a6;font-size:13px;text-align:center;}}
</style></head><body>

<h1>时政考点每日一练｜{ARTICLE_TITLE}</h1>
<div class="meta">人民日报 {DATE_STR} · 行测政治理论模拟题 · {total}题 · 价值分 92/100</div>

<div class="lead">
📖 本文基于人民日报头版权威文章生成 {total} 道政治理论模拟题，题型、干扰项手法均对标国考真题。<br>
<b>刷题方式</b>：答案滞后3题公布——做到第4题时才会看到第1题答案。建议独立作答后再往下翻。全部答案见文末速查表。
</div>
"""]

    for i, q in enumerate(questions):
        idx = i + 1

        if i >= 3:
            prev_q = questions[i - 3]
            prev_idx = i - 2
            brief = extract_brief_explanation(prev_q["explanation"], prev_q["answer"])
            html_parts.append(f"""
<div class="answer-block">
  <span class="ans-label">✅ 第{prev_idx:02d}题答案：{prev_q['answer']}</span><br>
  {brief}
</div>
""")

        opts = q["options"]
        opts_html = ""
        for letter in ["A", "B", "C", "D"]:
            if letter in opts:
                opts_html += f'<div class="q-opt"><b>{letter}.</b> {opts[letter]}</div>'

        difficulty = q.get("difficulty", 2)
        diff_label = {1: "简单", 2: "中等", 3: "较难"}.get(difficulty, "中等")
        topic = q.get("topic", "")

        html_parts.append(f"""
<div class="question">
  <span class="q-num">第{idx:02d}题</span><span class="q-tag">{diff_label}｜{topic}</span>
  <div class="q-stem">{q['stem']}</div>
  {opts_html}
</div>
""")

    # 最后三题答案（18、19、20）
    for i in [17, 18, 19]:
        prev_q = questions[i]
        prev_idx = i + 1
        brief = extract_brief_explanation(prev_q["explanation"], prev_q["answer"])
        html_parts.append(f"""
<div class="answer-block">
  <span class="ans-label">✅ 第{prev_idx:02d}题答案：{prev_q['answer']}</span><br>
  {brief}
</div>
""")

    # 答案速查表
    rows = ""
    for row_start in range(0, total, 5):
        cells = ""
        for j in range(5):
            idx = row_start + j + 1
            if idx <= total:
                q = questions[idx - 1]
                cells += f"<td>{idx:02d}<br><span class='ans'>{q['answer']}</span></td>"
            else:
                cells += "<td></td>"
        rows += f"<tr>{cells}</tr>"

    html_parts.append(f"""
<h2>📋 全部答案速查</h2>
<table class="answer-table">{rows}</table>

<div class="footer">
  人民日报 {DATE_STR} · 时政考点每日一练 · 基于权威文章生成，仅供学习参考<br>
  答案分布：A/B/C/D 各5题 · 难度：简单3/中等13/较难4
</div>
</body></html>""")

    return "\n".join(html_parts)


def main():
    global DATE_STR, ARTICLE_TITLE, DATE_DIR, JSON_PATH, GZH_DIR, ZHIHU_DIR
    parser = argparse.ArgumentParser(description="公众号长图 + 知乎HTML生成器（答案滞后3题）")
    parser.add_argument("--date", default=DATE_STR, help="日期 YYYY-MM-DD")
    parser.add_argument("--title", default=ARTICLE_TITLE, help="文章标题")
    args = parser.parse_args()
    DATE_STR = args.date
    ARTICLE_TITLE = args.title
    DATE_DIR = ICLOUD_ROOT / "物料" / DATE_STR
    JSON_PATH = DATE_DIR / "题目" / f"人民日报{DATE_STR}_{ARTICLE_TITLE}_20题.json"
    GZH_DIR = DATE_DIR / "公众号"
    ZHIHU_DIR = DATE_DIR / "知乎"

    if not JSON_PATH.exists():
        print(f"❌ 题目文件不存在: {JSON_PATH}")
        sys.exit(1)

    GZH_DIR.mkdir(parents=True, exist_ok=True)
    ZHIHU_DIR.mkdir(parents=True, exist_ok=True)

    questions = load_questions()
    print(f"加载 {len(questions)} 题")

    # 1. 公众号超长图（保留完整版）
    print("\n=== 公众号超长图 ===")
    long_html = gen_gzh_long_html(questions)
    with tempfile.TemporaryDirectory() as tmpdir:
        hp = Path(tmpdir) / "long.html"
        hp.write_text(long_html, encoding="utf-8")
        out_png = GZH_DIR / f"人民日报{DATE_STR}_{ARTICLE_TITLE}_20题_公众号长图.png"
        size = render_png(hp, out_png)
        print(f"✅ 超长图: {out_png.name} ({size[0]}x{size[1]})")

    # 1b. 公众号分段长图（拆成4张，加载更快）
    print("\n=== 公众号分段长图（4张） ===")
    total_parts = 4
    with tempfile.TemporaryDirectory() as tmpdir:
        for part_idx in range(total_parts):
            split_html = gen_long_split_html(questions, part_idx, total_parts)
            hp = Path(tmpdir) / f"split_{part_idx}.html"
            hp.write_text(split_html, encoding="utf-8")
            out_png = GZH_DIR / f"人民日报{DATE_STR}_{ARTICLE_TITLE}_20题_公众号长图_{part_idx + 1:02d}.png"
            size = render_png(hp, out_png)
            print(f"✅ 分段{part_idx + 1}/{total_parts}: {out_png.name} ({size[0]}x{size[1]})")

    # 2. 知乎HTML
    print("\n=== 知乎HTML ===")
    zhihu_html = gen_zhihu_html(questions)
    out_html = ZHIHU_DIR / f"人民日报{DATE_STR}_{ARTICLE_TITLE}_20题_知乎.html"
    out_html.write_text(zhihu_html, encoding="utf-8")
    print(f"✅ 知乎HTML: {out_html.name}")

    print("\n🎉 全部完成")


if __name__ == "__main__":
    main()
