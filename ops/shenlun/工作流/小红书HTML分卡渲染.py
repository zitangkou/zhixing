#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书 HTML 内容块分卡渲染（v2.15 替代方案）

基于原公众号 HTML 的顶层结构切分章节，每个章节组单独渲染为 PNG 卡片。
比"长图视觉分割"更可靠：内容 100% 完整、章节标题永远在卡顶、不依赖 OpenCV。

输入：公众号 HTML 文件
输出：6-12 张 1242x1660 PNG 卡片

算法：
1. BeautifulSoup 解析 HTML，提取顶层 div 下的 19 个子元素
2. 按 h2 标题分组：每个 h2 + 其后续内容（直到下一个 h2）= 一个"章节组"
   - 开头的非 h2 元素（头部/信息卡/原文摘录）归为第 0 组（封面组）
3. 每组生成独立 HTML 片段（含容器 div 样式 + 该组元素）
4. Playwright 渲染每个片段为 1242×N PNG（N=内容自然高度）
5. 短片段合并：相邻片段累计高度 ≤ 1660 时合并到一卡
6. 缩放/补白到 1242×1660 统一卡片尺寸

用法：
python3 工作流/小红书HTML分卡渲染.py <公众号HTML路径> --out <输出目录> [--max 12] [--size 1242x1660]
"""
import sys
import os
import argparse
import json
import asyncio
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image
from playwright.async_api import async_playwright


def parse_html_blocks(html_path: str) -> tuple:
    """
    解析 HTML，返回 (容器 div 样式, 顶层子元素列表)。
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml')
    body = soup.find('body')
    top_div = body.find('div')
    container_style = top_div.get('style', '')
    children = [c for c in top_div.children if isinstance(c, Tag)]
    return container_style, children


def group_by_h2(children: list) -> list:
    """
    按 h2 标题分组。
    - 遇到 h2 就开新组（h2 作为组首元素）
    - h2 之前的元素（头部/信息卡/原文摘录）归为第 0 组
    - 末尾的 <p>上一篇/下一篇</p> 不入组（过滤）
    返回 [[元素, 元素, ...], ...]
    """
    groups = []
    current = []
    for child in children:
        # 过滤"上一篇/下一篇"导航
        if child.name == 'p' and ('上一篇' in child.get_text() or '下一篇' in child.get_text()):
            continue
        if child.name == 'h2':
            if current:
                groups.append(current)
            current = [child]
        else:
            current.append(child)
    if current:
        groups.append(current)
    return groups


def build_fragment_html(container_style: str, elements: list) -> str:
    """
    构造独立 HTML 片段：含容器 div 样式 + 该组元素。
    """
    inner_html = '\n'.join(str(e) for e in elements)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=1242, initial-scale=1.0">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ margin: 0; padding: 0; background: #FFFFFF; }}
</style>
</head>
<body>
<div style="{container_style} width:1202px; max-width:1202px; margin:0 auto; padding:20px;">
{inner_html}
</div>
</body>
</html>"""


async def render_fragment(html_content: str, out_png: str, width: int = 1242) -> tuple:
    """
    用 Playwright 渲染 HTML 片段为 PNG，返回 (宽, 高)。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(viewport={'width': width, 'height': 800})
        page = await context.new_page()
        await page.set_content(html_content, wait_until='networkidle')
        # 等待字体加载
        await page.evaluate("document.fonts.ready")
        # 取内容实际高度
        height = await page.evaluate("""() => {
            const div = document.querySelector('body > div');
            return div ? div.scrollHeight : document.body.scrollHeight;
        }""")
        # 设置 viewport 为内容高度
        await page.set_viewport_size({'width': width, 'height': int(height) + 40})
        await page.screenshot(path=out_png, full_page=True)
        await browser.close()
        return (width, int(height) + 40)


def merge_fragments_to_cards(fragments: list, card_height: int = 1660, max_cards: int = 12, min_card_height: int = 1000) -> list:
    """
    fragments: [(html, png_path, height), ...]
    合并策略：
    - 单片段 > card_height：单独成卡（不切子内容）
    - 当前卡累计高度 < min_card_height：继续合并下一段
    - 当前卡累计高度 ≥ min_card_height 且加上下段会超 card_height：开新卡
    - 否则继续合并
    返回 [[片段索引, ...], ...]
    """
    cards = []
    cur_card = []
    cur_h = 0
    for idx, (_, _, h) in enumerate(fragments):
        if h > card_height:
            # 单片段就超长，单独成卡
            if cur_card:
                cards.append(cur_card)
                cur_card = []
                cur_h = 0
            cards.append([idx])
            continue
        if cur_h == 0:
            cur_card = [idx]
            cur_h = h
        elif cur_h >= min_card_height:
            # 当前卡已满，开新卡
            cards.append(cur_card)
            cur_card = [idx]
            cur_h = h
        elif cur_h + h <= card_height:
            cur_card.append(idx)
            cur_h += h
        else:
            # 加上下段会超，但当前卡还没满（< min），开新卡让下段单独
            cards.append(cur_card)
            cur_card = [idx]
            cur_h = h
    if cur_card:
        cards.append(cur_card)
    # 末尾短卡合并：最后一张 < min_card_height * 0.7 时合到前一张
    if len(cards) >= 2:
        last_frag_idxs = cards[-1]
        last_h = sum(fragments[i][2] for i in last_frag_idxs)
        if last_h < min_card_height * 0.7:
            cards[-2].extend(cards[-1])
            cards.pop()
    # 超过 max_cards：合并多余卡
    if len(cards) > max_cards:
        keep = cards[:max_cards - 1]
        rest = []
        for c in cards[max_cards - 1:]:
            rest.extend(c)
        keep.append(rest)
        cards = keep
    return cards


