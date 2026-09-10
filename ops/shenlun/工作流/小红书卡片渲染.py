#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书卡片渲染（路径 B：重新排版 · v2.15，v2.18 平行产出增强）

针对小红书 1242×1660 竖版重新排版公众号内容，文字 100% 准确（HTML 渲染），
版式可控（绕开 Canva AI 直出 bug）。

产出：
- 封面A 双版本：经典大红（01_封面A_大标题品牌色.png）+ 分色对撞（01_封面A_分色对撞.png）
- 正文卡：每个语义块一张

【v2.18 平行产出增强（2026-09-05，向后兼容）】
- v2.18 公众号 HTML（含「考题定位」章节）自动进入 v2.18 模式：
  ① 章节合并：「考题定位」+「全文骨架速览」→「🎯 立意·骨架」；
    「迁移指南」+「素材速记卡」→「🎯 迁移·速记」——解决短内容卡空旷问题，8 个 h2 → 6 张正文卡（+双封面=8 卡/篇）
  ② 高度自适应阶梯省略：渲染-测量-降级循环，内容超出卡片安全区时按章节语义阶梯省略
    （论证骨架：删小结行 → 保留分论点1其余省略；规范词表截 8 行；语录/句式尾部截断；
     迁移·速记：删金句/案例行），所有省略处显式加「……」标记，绝不静默截断
  ③ 渲染前剔除「v2.18 新增」类预览标签，避免混入卡片正文
- v2.17 公众号 HTML（6 章节）行为不变（7 卡/篇），但同样享受溢出检测保护

