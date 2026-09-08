#!/usr/bin/env python3
"""生成更精致的 tabBar 图标与品牌 Logo（纯 Python，无第三方依赖）

- tab 图标：162×162（@2x），再缩到 81×81，带抗锯齿
- logo：200×200 红色圆角标，白底书本+对勾图形
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON_OUT = ROOT / "src" / "assets" / "icons"
LOGO_OUT = ROOT / "src" / "assets" / "logo"
ICON_OUT.mkdir(parents=True, exist_ok=True)
LOGO_OUT.mkdir(parents=True, exist_ok=True)

TAB_SIZE = 81
SS = 4  # supersample factor
LOGO_SIZE = 200


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path: Path, size: int, pixels: list[tuple[int, int, int, int]]):
    raw = b""
    for y in range(size):
        raw += b"\x00"
        for x in range(size):
            raw += bytes(pixels[y * size + x])
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    data = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(data)


def blank(size: int) -> list[tuple[int, int, int, int]]:
    return [(0, 0, 0, 0)] * (size * size)


def set_px(px: list, size: int, x: int, y: int, color: tuple[int, int, int, int]):
    if 0 <= x < size and 0 <= y < size:
        px[y * size + x] = color


def blend(dst: tuple[int, int, int, int], src: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    sr, sg, sb, sa = src
    dr, dg, db, da = dst
    if sa == 255:
        return src
    if sa == 0:
        return dst
    out_a = sa + da * (255 - sa) // 255
    if out_a == 0:
        return (0, 0, 0, 0)
    r = (sr * sa + dr * da * (255 - sa) // 255) // out_a
    g = (sg * sa + dg * da * (255 - sa) // 255) // out_a
    b = (sb * sa + db * da * (255 - sa) // 255) // out_a
    return (r, g, b, out_a)


def put(px: list, size: int, x: int, y: int, color: tuple[int, int, int, int]):
    if 0 <= x < size and 0 <= y < size:
        px[y * size + x] = blend(px[y * size + x], color)


def fill_circle(px, size, cx, cy, r, color):
    r2 = r * r
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                put(px, size, x, y, color)


def stroke_circle(px, size, cx, cy, r, color, w):
    outer = (r + w / 2) ** 2
    inner = max(0, r - w / 2) ** 2
    for y in range(int(cy - r - w) - 1, int(cy + r + w) + 2):
        for x in range(int(cx - r - w) - 1, int(cx + r + w) + 2):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if inner <= d2 <= outer:
                put(px, size, x, y, color)


def fill_rect(px, size, x0, y0, x1, y1, color):
    for y in range(int(y0), int(y1) + 1):
        for x in range(int(x0), int(x1) + 1):
            put(px, size, x, y, color)


def fill_round_rect(px, size, x0, y0, x1, y1, radius, color):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    radius = max(0, int(radius))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dx = 0.0
            dy = 0.0
            if x < x0 + radius:
                dx = (x0 + radius) - x
            elif x > x1 - radius:
                dx = x - (x1 - radius)
            if y < y0 + radius:
                dy = (y0 + radius) - y
            elif y > y1 - radius:
                dy = y - (y1 - radius)
            if dx * dx + dy * dy <= radius * radius:
                put(px, size, x, y, color)


def stroke_line(px, size, x0, y0, x1, y1, color, w):
    steps = max(abs(int(x1 - x0)), abs(int(y1 - y0)), 1) * 2
    half = w / 2
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        fill_circle(px, size, x, y, half, color)


def downsample(src: list, src_size: int, dst_size: int) -> list[tuple[int, int, int, int]]:
    factor = src_size // dst_size
    out = blank(dst_size)
    for y in range(dst_size):
        for x in range(dst_size):
            r = g = b = a = 0
            for dy in range(factor):
                for dx in range(factor):
                    pr, pg, pb, pa = src[(y * factor + dy) * src_size + (x * factor + dx)]
                    r += pr * pa
                    g += pg * pa
                    b += pb * pa
                    a += pa
            n = factor * factor
            if a == 0:
                out[y * dst_size + x] = (0, 0, 0, 0)
            else:
                out[y * dst_size + x] = (r // a, g // a, b // a, a // n)
    return out


def draw_home(color, size):
    """学习：打开的书本"""
    px = blank(size)
    w = size * 0.055
    # left page
    stroke_line(px, size, size * 0.50, size * 0.28, size * 0.22, size * 0.36, color, w)
    stroke_line(px, size, size * 0.22, size * 0.36, size * 0.22, size * 0.72, color, w)
    stroke_line(px, size, size * 0.22, size * 0.72, size * 0.50, size * 0.64, color, w)
    # right page
    stroke_line(px, size, size * 0.50, size * 0.28, size * 0.78, size * 0.36, color, w)
    stroke_line(px, size, size * 0.78, size * 0.36, size * 0.78, size * 0.72, color, w)
    stroke_line(px, size, size * 0.78, size * 0.72, size * 0.50, size * 0.64, color, w)
    # spine
    stroke_line(px, size, size * 0.50, size * 0.28, size * 0.50, size * 0.64, color, w * 0.9)
    # page lines
    lw = size * 0.032
    stroke_line(px, size, size * 0.30, size * 0.46, size * 0.44, size * 0.42, color, lw)
    stroke_line(px, size, size * 0.30, size * 0.54, size * 0.44, size * 0.50, color, lw)
    stroke_line(px, size, size * 0.56, size * 0.42, size * 0.70, size * 0.46, color, lw)
    stroke_line(px, size, size * 0.56, size * 0.50, size * 0.70, size * 0.54, color, lw)
    return px


def draw_quiz(color, size):
    """答题：试卷折角 + 对勾"""
    px = blank(size)
    w = size * 0.055
    # paper
    stroke_line(px, size, size * 0.30, size * 0.22, size * 0.56, size * 0.22, color, w)
    stroke_line(px, size, size * 0.30, size * 0.22, size * 0.30, size * 0.80, color, w)
    stroke_line(px, size, size * 0.30, size * 0.80, size * 0.70, size * 0.80, color, w)
    stroke_line(px, size, size * 0.70, size * 0.80, size * 0.70, size * 0.38, color, w)
    # folded corner
    stroke_line(px, size, size * 0.56, size * 0.22, size * 0.70, size * 0.38, color, w)
    stroke_line(px, size, size * 0.56, size * 0.22, size * 0.56, size * 0.38, color, w)
    stroke_line(px, size, size * 0.56, size * 0.38, size * 0.70, size * 0.38, color, w)
    # checkmark
    cw = size * 0.06
    stroke_line(px, size, size * 0.40, size * 0.56, size * 0.48, size * 0.65, color, cw)
    stroke_line(px, size, size * 0.48, size * 0.65, size * 0.62, size * 0.46, color, cw)
    return px


def draw_user(color, size):
    """我的：简洁人物轮廓"""
    px = blank(size)
    w = size * 0.055
    # head
    stroke_circle(px, size, size * 0.50, size * 0.32, size * 0.13, color, w)
    # body — smooth shoulder arc
    cx, cy = size * 0.50, size * 0.82
    rx, ry = size * 0.24, size * 0.20
    prev = None
    for step in range(0, 181):
        a = math.radians(step)
        x = cx + rx * math.cos(math.pi - a)
        y = cy - ry * math.sin(a)
        if y < size * 0.55:
            prev = None
            continue
        if prev is not None:
            stroke_line(px, size, prev[0], prev[1], x, y, color, w)
        prev = (x, y)
    return px


def draw_today(color, size):
    """今日：日历 + 对勾（当天待办）"""
    px = blank(size)
    w = size * 0.055
    # calendar body
    stroke_line(px, size, size * 0.28, size * 0.34, size * 0.72, size * 0.34, color, w)
    stroke_line(px, size, size * 0.28, size * 0.34, size * 0.28, size * 0.78, color, w)
    stroke_line(px, size, size * 0.28, size * 0.78, size * 0.72, size * 0.78, color, w)
    stroke_line(px, size, size * 0.72, size * 0.78, size * 0.72, size * 0.34, color, w)
    # binder rings
    stroke_line(px, size, size * 0.36, size * 0.26, size * 0.40, size * 0.34, color, w)
    stroke_line(px, size, size * 0.60, size * 0.26, size * 0.64, size * 0.34, color, w)
    # header divider
    stroke_line(px, size, size * 0.28, size * 0.46, size * 0.72, size * 0.46, color, w)
    # checkmark
    cw = size * 0.06
    stroke_line(px, size, size * 0.42, size * 0.58, size * 0.48, size * 0.66, color, cw)
    stroke_line(px, size, size * 0.48, size * 0.66, size * 0.60, size * 0.52, color, cw)
    return px


def render_tab(draw_fn, color) -> list[tuple[int, int, int, int]]:
    big = TAB_SIZE * SS
    px = draw_fn(color, big)
    return downsample(px, big, TAB_SIZE)


def draw_logo() -> list[tuple[int, int, int, int]]:
    size = LOGO_SIZE
    px = blank(size)
    red = (30, 58, 95, 255)
    white = (255, 255, 255, 255)
    # rounded blue badge
    fill_round_rect(px, size, 8, 8, size - 9, size - 9, 44, red)
    # open book shape
    # left page
    stroke_line(px, size, size * 0.50, size * 0.30, size * 0.28, size * 0.38, white, 7)
    stroke_line(px, size, size * 0.28, size * 0.38, size * 0.28, size * 0.68, white, 7)
    stroke_line(px, size, size * 0.28, size * 0.68, size * 0.50, size * 0.60, white, 7)
    # right page
    stroke_line(px, size, size * 0.50, size * 0.30, size * 0.72, size * 0.38, white, 7)
    stroke_line(px, size, size * 0.72, size * 0.38, size * 0.72, size * 0.68, white, 7)
    stroke_line(px, size, size * 0.72, size * 0.68, size * 0.50, size * 0.60, white, 7)
    # spine
    stroke_line(px, size, size * 0.50, size * 0.30, size * 0.50, size * 0.60, white, 6)
    # page lines
    stroke_line(px, size, size * 0.34, size * 0.46, size * 0.46, size * 0.42, white, 3)
    stroke_line(px, size, size * 0.34, size * 0.54, size * 0.46, size * 0.50, white, 3)
    stroke_line(px, size, size * 0.54, size * 0.42, size * 0.66, size * 0.46, white, 3)
    stroke_line(px, size, size * 0.54, size * 0.50, size * 0.66, size * 0.54, white, 3)
    # check accent
    stroke_line(px, size, size * 0.40, size * 0.74, size * 0.48, size * 0.80, white, 6)
    stroke_line(px, size, size * 0.48, size * 0.80, size * 0.64, size * 0.66, white, 6)
    return px


GRAY = (153, 153, 153, 255)
RED = (30, 58, 95, 255)

for name, fn in [
    ("today", draw_today),
    ("home", draw_home),
    ("quiz", draw_quiz),
    ("user", draw_user),
]:
    write_png(ICON_OUT / f"{name}.png", TAB_SIZE, render_tab(fn, GRAY))
    write_png(ICON_OUT / f"{name}-active.png", TAB_SIZE, render_tab(fn, RED))

write_png(LOGO_OUT / "logo.png", LOGO_SIZE, draw_logo())
# smaller for inline use
small = downsample(draw_logo(), LOGO_SIZE, 96)
write_png(LOGO_OUT / "logo-96.png", 96, small)

print(f"已生成 tab 图标 -> {ICON_OUT}")
print(f"已生成 logo -> {LOGO_OUT}")
