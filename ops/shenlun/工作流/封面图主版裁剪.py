#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号封面图 → 主版裁剪（v2.15 补充）

把双封面套图（1283×383）右侧的正方形小封面（杜衡阁 logo）截掉，
只保留左侧主封面部分（2.48:1 约 951×383），用于知乎等不支持自动选择裁剪范围的平台。

裁剪边界自动从 `物料模板/封面模板库.json` 的 `avatar.left` 字段读取，
不同模板自动适配。

用法：
python3 工作流/封面图主版裁剪.py <封面图PNG路径> [--out <输出主版路径>] [--template <模板库JSON路径>]
"""
import os
import sys
import json
import argparse
from PIL import Image


def crop_main(cover_path: str, template_path: str = None, out_path: str = None) -> dict:
    if template_path is None:
        # 默认从项目根的物料模板/找
        workspace = '/Users/dnn/Library/Mobile Documents/com~apple~CloudDocs/申论学习'
        template_path = os.path.join(workspace, '物料模板', '封面模板库.json')
    with open(template_path, encoding='utf-8') as f:
        cfg = json.load(f)

    tpl_id = cfg.get('default_template', '')
    tpl = next((t for t in cfg['templates'] if t['id'] == tpl_id), None)
    if tpl is None:
        raise ValueError(f'模板库中未找到 default_template: {tpl_id}')

    cut_x = tpl['avatar']['left']  # 正方形小封面左边界
    cut_w = tpl['avatar'].get('size', 0)  # 正方形小封面边长
    canvas_w = tpl.get('canvas', {}).get('width', 0)
    canvas_h = tpl.get('canvas', {}).get('height', 0)

    im = Image.open(cover_path).convert('RGB')
    w, h = im.size

    # 校验画布尺寸（如果封面图实际尺寸与模板不符，给提示）
    note = ''
    if canvas_w and w != canvas_w:
        note = f'（注：实际图宽 {w} 与模板声明的 {canvas_w} 不符）'

    # 裁剪：保留 0 ~ cut_x
    main = im.crop((0, 0, cut_x, h))
    ratio = main.size[0] / main.size[1]

    if not out_path:
        base, ext = os.path.splitext(cover_path)
        out_path = f'{base}_主版{ext or ".png"}'
    main.save(out_path, 'PNG', optimize=True)

    return {
        'cover': cover_path,
        'source_size': [w, h],
        'template': tpl_id,
        'cut_x': cut_x,
        'square_side': cut_w,
        'main_size': list(main.size),
        'main_ratio': f'{ratio:.2f}:1',
        'out': out_path,
        'note': note,
    }


def main():
    ap = argparse.ArgumentParser(description='公众号封面图主版裁剪（去右侧正方形小封面）')
    ap.add_argument('cover', help='封面图 PNG 路径（双封面套图）')
    ap.add_argument('--out', help='输出主版路径（默认 <原图>_主版.png）')
    ap.add_argument('--template', help='封面模板库 JSON 路径（默认 物料模板/封面模板库.json）')
    args = ap.parse_args()

    result = crop_main(args.cover, args.template, args.out)
    for k, v in result.items():
        print(f'  {k}: {v}')


if __name__ == '__main__':
    main()
