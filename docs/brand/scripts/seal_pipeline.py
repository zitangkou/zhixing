#!/usr/bin/env python3
"""印章头像成品流水线（合并居中 + 转品牌红 + 多尺寸导出）。

用法：
    python3 seal_pipeline.py <导出png> <输出前缀> [--out DIR] [--no-recolor]

步骤：
1. 检测背景色 → 按内容包围盒裁切 → 重新居中
2. 按内切圆安全边距补底（圆形头像裁切不切角）
3. 把模板珊瑚红按通道比例映射为品牌红 #D0021B（保留纹理与抗锯齿）
4. 导出 1024 / 512 / 144 PNG + 圆形裁切预览
"""
import argparse
import collections
import os
import sys

from PIL import Image, ImageChops, ImageDraw

BRAND = (208, 2, 27)          # #D0021B
BG_TOL = 26
CIRCLE_SAFE = 0.90


def bg_color(img):
    px = img.convert("RGB").load()
    w, h = img.size
    corners = [px[2, 2], px[w - 3, 2], px[2, h - 3], px[w - 3, h - 3]]
    return tuple(int(sorted(c[i] for c in corners)[1]) for i in range(3))


def dominant_red(img):
    px = img.convert("RGB").load()
    w, h = img.size
    hist = collections.Counter()
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            r, g, b = px[x, y]
            if r > 150 and r - g > 40 and r - b > 40:
                hist[(r // 8 * 8, g // 8 * 8, b // 8 * 8)] += 1
    if not hist:
        return None
    return hist.most_common(1)[0][0]


def recolor(img, src_red):
    scale = tuple(BRAND[i] / max(src_red[i], 1) for i in range(3))
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r - g > 18 or r - b > 18:
                px[x, y] = (min(255, int(r * scale[0])),
                            min(255, int(g * scale[1])),
                            min(255, int(b * scale[2])))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("prefix")
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)) + "/canva")
    ap.add_argument("--no-recolor", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    img = Image.open(args.src).convert("RGB")
    bg = bg_color(img)

    diff = ImageChops.difference(img, Image.new("RGB", img.size, bg))
    mask = diff.convert("L").point(lambda v: 255 if v > BG_TOL else 0)
    box = mask.getbbox()
    if not box:
        sys.exit("未检测到内容，请检查导出图")

    content = img.crop(box)
    w, h = content.size
    half_diag = (w * w + h * h) ** 0.5 / 2
    C = int(2 * half_diag / CIRCLE_SAFE)
    C += C % 2
    canvas = Image.new("RGB", (C, C), bg)
    canvas.paste(content, ((C - w) // 2, (C - h) // 2))
    print(f"内容 {w}x{h} → 居中画布 {C}x{C}")

    variants = {"": canvas}
    if not args.no_recolor:
        src_red = dominant_red(canvas)
        if src_red:
            variants["-brand"] = recolor(canvas.copy(), src_red)
            print(f"印章换色 {src_red} → {BRAND}")
        else:
            print("未检出红色，跳过换色")

    for suf, im in variants.items():
        name = f"{args.prefix}{suf}"
        for size in (1024, 512, 144):
            out = im.resize((size, size), Image.LANCZOS) if size != C else im
            p = f"{args.out}/{name}-{size}.png"
            out.save(p, "PNG", optimize=True)
        prev = im.resize((512, 512), Image.LANCZOS).convert("RGBA")
        m = Image.new("L", (512, 512), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 511, 511], fill=255)
        prev.putalpha(m)
        prev.save(f"{args.out}/{name}-circle.png", "PNG")
        print(f"导出 {name}-1024/512/144 + circle")


if __name__ == "__main__":
    main()
