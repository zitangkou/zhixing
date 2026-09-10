#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
去水印 LaMa v2 —— 优化版（文字级精准 mask + 软边融合 + hd 策略可选 + 残留检测）

针对 v1 的"覆盖框痕迹"问题优化：
  A. 文字级精准 mask：自适应检测水印文字像素 → 紧贴文字的 mask（不整块矩形）
  B. 软边融合：修复后按高斯权重与边缘融合，消除接缝
  C. hd_strategy 可调（resize/crop/original）
  D. 残留检测：修复后复查文字特征，疑似残留则提示

用法：
    python3 工作流/去水印lama_v2.py <图片或目录> [--out 输出目录] [--hd resize] [--debug 输出mask预览]

依赖：iopaint + torch + opencv（venv envs/default）；模型 big-lama.pt 本地缓存
"""
import os, sys, argparse
import numpy as np
import cv2

LOCAL_LAMA = os.path.expanduser("~/.cache/torch/hub/checkpoints/big-lama.pt")
os.environ.setdefault("LAMA_MODEL_URL", LOCAL_LAMA)

# 右下角水印搜索区（归一化，可调）
SEARCH_X0, SEARCH_Y0 = 0.55, 0.90
SEARCH_X1, SEARCH_Y1 = 1.0, 1.0

def detect_watermark_bbox(img, x0, y0, x1, y1):
    """在搜索区内检测水印文字像素，返回文字连通域 bbox（含膨胀）"""
    h, w = img.shape[:2]
    x0i, y0i = int(w * x0), int(h * y0)
    x1i, y1i = int(w * x1), int(h * y1)
    region = img[y0i:y1i, x0i:x1i]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    med = int(np.median(gray))
    # 双向检测：文字与背景亮度差异显著（暗字或亮字）
    dark = (gray < max(0, med - 35)).astype(np.uint8) * 255
    light = (gray > min(255, med + 35)).astype(np.uint8) * 255
    text = cv2.bitwise_or(dark, light)
    # 形态学清理噪点
    text = cv2.morphologyEx(text, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(text)
    if n <= 1:
        return None, (x0i, y0i, x1i, y1i)
    # 取面积较大的连通域（过滤 <40px 噪点），合并 bbox
    boxes = [stats[i] for i in range(1, n) if stats[i][4] >= 40]
    if not boxes:
        boxes = [stats[i] for i in range(1, n)]
    xs0 = min(b[0] for b in boxes); ys0 = min(b[1] for b in boxes)
    xs1 = max(b[0] + b[2] for b in boxes); ys1 = max(b[1] + b[3] for b in boxes)
    # 膨胀 12px 余量，并限制在搜索区内
    pad = 12
    bx0 = max(0, x0i + xs0 - pad); by0 = max(0, y0i + ys0 - pad)
    bx1 = min(w, x0i + xs1 + pad); by1 = min(h, y0i + ys1 + pad)
    return (bx0, by0, bx1, by1), (x0i, y0i, x1i, y1i)

def build_text_mask(h, w, bbox):
    """文字级 mask（0/255 硬边，供 LaMa）"""
    mask = np.zeros((h, w), dtype=np.uint8)
    x0, y0, x1, y1 = bbox
    mask[y0:y1, x0:x1] = 255
    return mask

def feather_merge(orig, repaired, mask, feather=14):
    """软边融合：边界按高斯权重渐变，消除接缝"""
    soft = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigmaX=feather)
    w = (soft / 255.0)[..., None]
    return (orig.astype(np.float32) * (1 - w) + repaired.astype(np.float32) * w).astype(np.uint8)

def residual_check(img, bbox, thr_area=300):
    """修复后残留检测：bbox 区域内是否仍有明显文字特征"""
    x0, y0, x1, y1 = bbox
    region = img[y0:y1, x0:x1]
    if region.size == 0:
        return False
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    med = int(np.median(gray))
    text = cv2.bitwise_or((gray < max(0, med - 35)).astype(np.uint8) * 255,
                          (gray > min(255, med + 35)).astype(np.uint8) * 255)
    text = cv2.morphologyEx(text, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return int((text > 0).sum()) > thr_area

def process(model, path, hd_strategy, out_path=None, debug_dir=None):
    from iopaint.schema import InpaintRequest
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"无法读取: {path}")
    h, w = img.shape[:2]
    bbox, search = detect_watermark_bbox(img, SEARCH_X0, SEARCH_Y0, SEARCH_X1, SEARCH_Y1)
    if bbox is None:
        raise ValueError("未检测到水印文字（搜索区无显著文字特征）")
    mask = build_text_mask(h, w, bbox)
    req = InpaintRequest(hd_strategy=hd_strategy)
    repaired = model(img, mask, req)
    result = feather_merge(img, repaired, mask)
    residual = residual_check(result, bbox)
    if out_path is None:
        out_path = path
    cv2.imwrite(out_path, result)
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        # mask 覆盖预览：红色半透明显示修复范围
        overlay = img.copy()
        overlay[bbox[1]:bbox[3], bbox[0]:bbox[2]] = (
            overlay[bbox[1]:bbox[3], bbox[0]:bbox[2]] * 0.5 +
            np.array([0, 0, 255], np.uint8) * 0.5).astype(np.uint8)
        cv2.imwrite(os.path.join(debug_dir, os.path.basename(path).replace(".png", "_mask预览.png")), overlay)
    return bbox, residual

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--out", default=None)
    ap.add_argument("--hd", default="resize", choices=["resize", "crop", "original"])
    ap.add_argument("--debug", action="store_true", help="输出 mask 覆盖预览图")
    a = ap.parse_args()

    from iopaint.model import LaMa
    print("加载 LaMa 模型（CPU）...")
    model = LaMa(device="cpu")

    files = []
    if os.path.isdir(a.target):
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
        debug_dir = os.path.join(a.out or os.path.dirname(f), "debug") if a.debug else None
        try:
            import time
            t0 = time.time()
            bbox, residual = process(model, f, a.hd, out, debug_dir)
            tag = "⚠️ 疑似残留" if residual else "✅"
            print(f"{tag} {os.path.basename(f)}  水印bbox{bbox} 耗时{time.time()-t0:.1f}s")
        except Exception as e:
            print(f"❌ {os.path.basename(f)}: {e}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