用法：
python3 工作流/小红书卡片渲染.py <公众号HTML路径> --out <输出目录>
"""
import os
import re
import sys
import argparse
import asyncio
from bs4 import BeautifulSoup, Tag
from playwright.async_api import async_playwright

BRAND_RED = '#D0021B'
PINK_BG = '#FFF5F6'
CREAM_BG = '#FAF9F5'
DARK = '#333333'
MID = '#666666'
W, H = 1242, 1660

ELIDE_NOTE = '…… 完整版见公众号：杜衡阁'  # 品牌引导（用户定 2026-09-05）
PREVIEW_TAG = re.compile(r'<span[^>]*>[^<]*v2\.18[^<]*</span>')


def _strip_preview_tags(node):
    """剔除 HTML 里的「v2.18 新增」类预览标签 span（防混入卡片正文）"""
    return PREVIEW_TAG.sub('', str(node))


def _drop_lines(html, keywords):
    """删除包含任一关键词的 <p> 行，并清理删空了的顶层 <div> 壳（避免残留空边框）"""
    soup = BeautifulSoup(html, 'lxml')
    for p in soup.find_all('p'):
        txt = p.get_text()
        if any(k in txt for k in keywords):
            p.decompose()
    for div in soup.find_all('div'):
        if not div.get_text(strip=True) and not div.find(['table', 'img']):
            div.decompose()
    return str(soup)


def _note_p(text=ELIDE_NOTE):
    # font-size 用原始尺度（13px），scale_content 放大 2.2 倍后 ≈29px
    return f'<p style="color:#999;font-size:13px;margin-top:8px;">{text}</p>'


def _truncate_table_rows(html, keep, note):
    """规范词等表格：数据行超 keep 行时截断并追加省略行"""
    soup = BeautifulSoup(html, 'lxml')
    changed = False
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) <= keep + 1:  # 表头 + keep 行以内不动
            continue
        omitted = len(rows) - 1 - keep
        for tr in rows[keep + 1:]:
            tr.decompose()
        note_tr = soup.new_tag('tr')
        td = soup.new_tag('td')
        td['colspan'] = '3'
        td['style'] = 'color:#999;padding:8px;border:1px solid #ddd;'
        td.string = f'…… 其余 {omitted} 个见正文长图'
        note_tr.append(td)
        table.append(note_tr)
        changed = True
    return str(soup), changed


def apply_ladder(title, nodes, level):
    """按章节语义应用第 level 级省略（level=0 完整）。nodes: List[str]。返回 List[str]"""
    if level <= 0:
        return nodes
    is_div = lambda n: n.lstrip().startswith('<div')
    if '论证骨架' in title:
        # 偏完整阶梯（用户定 2026-09-05）：先逐级删行保住全部分论点，最后才省略块
        if level == 1:      # 删各分论点「小结」行
            return [_drop_lines(n, ['小结']) if is_div(n) else n for n in nodes] + [_note_p('…… 完整版见公众号：杜衡阁')]
        if level == 2:      # 再删「论据」行（保留 标题/提出论点/论证方法/套用模板）
            return [_drop_lines(n, ['小结', '论据']) if is_div(n) else n for n in nodes] + [_note_p('…… 完整版见公众号：杜衡阁')]
        if level == 3:      # 再删「提出论点」行（保留 标题/论证方法/套用模板——教学核心三块齐全）
            return [_drop_lines(n, ['小结', '论据', '提出论点']) if is_div(n) else n for n in nodes] + [_note_p('…… 完整版见公众号：杜衡阁')]
        # level>=4：保留分论点1 完整块，其余分论点块整体省略
        out, kept_first = [], False
        for n in nodes:
            if is_div(n):
                if not kept_first:
                    out.append(n)
                    kept_first = True
                continue
            out.append(n)
        out.append(_note_p('…… 分论点2/3 完整版见公众号：杜衡阁'))
        return out
    if '规范词' in title:
        out, changed = [], False
        for n in nodes:
            if '<table' in n:
                n2, ch = _truncate_table_rows(n, keep=8, note=ELIDE_NOTE)
                out.append(n2)
                changed = changed or ch
            else:
                out.append(n)
        return out if changed else nodes
    if '句式' in title:
        if level == 1:      # 每组删「仿写」行，保留全部句式组
            return [_drop_lines(n, ['仿写']) if is_div(n) else n for n in nodes] + [_note_p('…… 仿写示例见公众号：杜衡阁')]
        # level>=2：删仿写 + 尾部少 1 组
        idx = [k for k, n in enumerate(nodes) if is_div(n)]
        keep_n = max(1, len(idx) - (level - 1))
        out = [_drop_lines(n, ['仿写']) if is_div(n) and k in set(idx[:keep_n]) else n
               for k, n in enumerate(nodes) if k in set(idx[:keep_n]) or not is_div(n)]
        out.append(_note_p('…… 更多句式见公众号：杜衡阁'))
        return out
    if '迁移·速记' in title and level == 1:
        # 先删速记卡的 金句/案例 行（仿写示范与行动清单保留）
        return [_drop_lines(n, ['💬', '📚']) if is_div(n) else n for n in nodes]
    # 通用阶梯：从尾部整块删除 level 个顶层 <div> 条目（语录条目等）
    idx = [k for k, n in enumerate(nodes) if is_div(n)]
    if level <= len(idx):
        drop = set(idx[len(idx) - level:])
        out = [n for k, n in enumerate(nodes) if k not in drop]
        out.append(_note_p())
        return out
    return nodes


def max_ladder_level(title):
    """各卡最大降级档位（防死循环兜底）"""
    if '论证骨架' in title:
        return 4
    if '句式' in title:
        return 2
    if '规范词' in title:
        return 1
    if '迁移·速记' in title:
        return 2
    return 3


def is_v18(sections):
    """v2.18 公众号 HTML 判别：章节含「考题定位」"""
    return any('考题定位' in s['title'] for s in sections)


def merge_v18_sections(sections):
    """v2.18 章节合并：考题定位+骨架 → 立意·骨架；迁移指南+素材速记 → 迁移·速记（解决短卡空旷）"""
    merged, i = [], 0
    while i < len(sections):
        s = sections[i]
        nxt = sections[i + 1] if i + 1 < len(sections) else None
        if nxt and '考题定位' in s['title'] and '骨架' in nxt['title']:
            merged.append({'title': '🎯 立意·骨架', 'content': s['content'] + nxt['content']})
            i += 2
        elif nxt and '迁移指南' in s['title'] and '速记' in nxt['title']:
            merged.append({'title': '🎯 迁移·速记', 'content': s['content'] + nxt['content']})
            i += 2
        else:
            merged.append(s)
            i += 1
    return merged


# ---------- 内容解析 ----------

def parse_article(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml')
    body = soup.find('body')
    body_divs = [c for c in body.children if isinstance(c, Tag) and c.name == 'div']
    if len(body_divs) <= 1:
        # 新版（v2.16+）：body 下唯一容器 div
        top = body_divs[0] if body_divs else body
        children = [c for c in top.children if isinstance(c, Tag)]
        legacy = False
    else:
        # 老版（v2.14/2.15）：body 下平级多 div（无总容器），首元素即信息卡
        children = [c for c in body.children if isinstance(c, Tag)]
        legacy = True
    data = {'title': '', 'issue': '', 'theme': '', 'sections': []}

    # 元素0：头部（标题；老版无独立报头，置空）
    if legacy:
        data['header_lines'] = []
    else:
        h0 = children[0]
        data['header_lines'] = [d.get_text(strip=True) for d in h0.find_all('div')]

    # 元素1：信息卡（期号/标题/主题；老版为平级首元素）
    h1 = children[0] if legacy else children[1]
    p1 = h1.find('p')
    if p1:
        txt = p1.get_text(' ', strip=True)
        m = re.search(r'第([\d-]+)期', txt)
        data['issue'] = m.group(1) if m else ''
        m2 = re.search(r'《(.+?)》', txt)
        data['title'] = m2.group(1) if m2 else ''
        # 核心主题/适用
        theme_line = [l for l in txt.split(' ') if '核心主题' in l or '适用' in l]
        data['theme'] = ' '.join(theme_line) if theme_line else ''

    # 元素2：原文摘录（老版为平级第二元素，即开篇导语引用）
    h2 = children[1] if legacy else children[2]
    quote_p = h2.find('p')
    data['quote'] = quote_p.get_text(' ', strip=True) if quote_p else ''
    cite_p = h2.find_all('p')
    data['cite'] = cite_p[-1].get_text(strip=True) if len(cite_p) > 1 else ''

    # 后续：章节（h2 + 内容；老版 h2 从元素2 开始）
    sections = []
    i = 2 if legacy else 3
    while i < len(children):
        c = children[i]
        if c.name == 'h2':
            title = c.get_text(strip=True)
            # 收集后续非 h2 内容
            content = []
            j = i + 1
            while j < len(children) and children[j].name != 'h2':
                if children[j].name != 'p' or not ('上一篇' in children[j].get_text() or '下一篇' in children[j].get_text()):
                    content.append(children[j])
                j += 1
            sections.append({'title': title, 'content': content})
            i = j
        else:
            i += 1
    data['sections'] = sections
    return data


# ---------- 模板 ----------

def html_doc(inner, width=W, height=H):
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{margin:0;padding:0;background:#fff;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;}}
</style></head><body>{inner}</body></html>"""


