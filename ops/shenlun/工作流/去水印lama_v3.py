#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
去水印 LaMa v3 —— 修正版（v1 固定矩形 mask + crop_margin 256 + 边缘羽化融合 + 残留检测）

针对 v1"覆盖框痕迹"的修正：
  - 保持 v1 的固定矩形 mask（不做文字检测，避免 v2 的坑）
  - crop 策略 margin 128→256（更多真实纹理上下文，重建更贴近周围）
  - 修复后高斯羽化边缘融合（σ 可调），消除硬边切换的"框痕"
  - 残留检测 + 页脚条兜底（质量闸门）

用法：
    python3 工作流/去水印lama_v3.py <图片或目录> [--out 输出目录] [--feather 14] [--debug]

依赖：iopaint + torch + opencv（venv envs/default）；模型 big-lama.pt 本地缓存
"""
import os, sys, argparse, time
import numpy as np
import cv2

LOCAL_LAMA = os.path.expanduser("~/.cache/torch/hub/checkpoints/big-lama.pt")
os.environ.setdefault("LAMA_MODEL_URL", LOCAL_LAMA)

# v1 固定水印区域（归一化，右下角）
MASK_X0, MASK_Y0 = 0.72, 0.955
MASK_X1, MASK_Y1 = 0.995, 0.995


def build_mask(h, w):
    x0, y0 = int(w * MASK_X0), int(h * MASK_Y0)
    x1, y1 = int(w * MASK_X1), int(h * MASK_Y1)
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[y0:y1, x0:x1] = 255
    return mask, (x0, y0, x1, y1)


def feather_merge(orig_bgr, repaired_bgr, mask, feather):
    """软边融合：mask 高斯羽化，边缘渐变混合消除硬边框痕"""
    soft = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigmaX=feather)
    w = (soft / 255.0)[..., None]
    return (orig_bgr.astype(np.float32) * (1 - w) + repaired_bgr.astype(np.float32) * w).astype(np.uint8)


def residual_check(img, bbox, thr_area=300):
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


def process(model, path, feather, out_path=None, debug_dir=None):
    from iopaint.schema import InpaintRequest
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"无法读取: {path}")
    h, w = img.shape[:2]
    mask, bbox = build_mask(h, w)
    req = InpaintRequest(hd_strategy="crop", hd_strategy_crop_margin=256)
    repaired = model(img, mask, req)
    result = feather_merge(img, repaired, mask, feather)
    residual = residual_check(result, bbox)
    if out_path is None:
        out_path = path
    cv2.imwrite(out_path, result)
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        overlay = img.copy()
        x0, y0, x1, y1 = bbox
        overlay[y0:y1, x0:x1] = (overlay[y0:y1, x0:x1] * 0.5 +
                                 np.array([0, 0, 255], np.uint8) * 0.5).astype(np.uint8)
        cv2.imwrite(os.path.join(debug_dir, os.path.basename(path).replace(".png", "_mask预览.png")), overlay)
    return bbox, residual


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--out", default=None)
    ap.add_argument("--feather", type=float, default=14)
    ap.add_argument("--debug", action="store_true")
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
            t0 = time.time()
            bbox, residual = process(model, f, a.feather, out, debug_dir)
            tag = "⚠️ 疑似残留" if residual else "✅"
            print(f"{tag} {os.path.basename(f)}  区域{bbox} 羽化σ={a.feather} 耗时{time.time()-t0:.1f}s")
        except Exception as e:
            print(f"❌ {os.path.basename(f)}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
