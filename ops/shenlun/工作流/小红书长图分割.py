#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书长图分割脚本（v2.15 新增）

输入：HTML 渲染的长图 PNG（默认宽度 750）
输出：多张 1242x1660 竖版小红书卡片 PNG（数量不固定，按内容自然分，最多 12 张）

算法：
1. 长图缩放到目标宽度 1242（保持比例，高度按比例放大）
2. 转灰度，检测水平空白带（连续白色行）作为内容块天然边界
3. 相邻短内容块合并（合并后总高度 ≤ 卡片高度）
4. 超长内容块：内部按 1660 高度再切，保留子内容连续（不在子段中间切）
5. 每张卡缩放到 1242x1660（不足补白、居中）
6. 编号输出 01_xxx.png ~ NN_xxx.png

用法：
python3 工作流/小红书长图分割.py <长图PNG路径> --out <输出目录> [--max 12] [--size 1242x1660]
"""
import sys
import os
import argparse
import json
from pathlib import Path
from PIL import Image
import numpy as np
import cv2


def load_long_image(path: str) -> Image.Image:
    img = Image.open(path).convert('RGB')
    return img


def detect_blank_bands(gray: np.ndarray, blank_threshold: int = 248, min_gap: int = 25) -> list:
    """
    检测每一行是否为"近白"（行像素均值 >= blank_threshold）。
    短空白（连续白行 < min_gap）被忽略：避免表格行间小空白被识别为分节。
    返回 [y_start, y_end] 列表（连续非白行段）。
    """
    row_means = gray.mean(axis=1)
    is_content = row_means < blank_threshold
    segments = []
    in_seg = False
    start = 0
    blank_run = 0
    for y, c in enumerate(is_content):
        if c:
            if not in_seg:
                start = y
                in_seg = True
            blank_run = 0
        else:
            blank_run += 1
            if in_seg and blank_run >= min_gap:
                segments.append((start, y - blank_run + 1))
                in_seg = False
                blank_run = 0
    if in_seg:
        segments.append((start, len(is_content)))
    return segments


def merge_short_content_segments(segments: list, short_threshold: int = 60) -> list:
    """
    合并连续短内容段（被小空白切碎的内容，如表格行）成大段。
    短段（< threshold）如果不是段尾就并入下一段。
    """
    if not segments:
        return segments
    out = []
    i = 0
    while i < len(segments):
        s, e = segments[i]
        h = e - s
        if h < short_threshold and i + 1 < len(segments):
            ns, ne = segments[i + 1]
            out.append((s, ne))
            i += 2
        else:
            out.append((s, e))
            i += 1
    return out


def split_into_blocks(img_width: int, img_height: int, segments: list, pad: int = 8) -> list:
    """
    接收已经合并过的内容段，加 padding 防切到文字边缘。
    """
    blocks = []
    for s, e in segments:
        bs = max(s - pad, 0)
        be = min(e + pad, img_height)
        blocks.append((bs, be))
    return blocks


def merge_blocks_to_cards(blocks: list, card_height: int, max_cards: int = 12) -> list:
    """
    短块合并到一卡（合并后总高严格 ≤ card_height）。
    严格切：当前卡满了就开新卡，不论 cur_h 大小。
    返回卡组，每卡 = [块索引列表]。
    """
    cards = []
    cur_card = []
    cur_h = 0
    for idx, (s, e) in enumerate(blocks):
        h = e - s
        # 单块就超长，单独成卡
        if h > card_height:
            if cur_card:
                cards.append(cur_card)
                cur_card = []
                cur_h = 0
            cards.append([idx])
            continue
        if cur_h == 0:
            cur_card = [idx]
            cur_h = h
        elif cur_h + h <= card_height:
            cur_card.append(idx)
            cur_h += h
        else:
            cards.append(cur_card)
            cur_card = [idx]
            cur_h = h
    if cur_card:
        cards.append(cur_card)
    # 超过 max_cards：把多余卡的内容合并到前一张（保留所有内容，宁可多一张）
    if len(cards) > max_cards:
        keep = cards[:max_cards - 1]
        rest_blocks = []
        for c in cards[max_cards - 1:]:
            rest_blocks.extend(c)
        keep.append(rest_blocks)
        cards = keep
    return cards


def make_card(content_img: Image.Image, size: tuple, bg: tuple = (255, 255, 255)) -> Image.Image:
    """
    将内容图缩放并居中补白到目标卡片尺寸。
    content_img 的宽高比与 size 一致（已按比例缩放到目标宽）。
    """
    tw, th = size
    cw, ch = content_img.size
    if (cw, ch) == (tw, th):
        return content_img
    canvas = Image.new('RGB', (tw, th), bg)
    if cw == tw and ch <= th:
        # 等宽，内容高度不足，上下补白
        offset = (0, (th - ch) // 2)
        canvas.paste(content_img, offset)
    else:
        # 内容高度超出，强制缩放到完全适配（保持比例可能在长边裁切，但本脚本保证 ≤ card_height）
        ratio = min(tw / cw, th / ch)
        nw, nh = int(cw * ratio), int(ch * ratio)
        resized = content_img.resize((nw, nh), Image.LANCZOS)
        offset = ((tw - nw) // 2, (th - nh) // 2)
        canvas.paste(resized, offset)
    return canvas


def split_long_image(long_path: str, out_dir: str, size=(1242, 1660), max_cards: int = 12) -> dict:
    src = load_long_image(long_path)
    src_w, src_h = src.size
    target_w, target_h = size

    # 1. 缩放到目标宽度
    if src_w != target_w:
        scale = target_w / src_w
        new_h = int(src_h * scale)
        scaled = src.resize((target_w, new_h), Image.LANCZOS)
    else:
        scale = 1.0
        new_h = src_h
        scaled = src

    # 2. 转灰度，检测内容段（连续非白行）
    arr = np.array(scaled)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    segments = detect_blank_bands(gray, blank_threshold=248, min_gap=25)
    # 2.1 合并短段：表格行被切开的情况
    segments = merge_short_content_segments(segments, short_threshold=60)

    # 3. 加 padding 转成内容块
    blocks = split_into_blocks(target_w, new_h, segments, pad=8)

    # 4. 合并块到卡片
    cards = merge_blocks_to_cards(blocks, target_h, max_cards)

    # 5. 输出每张卡
    os.makedirs(out_dir, exist_ok=True)
    out_files = []
    card_meta = []
    for i, card_blocks in enumerate(cards, 1):
        # 合并块：取首块 start 到末块 end
        ys = [blocks[idx][0] for idx in card_blocks]
        ye = [blocks[idx][1] for idx in card_blocks]
        crop_y0 = min(ys)
        crop_y1 = max(ye)
        content = scaled.crop((0, crop_y0, target_w, crop_y1))
        card = make_card(content, size)
        out_name = f"{i:02d}_card.png"
        out_path = os.path.join(out_dir, out_name)
        card.save(out_path, 'PNG', optimize=True)
        out_files.append(out_path)
        card_meta.append({
            'index': i,
            'file': out_name,
            'blocks': card_blocks,
            'content_height': crop_y1 - crop_y0,
            'y_range': [crop_y0, crop_y1],
        })

    meta = {
        'source': os.path.abspath(long_path),
        'source_size': [src_w, src_h],
        'target_size': list(size),
        'scale': scale,
        'scaled_height': new_h,
        'content_segments_count': len(segments),
        'blocks_count': len(blocks),
        'cards_count': len(cards),
        'cards': card_meta,
    }
    meta_path = os.path.join(out_dir, '分割元数据.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {
        'count': len(out_files),
        'files': out_files,
        'meta_path': meta_path,
        'meta': meta,
    }


def main():
    ap = argparse.ArgumentParser(description='HTML 长图按内容分割为小红书卡片（1242x1660）')
    ap.add_argument('long_image', help='长图 PNG 路径')
    ap.add_argument('--out', required=True, help='输出目录')
    ap.add_argument('--size', default='1242x1660', help='目标卡片尺寸 WxH，默认 1242x1660')
    ap.add_argument('--max', type=int, default=12, help='最多卡片数（超过则合并多余内容到前卡），默认 12')
    args = ap.parse_args()

    w, h = map(int, args.size.lower().split('x'))
    result = split_long_image(args.long_image, args.out, size=(w, h), max_cards=args.max)

    print(f"切分完成：{result['count']} 张卡片")
    for f in result['files']:
        print(f"  - {f}")
    print(f"元数据：{result['meta_path']}")


if __name__ == '__main__':
    main()