# 封面A「分色对撞」配色
INK = '#20242C'
GOLD = '#F2D9A0'
GOLD_DIM = '#E6C478'
RED_SEAL = '#C41E24'
CREAM_PAPER = '#FBF6EC'
TITLE_DARK = '#2B2B2B'
BODY_GRAY = '#5A5248'
MUTE_GRAY = '#8A7A5E'


def cover_a(data):
    """封面A：分色对撞（上墨黑品牌区 + 下米白标题区 + 红章「申论·精读」）"""
    title = data['title']
    issue = data['issue']
    theme = data['theme']
    # 拆解视角一句话：取「核心主题：」之后、｜/| 之前的部分
    hook = re.sub(r'^核心主题[:：]\s*', '', theme or '')
    hook = re.split(r'[｜|]', hook)[0].strip()
    if not hook:
        hook = theme
    date_label = issue if issue else ''
    inner = f"""
<div style="width:{W}px;height:{H}px;background:{CREAM_PAPER};display:flex;flex-direction:column;overflow:hidden;">
  <div style="height:430px;background:{INK};display:flex;flex-direction:column;align-items:center;justify-content:center;">
    <div style="color:{GOLD_DIM};font-size:24px;letter-spacing:10px;margin-bottom:42px;">人民日报评论 · 精读系列</div>
    <div style="color:{GOLD};font-size:118px;font-weight:bold;letter-spacing:30px;margin-bottom:40px;">时评精拆</div>
    <div style="color:rgba(242,217,160,0.9);font-size:28px;letter-spacing:12px;">申论素材 · 拆解 · 金句 · 句式</div>
  </div>
  <div style="flex:1;display:flex;flex-direction:column;align-items:center;padding:0 90px;">
    <div style="width:300px;height:300px;margin-top:56px;background:{RED_SEAL};border:8px solid {CREAM_PAPER};border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;">
      <div style="color:#fff;font-size:68px;font-weight:bold;letter-spacing:6px;">申论</div>
      <div style="color:#FFD9DC;font-size:26px;letter-spacing:8px;margin-top:4px;">精读</div>
    </div>
    <div style="align-self:flex-start;color:{RED_SEAL};font-size:30px;letter-spacing:6px;font-weight:bold;margin-top:64px;">▍本期拆解</div>
    <div style="align-self:flex-start;color:{TITLE_DARK};font-size:92px;font-weight:bold;line-height:1.42;letter-spacing:2px;margin-top:30px;">{title}</div>
    <div style="align-self:flex-start;color:{BODY_GRAY};font-size:34px;line-height:1.7;margin-top:44px;">{hook}</div>
    <div style="flex:1;"></div>
    <div style="align-self:stretch;display:flex;align-items:center;justify-content:space-between;margin-bottom:54px;">
      <span style="border:2px solid {RED_SEAL};color:{RED_SEAL};font-size:26px;letter-spacing:6px;padding:10px 26px;border-radius:6px;">原文精拆</span>
      <span style="color:{MUTE_GRAY};font-size:26px;letter-spacing:3px;">{date_label}</span>
    </div>
  </div>
</div>"""
    return html_doc(inner)