def make_card_image(png_paths: list, size: tuple, bg=(255, 255, 255)) -> Image.Image:
    """
    把多个片段 PNG 垂直拼接后，缩放/补白到目标卡片尺寸。
    """
    target_w, target_h = size
    # 拼接
    images = [Image.open(p).convert('RGB') for p in png_paths]
    total_h = sum(im.size[1] for im in images)
    max_w = max(im.size[0] for im in images)
    canvas = Image.new('RGB', (max_w, total_h), bg)
    y = 0
    for im in images:
        canvas.paste(im, ((max_w - im.size[0]) // 2, y))
        y += im.size[1]
    # 缩放到目标宽度
    if canvas.size[0] != target_w:
        scale = target_w / canvas.size[0]
        new_h = int(canvas.size[1] * scale)
        canvas = canvas.resize((target_w, new_h), Image.LANCZOS)
    # 补白到目标高度
    if canvas.size[1] < target_h:
        final = Image.new('RGB', (target_w, target_h), bg)
        final.paste(canvas, (0, (target_h - canvas.size[1]) // 2))
        return final
    elif canvas.size[1] > target_h:
        # 超高：等比缩放到完全适配
        scale = target_h / canvas.size[1]
        new_w = int(target_w * scale)
        new_h = target_h
        canvas = canvas.resize((new_w, new_h), Image.LANCZOS)
        final = Image.new('RGB', (target_w, target_h), bg)
        final.paste(canvas, ((target_w - new_w) // 2, 0))
        return final
    return canvas


async def split_html_to_cards(html_path: str, out_dir: str, size=(1242, 1660), max_cards: int = 12, min_card_height: int = 1000) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    container_style, children = parse_html_blocks(html_path)
    groups = group_by_h2(children)

    # 渲染每个章节组
    fragments = []
    tmp_dir = os.path.join(out_dir, '_fragments')
    os.makedirs(tmp_dir, exist_ok=True)
    for i, group in enumerate(groups):
        html_content = build_fragment_html(container_style, group)
        tmp_html = os.path.join(tmp_dir, f'frag_{i:02d}.html')
        tmp_png = os.path.join(tmp_dir, f'frag_{i:02d}.png')
        with open(tmp_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        w, h = await render_fragment(html_content, tmp_png, width=1242)
        fragments.append((html_content, tmp_png, h))
        # 章节组描述
        first = group[0]
        title = first.get_text(strip=True)[:40] if first else f'组{i}'
        print(f'  片段{i}: {len(group)}元素 高度={h}px 标题={title!r}')

    # 合并片段到卡片
    cards = merge_fragments_to_cards(fragments, card_height=size[1], max_cards=max_cards, min_card_height=min_card_height)

    # 生成最终卡片
    out_files = []
    card_meta = []
    for i, frag_indices in enumerate(cards, 1):
        png_paths = [fragments[idx][1] for idx in frag_indices]
        card = make_card_image(png_paths, size)
        out_name = f'{i:02d}_card.png'
        out_path = os.path.join(out_dir, out_name)
        card.save(out_path, 'PNG', optimize=True)
        out_files.append(out_path)
        card_meta.append({
            'index': i,
            'file': out_name,
            'fragments': frag_indices,
            'fragments_count': len(frag_indices),
            'fragment_heights': [fragments[idx][2] for idx in frag_indices],
            'total_height': sum(fragments[idx][2] for idx in frag_indices),
        })

    # 清理临时片段（保留以备调试，可选）
    # shutil.rmtree(tmp_dir)

    meta = {
        'source': os.path.abspath(html_path),
        'target_size': list(size),
        'groups_count': len(groups),
        'cards_count': len(cards),
        'cards': card_meta,
    }
    meta_path = os.path.join(out_dir, '分割元数据.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {'count': len(out_files), 'files': out_files, 'meta_path': meta_path, 'meta': meta}


def main():
    ap = argparse.ArgumentParser(description='HTML 内容块分卡渲染（小红书 1242x1660）')
    ap.add_argument('html', help='公众号 HTML 文件路径')
    ap.add_argument('--out', required=True, help='输出目录')
    ap.add_argument('--size', default='1242x1660', help='目标卡片尺寸 WxH，默认 1242x1660')
    ap.add_argument('--max', type=int, default=12, help='最多卡片数，默认 12')
    ap.add_argument('--min-card-height', type=int, default=1000, help='单卡最小高度（低于则继续合并），默认 1000')
    args = ap.parse_args()

    w, h = map(int, args.size.lower().split('x'))
    result = asyncio.run(split_html_to_cards(args.html, args.out, size=(w, h), max_cards=args.max, min_card_height=args.min_card_height))

    print(f'\n切分完成：{result["count"]} 张卡片')
    for f in result['files']:
        print(f'  - {f}')
    print(f'元数据：{result["meta_path"]}')


if __name__ == '__main__':
    main()
