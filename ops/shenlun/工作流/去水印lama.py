#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
去水印 LaMa 版 v1.0 —— AI 修复模型（LaMa inpainting）去除右下角「包含AI生成」水印

原理：LaMa（大掩码修复模型）用深度学习语义重建水印区域背景，
      效果远超 OpenCV 算法填充；只处理水印区域，其余像素 100% 原样。

依赖：iopaint + torch（已装于 venv envs/default）；模型 big-lama.pt 在
      ~/.cache/torch/hub/checkpoints/（从 HF 镜像下载，200MB）

用法：
    python3 工作流/去水印lama.py <图片或目录> [--x0 0.72 --y0 0.955 --x1 0.995 --y1 0.995] [--out 输出目录]

参数为归一化坐标（0~1），默认右下角水印区域；可按实际水印位置调整。
"""
import os, sys, argparse, time
import numpy as np
import cv2

# 指向本地已下载的 LaMa 模型（HF 镜像下载，206MB），避免重新联网下载
LOCAL_LAMA = os.path.expanduser("~/.cache/torch/hub/checkpoints/big-lama.pt")
os.environ.setdefault("LAMA_MODEL_URL", LOCAL_LAMA)

def build_mask(h, w, x0, y0, x1, y1):
    x0i, y0i = int(w * x0), int(h * y0)
    x1i, y1i = int(w * x1), int(h * y1)
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[y0i:y1i, x0i:x1i] = 255
    # 边缘羽化，减少修复接缝
    mask = cv2.GaussianBlur(mask, (7, 7), 0)
    mask = (mask > 127).astype(np.uint8) * 255
    return mask, (x0i, y0i, x1i, y1i)

def process(model, path, x0, y0, x1, y1, out_path=None):
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"无法读取: {path}")
    h, w = img.shape[:2]
    mask, box = build_mask(h, w, x0, y0, x1, y1)
    from iopaint.schema import InpaintRequest
    # ⚠️ 通道顺序修复（2026-08-28）：iopaint LaMa 接口约定 输入=RGB、返回=BGR；
    # cv2.imread 返回 BGR，直接传入会把红蓝当反（成品整体偏色）。
    # 正确做法：读图后转 RGB 喂模型，模型返回的 BGR 结果直接 imwrite 即可。
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    t0 = time.time()
    result = model(img_rgb, mask, InpaintRequest())
    cost = time.time() - t0
    if out_path is None:
        out_path = path
    cv2.imwrite(out_path, result)
    return box, cost

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--x0", type=float, default=0.72)
    ap.add_argument("--y0", type=float, default=0.955)
    ap.add_argument("--x1", type=float, default=0.995)
    ap.add_argument("--y1", type=float, default=0.995)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    # 加载模型（首次会检查/下载 big-lama.pt）
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
        try:
            box, cost = process(model, f, a.x0, a.y0, a.x1, a.y1, out)
            print(f"✅ {os.path.basename(f)}  区域{box} 耗时{cost:.1f}s")
        except Exception as e:
            print(f"❌ {os.path.basename(f)}: {e}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