def cover_a_classic(data):
    """封面A（经典版）：满版品牌红 + 超大标题 + 核心主题副标题 + 期号"""
    title = data['title']
    issue = data['issue']
    theme = data['theme']
    inner = f"""
<div style="width:{W}px;height:{H}px;background:{BRAND_RED};position:relative;overflow:hidden;">
  <div style="position:absolute;top:90px;left:0;right:0;text-align:center;color:rgba(255,255,255,0.85);font-size:30px;letter-spacing:14px;">人民时评 · 精读系列</div>
  <div style="position:absolute;top:380px;left:0;right:0;text-align:center;color:#fff;font-size:120px;font-weight:bold;line-height:1.3;letter-spacing:3px;padding:0 80px;">
    {title}
  </div>
  <div style="position:absolute;top:1100px;left:0;right:0;text-align:center;color:#ffd9dc;font-size:40px;line-height:1.7;padding:0 100px;">{theme}</div>
  <div style="position:absolute;bottom:140px;left:0;right:0;text-align:center;color:#fff;font-size:38px;letter-spacing:6px;">【时评精拆】第{issue}期</div>
  <div style="position:absolute;bottom:60px;left:0;right:0;text-align:center;color:rgba(255,255,255,0.55);font-size:24px;letter-spacing:3px;">人民日报评论文章 · 申论素材拆解</div>
  <div style="position:absolute;top:0;left:0;width:18px;height:{H}px;background:rgba(255,255,255,0.18);"></div>
  <div style="position:absolute;top:0;right:0;width:18px;height:{H}px;background:rgba(255,255,255,0.18);"></div>
</div>"""
    return html_doc(inner)


def cover_b(data, children_0_2):
    """封面B：沿用公众号头部（元素0/1/2），但字号放大到小红书尺度"""
    # 对每个元素做字号放大
    scaled = []
    for e in children_0_2:
        s = str(e)
        # 标题28→54，副标题12→26，正文14→30，斜体13→30
        s = re.sub(r'font-size:(\d+)px', lambda m: f'font-size:{int(int(m.group(1))*2.2)}px', s)
        s = re.sub(r'padding:(\d+)px', lambda m: f'padding:{int(int(m.group(1))*1.8)}px', s)
        scaled.append(s)
    inner_html = '\n'.join(scaled)
    return html_doc(f"""
<div style="width:{W}px;height:{H}px;background:#fff;display:flex;align-items:center;justify-content:center;">
  <div style="width:1140px;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;color:#333;">
    {inner_html}
  </div>
</div>""")


def scale_content(content_nodes, scale_body=2.2):
    """内容节点字号/padding 等比放大到卡片尺度，返回 HTML 字符串"""
    scaled = []
    for e in content_nodes:
        s = str(e)
        s = re.sub(r'font-size:(\d+)px',
                   lambda m: f'font-size:{int(int(m.group(1))*scale_body)}px', s)
        s = re.sub(r'padding:(\d+)px',
                   lambda m: f'padding:{int(int(m.group(1))*1.8)}px', s)
        scaled.append(s)
    return '\n'.join(scaled)


def section_card(data, title, content_html, page, total):
    """正文卡：章节标题 + 内容重排（内容区带 id=card-content 供溢出测量）"""
    inner = f"""
<div style="width:{W}px;height:{H}px;background:#fff;position:relative;display:flex;flex-direction:column;">
  <div style="background:{PINK_BG};padding:28px 56px;display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid {BRAND_RED};">
    <span style="color:{BRAND_RED};font-size:34px;font-weight:bold;letter-spacing:5px;">时评精拆</span>
    <span style="color:{MID};font-size:28px;">第{data['issue']}期 · {data['title'][:16]}</span>
  </div>
  <div style="background:{BRAND_RED};padding:28px 56px;">
    <span style="color:#fff;font-size:52px;font-weight:bold;letter-spacing:3px;">{title}</span>
  </div>
  <div id="card-content" style="flex:1;padding:50px 56px;overflow:hidden;">
    <div style="font-size:38px;line-height:1.7;color:{DARK};">
      {content_html}
    </div>
  </div>
  <div style="padding:28px 56px;border-top:2px solid #eee;display:flex;justify-content:space-between;align-items:center;">
    <span style="color:{MID};font-size:26px;">人民日报评论 · 申论素材</span>
    <span style="color:{BRAND_RED};font-size:30px;font-weight:bold;">{page}/{total}</span>
  </div>
</div>"""
    return html_doc(inner)


