#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML → 纯文本结构文件（完整版 / 简化版）

把「时评精拆」公众号 HTML（A套）的内容提取为纯文本，
用基本缩进 + 换行展示内容层级结构。

完整版：全部章节内容（多平台发布正文源）。
简化版（--brief）：适配小红书 1000 字限制——
  · 头部只留期号+标题+精简主题
  · 原文摘录：首尾金句，删出处
  · 骨架速览：只留引题/总论点/分论点1/总结
  · 规范词：保留 2 个
  · 论证骨架：只留分论点1，论据精简
  · 万能句式：只留句式1，删仿写
  · 速记卡：去emoji+案例精简+删重复仿写
  · 行动清单：去emoji+精简
  · 全局缩进压缩为 1/2 空格
【v2.18 平行产出适配（2026-09-05）】brief 模式对 v2.18 新增区块精简：
  · 考题定位：只留主题归类行（标题机关/立意路径省略）
  · 语录：只留 1 条
  · 迁移指南：只留 适用考题+套用警示 两行（仿写示范省略）
  · 全局剔除「v2.18 新增/穷尽开采/新增展示」预览标签文字

用法：
python3 工作流/HTML转内容文本.py <公众号HTML路径> [--out <输出txt路径>] [--brief]
"""
import os
import re
import argparse
from bs4 import BeautifulSoup, Tag

# 章节 emoji 清理（保留中文章节名）
def clean_emoji(s: str) -> str:
    s = re.sub(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\ufe0f\u200d]', '', s)
    return s.strip()


def parse_html(html_path):
    """解析 HTML 为模块子元素列表，兼容两代模板。

    新版（v2.16+，含 08-27 单容器过渡版）：body 下唯一容器 div，返回容器内子模块；
    老版（v2.14/2.15，08-28 等）：body 下平级多 div（无总容器），返回 body 全部子元素。
    返回值：(children, legacy) —— legacy=True 表示老版平级结构。
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml')
    body = soup.find('body')
    body_divs = [c for c in body.children if isinstance(c, Tag) and c.name == 'div']
    if len(body_divs) <= 1:
        top = body_divs[0] if body_divs else body
        return [c for c in top.children if isinstance(c, Tag)], False
    return [c for c in body.children if isinstance(c, Tag)], True


def parse_header(children, header_idx=1):
    """从头部卡提取 期号/标题/主题。

    新版头部卡在 children[1]；老版（平级多 div）头部卡在 children[0]。
    依次尝试，命中期号即返回。
    """
    for idx in (header_idx, 0):
        if idx >= len(children):
            continue
        info = children[idx].get_text('\n', strip=True).split('\n')
        issue, title, theme = '', '', ''
        for line in info:
            line = line.strip()
            m = re.search(r'第([\d-]+)期', line)
            if m:
                issue = m.group(0)
            m2 = re.search(r'《(.+?)》', line)
            if m2:
                title = m2.group(1)
            if '核心主题' in line or '适用' in line:
                theme = line
        if issue:
            return issue, title, theme
    return '', '', ''


def render_div(node, lines, brief=False):
    """渲染一个 div（分论点/句式/速记卡/行动清单）到 lines。"""
    ps = node.find_all('p')
    p_lines = [p.get_text('', strip=True).strip() for p in ps]
    p_lines = [l for l in p_lines if l]
    if not p_lines:
        return
    first = p_lines[0]
    if '今日行动清单' in first:
        lines.append('')
        lines.append('【今日行动清单】')
        for r in p_lines[1:]:
            if brief:
                r = re.sub(r'背诵一句金句[“”"].*?[“”"]', '背诵核心金句', r)
                r = r.replace('仿写一个万能句式（政策排比句）', '仿写万能句式')
                r = r.replace('评论区打卡你的仿写', '评论区打卡')
            lines.append(f' {r}')
    elif first.startswith('分论点') or first.startswith('句式'):
        lines.append(f' {first}')
        for r in p_lines[1:]:
            if brief:
                if '仿写' in r:
                    continue
                if '论据' in r:
                    r = re.sub(r'（[^）]*）', '', r)
                    r = r.replace('；济南稻田画→农文旅融合', '等')
            lines.append(f'  {r}')
    else:
        # 速记卡等
        for r in p_lines:
            if brief:
                if '今日仿写' in r:
                    continue
                r = clean_emoji(r)
                if '案例' in r:
                    r = r.replace('桦南紫苏120+产品｜', '')
                    r = r.replace('（利用率96%）', '')
                    r = r.replace('利川"金豆豆"土豆', '利川"金豆豆"')
                    r = r.replace('肥西碎米酿红曲米酒', '肥西红曲米酒')
                    r = r.replace('盱眙小龙虾400亿产业', '盱眙小龙虾400亿')
            lines.append(f' {r}')


