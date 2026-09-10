# -*- coding: utf-8 -*-
"""可读性检测 v2.1 —— 背景/文字对比度 + 风格饱和度把关（辅助工具，最终以人工复核为准）

用法：
    python3 工作流/可读性检测.py <图片路径或目录>

检测四层：
- 全局指标：亮度动态范围、整体评分
- 网格低对比区：粗粒度找大面积低对比区域
- **文字级低对比检测（v2.0 新增，核心）**：
  文字存在 → 边缘密度高；对比充足 → 局部亮度方差高。
  「边缘密度高 但 局部方差低」= 文字笔画与背景颜色接近 → 看不见的文字。
  输出低对比文字区域的坐标，供人工定位。
- **整体饱和度（v2.1 新增·v2.17 起仅参考）**：饱和度作为信息输出，
  不再按「复古油墨风」标准判弃用（HTML 渲染卡片为白底+中国红，正文卡饱和度天然低）。

依赖：opencv + numpy（venv envs/default 已装）
局限：测亮度/边缘，色相对比（如红字压棕底但亮度相近）仍需人工看图最终把关。
"""
import os, sys
import numpy as np
import cv2


def _gray(path):
    return cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)


def global_score(gray):
    px = gray.ravel().astype(np.float32)
    std = float(px.std())
    dark = float((px < 90).mean()) * 100
    light = float((px > 165).mean()) * 100
    drange = int(px.max() - px.min())
    score = min(100, std * 2.2 + (dark + light) / 100 * 60)
    return dict(std=round(std, 1), dark=round(dark), light=round(light),
                drange=drange, score=round(score))


def low_contrast_regions(gray, grid=(4, 6)):
    h, w = gray.shape
    gw, gh = grid
    cw, ch = w // gw, h // gh
    lows = []
    for gy in range(gh):
        for gx in range(gw):
            cell = gray[gy*ch:(gy+1)*ch, gx*cw:(gx+1)*cw]
            std = float(cell.std())
            dyn = int(cell.max() - cell.min())
            mean = float(cell.mean())
            if dyn < 90 and 60 < mean < 200:
                lows.append((gx + 1, gy + 1, round(std), dyn, round(mean)))
    return lows


def text_contrast(gray, grid=(12, 16)):
    """文字级低对比检测：边缘密度高 + 局部亮度方差低 = 文字与背景颜色接近"""
    edges = cv2.Canny(gray, 50, 150)
    h, w = gray.shape
    gh, gw = grid
    ch, cw = h // gh, w // gw
    hits = []
    for gy in range(gh):
        for gx in range(gw):
            e = edges[gy*ch:(gy+1)*ch, gx*cw:(gx+1)*cw]
            cell = gray[gy*ch:(gy+1)*ch, gx*cw:(gx+1)*cw]
            edge_density = float((e > 0).mean())
            std = float(cell.std())
            # 有文字/图案（边缘密度高）但明暗差异小（方差低）→ 低对比文字
            if edge_density > 0.04 and std < 28:
                hits.append((gx + 1, gy + 1, round(edge_density, 3), round(std, 1)))
    return hits


def saturation_metric(path):
    """整体饱和度（v2.17 起仅作信息参考）：
    HTML 渲染卡片为白底+中国红，正文卡饱和度天然低，不再据此判弃用。"""
    img = cv2.imread(path)
    if img is None:
        return 0.0
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return float(hsv[:, :, 1].mean())


def check(path):
    g = global_score(_gray(path))
    gray = _gray(path)
    lows = low_contrast_regions(gray)
    text_low = text_contrast(gray)
    sat = saturation_metric(path)
    problems = []
    if g["score"] < 40:
        problems.append(f"整体对比不足(评分{g['score']})")
    if len(lows) >= 4:
        problems.append(f"{len(lows)}个网格低对比区")
    if len(text_low) >= 6:
        problems.append(f"{len(text_low)}个低对比文字区(文字与背景颜色接近,可能看不清)")
    elif len(text_low) >= 2:
        problems.append(f"{len(text_low)}个低对比文字区(建议复核)")
    # 饱和度仅作信息参考（v2.17 起小红书卡片为 HTML 渲染「白底+中国红」，
    # 正文卡饱和度天然低，不再按「复古油墨风」标准判弃用）
    ok = not problems
    return dict(ok=ok, score=g["score"], drange=g["drange"],
                dark=g["dark"], light=g["light"], low_regions=len(lows),
                text_low=len(text_low), saturation=round(sat, 1),
                problems=problems)


def main(target):
    files = []
    if os.path.isdir(target):
        for root, _, fs in os.walk(target):
            for f in sorted(fs):
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    files.append(os.path.join(root, f))
    else:
        files = [target]
    if not files:
        print("未找到图片"); return 1
    failed = 0
    for f in files:
        try:
            r = check(f)
        except Exception as e:
            print(f"❌ {os.path.basename(f)}: {e}"); failed += 1; continue
        tag = "❌" if not r["ok"] else ("⚠️" if r["text_low"] else "✅")
        rel = os.path.relpath(f, target if os.path.isdir(target) else os.path.dirname(target))
        print(f"{tag} {rel}  评分{r['score']} 饱和{r['saturation']} 低对比区{r['low_regions']} 低对比文字{r['text_low']}"
              + (f"  {','.join(r['problems'])}" if r["problems"] else ""))
        if not r["ok"]:
            failed += 1
    print(f"\n共 {len(files)} 张，{failed} 张需人工复核")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1]))