JS_MEASURE = """() => { const el = document.getElementById('card-content');
  return el ? {sh: el.scrollHeight, ch: el.clientHeight} : {sh: 0, ch: 0}; }"""


def rescale_content_html(content_nodes, scale_title=2.2, scale_body=2.0):
    """把公众号内容块的字号等比放大到小红书卡片尺度。"""
    out = []
    for node in content_nodes:
        node = str(node)
        # 替换 font-size 数值
        def repl(m):
            n = float(m.group(1))
            # 标题(17px)放大2.2，正文(13-15px)放大2.0
            if n >= 16:
                return f'font-size:{int(n*scale_title)}px'
            else:
                return f'font-size:{int(n*scale_body)}px'
        node = re.sub(r'font-size:(\d+(?:\.\d+)?)px', repl, node)
        # padding 也放大一点
        node = re.sub(r'padding:(\d+)px', lambda m: f'padding:{int(m.group(1))*1.6}px', node)
        out.append(node)
    return '\n'.join(out)


# ---------- 渲染 ----------

async def render_all(html_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    data = parse_article(html_path)
    sections = data['sections']
    v18 = is_v18(sections)

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(viewport={'width': W, 'height': H})

        # 封面：双版本并出（经典大红 + 分色对撞），人工自主选择
        await page.set_content(cover_a_classic(data), wait_until='networkidle')
        await page.evaluate("document.fonts.ready")
        await page.screenshot(path=os.path.join(out_dir, '01_封面A_大标题品牌色.png'))
        print('已生成 01_封面A_大标题品牌色.png（经典大红版）')
        await page.set_content(cover_a(data), wait_until='networkidle')
        await page.evaluate("document.fonts.ready")
        await page.screenshot(path=os.path.join(out_dir, '01_封面A_分色对撞.png'))
        print('已生成 01_封面A_分色对撞.png（分色对撞版）')

        if v18:
            sections = merge_v18_sections(sections)
            print(f'v2.18 模式：章节合并 → {len(sections)} 张正文卡（立意·骨架 / 迁移·速记）')

        # 正文卡：渲染-测量-降级循环（内容超出卡片安全区时按阶梯省略）
        total = len(sections)
        for i, sec in enumerate(sections, 1):
            title = re.sub(r'\s*v2\.18\s*(新增|穷尽开采)\s*', '', sec['title']).strip()
            nodes = [_strip_preview_tags(n) for n in sec['content']]
            level = 0
            prev_sh = None
            while True:
                content_html = scale_content(apply_ladder(title, nodes, level))
                await page.set_content(section_card(data, title, content_html, i, total),
                                       wait_until='networkidle')
                await page.evaluate("document.fonts.ready")
                m = await page.evaluate(JS_MEASURE)
                overflow = m['sh'] > m['ch'] + 4
                if not overflow:
                    if level > 0:
                        print(f'  ↳ 内容超限，按 L{level} 阶梯省略后适配（{title[:12]}）')
                    break
                # 降级无进展（内容高度未减小）或已到该卡最大档位 → 停止
                if level >= max_ladder_level(title) or (prev_sh is not None and m['sh'] >= prev_sh):
                    print(f'  ⚠️ {title[:12]} 已到 L{level} 档仍超限（sh={m["sh"]}/ch={m["ch"]}），按现状出卡（人工复核）')
                    break
                prev_sh = m['sh']
                level += 1
            out = os.path.join(out_dir, f'{i+1:02d}_正文_{i}.png')
            await page.screenshot(path=out)
            print(f'已生成 {i+1:02d}_正文_{i}.png  ({title[:20]})')

        await browser.close()


async def main_async(html_path, out_dir):
    await render_all(html_path, out_dir)


def main():
    ap = argparse.ArgumentParser(description='小红书卡片渲染（路径B 重新排版）')
    ap.add_argument('html', help='公众号 HTML 路径')
    ap.add_argument('--out', required=True, help='输出目录')
    args = ap.parse_args()
    asyncio.run(main_async(args.html, args.out))


if __name__ == '__main__':
    main()