def build_text(children, brief=False, legacy=False):
    lines = []

    # ---- 头部 ----
    issue, title, theme = parse_header(children, 0 if legacy else 1)
    lines.append(issue)
    lines.append(f'《{title}》')
    if theme:
        if brief:
            theme = theme.split('｜')[0]
        lines.append(theme)
    lines.append('')

    # ---- 原文摘录（元素2；老版平级结构为元素1，即开篇导语引用）----
    quote = children[1 if legacy else 2].get_text('\n', strip=True).split('\n')
    quote = [q for q in quote if q.strip()]
    lines.append('【原文摘录】')
    if brief and quote:
        body = [q for q in quote if not q.startswith('——') and '人民日报' not in q]
        if body:
            full = body[0]
            first_sent = full.split('。')[0] + '。'
            m = re.search(r'(从[^。]*环环生金[^。]*。[”"]?)', full)
            key_sent = m.group(1) if m else ''
            if key_sent:
                lines.append(f' {first_sent}……{key_sent}')
            else:
                # v2.18：无特征金句时取首句 + 次句首段，控制摘录篇幅
                sents = [s + '。' for s in full.split('。') if s.strip()]
                lines.append(' ' + sents[0] + ('……' if len(sents) > 1 else ''))
    else:
        for q in quote:
            lines.append(f' {q}')
    lines.append('')

    # ---- 遍历后续章节（h2 + 内容；老版平级结构 h2 从元素2 开始）----
    i = 2 if legacy else 3
    while i < len(children):
        c = children[i]
        if c.name != 'h2':
            i += 1
            continue
        section_title = clean_emoji(c.get_text(strip=True))
        omit_tail_v18 = False
        lines.append(f'【{section_title}】')

        j = i + 1
        content = []
        while j < len(children) and children[j].name != 'h2':
            content.append(children[j])
            j += 1

        # v2.18 简化版区块精简（brief 模式）
        if brief:
            if '考题定位' in section_title:
                # 只留主题归类行，标题机关/立意路径省略
                for node in content:
                    if node.name == 'div':
                        ps = node.find_all('p')
                        for extra in ps[1:]:
                            extra.decompose()
            elif '语录' in section_title:
                # 只留语录 1
                divs = [n for n in content if n.name == 'div']
                if divs:
                    content = divs[:1]
                    omit_tail_v18 = True
            elif '迁移指南' in section_title:
                # 只留 适用考题+套用警示 div，仿写示范卡省略
                divs = [n for n in content if n.name == 'div']
                if divs:
                    content = divs[:1]
                    omit_tail_v18 = True

        # brief 模式：论证骨架 / 万能句式 只保留第一个 div
        omit_tail = False
        if brief and ('论证骨架' in section_title or '万能句式' in section_title):
            divs = [n for n in content if n.name == 'div']
            content = divs[:1]
            omit_tail = True

        for node in content:
            if node.name == 'p' and ('上一篇' in node.get_text() or '下一篇' in node.get_text()):
                continue
            if node.name == 'pre':
                pre_lines = [l.strip() for l in node.get_text('\n', strip=True).split('\n')]
                pre_lines = [l for l in pre_lines if l and l != '↓']
                if brief:
                    kept = [l for l in pre_lines if not (l.startswith('分论点2') or l.startswith('分论点3') or l.startswith('总结'))]
                    for l in kept:
                        lines.append(f' {l}')
                        if l.startswith('分论点1'):
                            lines.append(f' ……')
                else:
                    for line in pre_lines:
                        lines.append(f' {line}')
            elif node.name == 'table':
                data_rows = [tr for tr in node.find_all('tr') if tr.find('td')]
                need_ellipsis = brief and len(data_rows) > 2
                if brief:
                    data_rows = data_rows[:2]
                for tr in data_rows:
                    tds = [td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]
                    if tds:
                        lines.append(f' {"｜".join(tds)}')
                if need_ellipsis:
                    lines.append(f' ……')
            elif node.name == 'div':
                if brief and '论证骨架' in section_title:
                    for pp in node.find_all('p'):
                        t = pp.get_text()
                        if '小结' in t or '提出论点' in t:
                            pp.decompose()
                render_div(node, lines, brief)
            else:
                txt = node.get_text('\n', strip=True)
                for line in txt.split('\n'):
                    if line.strip():
                        lines.append(f' {line.strip()}')

        if omit_tail or omit_tail_v18:
            lines.append(f' ……')

        lines.append('')
        i = j

    # v2.18 预览标签过滤（考题定位/语录/套用模板等处的「v2.18 新增」类文字）
    lines = [re.sub(r'v2\.18\s*(新增展示|新增|穷尽开采)', '', l) for l in lines]
    lines = [l.replace('（ 参考', '（参考') for l in lines]  # ⚠️ 被 clean_emoji 清除后的空格修复
    if brief:
        # v2.18 brief 后处理：笔法行省略（卡片/长图有）+ 速记卡金句/案例各取 1 + 行动清单去①
        lines = [l for l in lines
                 if not l.strip().startswith(('开头范式：', '过渡技巧：'))
                 and '① 背诵' not in l]
        lines = [l.split('｜')[0].strip() if l.strip().startswith('——') else l for l in lines]
        lines = [l.replace('（ 参考，以真题原文为准）', '（参考）') for l in lines]
        lines = [l for l in lines if l.strip()]  # 去空行（发布端自动压缩段落间距）
        out = []
        for l in lines:
            m = re.match(r'(\s*)金句：\s*["“]([^"”]+)["”]', l)
            if m:
                out.append(f'{m.group(1)}金句："{m.group(2)}"')
                continue
            if l.strip().startswith('案例：'):
                out.append(l.split('；')[0].rstrip())
                continue
            if l.strip() == '……':
                continue
            out.append(l)
        lines = out
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description='HTML → 纯文本结构文件（完整版/简化版）')
    ap.add_argument('html', help='公众号 HTML 路径')
    ap.add_argument('--out', help='输出 txt 路径（默认同目录自动命名 .txt）')
    ap.add_argument('--brief', action='store_true', help='生成简化版（小红书 1000 字内）')
    args = ap.parse_args()

    if not args.out:
        gzh_dir = os.path.dirname(os.path.abspath(args.html))  # 公众号/ 目录
        article_dir = os.path.dirname(gzh_dir)                  # 文章目录
        fname = os.path.splitext(os.path.basename(args.html))[0]
        title = fname.replace('_公众号', '')
        if args.brief:
            xhs_dir = os.path.join(article_dir, '小红书')
            os.makedirs(xhs_dir, exist_ok=True)
            args.out = os.path.join(xhs_dir, f'{title}_内容结构_简化版.txt')
        else:
            args.out = os.path.join(gzh_dir, f'{title}_内容结构.txt')

    children, legacy = parse_html(args.html)
    text = build_text(children, brief=args.brief, legacy=legacy)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(text)

    char_count = len(text)
    no_ws = len(re.sub(r'\s', '', text))
    print(f'已生成：{args.out}（纯文本）')
    print(f'字数：{char_count} 字（含空白，小红书口径）/ {no_ws} 字（不含空白）')
    if args.brief and char_count > 800:
        print(f'⚠️ 注意：含空白 {char_count} 字偏多，小红书实际显示可能超 1000，建议进一步精简')


if __name__ == '__main__':
    main()
