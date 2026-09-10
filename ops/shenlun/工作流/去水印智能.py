#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
去水印智能版 v1.0 —— OpenCV inpainting 内容感知填充（右下角「包含AI生成」水印）

原理：定位右下角水印区域 → 检测水印文字像素生成 mask → cv2.inpaint 用周围背景
      智能填充 → 边缘羽化 → 输出。无成本、不裁剪、不降质、全自动。

用法：
    python3 工作流/去水印智能.py <图片或目录> [--x0 0.72 --y0 0.955 --x1 0.995 --y1 0.995]
    # 区域参数为归一化坐标（0~1），默认右下角区域，可按实际水印位置调整

依赖：opencv-python-headless（已装于 venv envs/default）
"""
import os, sys, argparse
import numpy as np
import cv2

def remove_watermark(path, x0, y0, x1, y1, out_path=None):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"无法读取图片: {path}")
    if img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    h, w = img.shape[:2]
    x0i, y0i = int(w * x0), int(h * y0)
    x1i, y1i = int(w * x1), int(h * y1)
    x0i, y0i = max(0, x0i), max(0, y0i)
    x1i, y1i = min(w, x1i), min(h, y1i)
    if x1i - x0i < 10 or y1i - y0i < 10:
        raise ValueError("水印区域过小")
    region = img[y0i:y1i, x0i:x1i]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    # 自适应检测水印文字像素：取区域中位亮度，向两端（暗/亮）找显著差异像素
    med = int(np.median(gray))
    # 背景若是浅色（纸张），水印文字通常较深；反之较浅——取差异更大的一侧
    dark_mask = cv2.threshold(gray, max(0, med - 45), 255, cv2.THRESH_BINARY)[1]
    light_mask = cv2.threshold(gray, min(255, med + 45), 255, cv2.THRESH_BINARY_INV)[1]
    mask = dark_mask if (dark_mask > 0).sum() > (light_mask > 0).sum() else light_mask
    # 膨胀+羽化，避免填充边缘生硬
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    # inpaint（Telea 算法，内容感知填充）
    filled = cv2.inpaint(region, mask.astype(np.uint8), 3, cv2.INPAINT_TELEA)
    img[y0i:y1i, x0i:x1i] = filled
    if out_path is None:
        out_path = path
    cv2.imwrite(out_path, img)
    return dict(w=w, h=h, box=(x0i, y0i, x1i, y1i), mask_px=int((mask > 0).sum()))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="图片或目录")
    ap.add_argument("--x0", type=float, default=0.72)
    ap.add_argument("--y0", type=float, default=0.955)
    ap.add_argument("--x1", type=float, default=0.995)
    ap.add_argument("--y1", type=float, default=0.995)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if os.path.isdir(a.target):
        files = []
        for root, _, fs in os.walk(a.target):
            for f in sorted(fs):
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    files.append(os.path.join(root, f))
    else:
        files = [a.target]
    if not files:
        print("未找到图片"); return 1
    for f in files:
        out = None
        if a.out:
            os.makedirs(a.out, exist_ok=True)
            out = os.path.join(a.out, os.path.basename(f))
        try:
            r = remove_watermark(f, a.x0, a.y0, a.x1, a.y1, out)
            print(f"✅ {os.path.basename(f)}  区域{r['box']} 填充水印像素{r['mask_px']}")
        except Exception as e:
            print(f"❌ {os.path.basename(f)}: {e}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
