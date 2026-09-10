# -*- coding: utf-8 -*-
"""封面智能裁剪：16:9 横版 → 2.35:1，自动避开文字区域（检测顶部/底部文字行）"""
import cv2, numpy as np, sys, os

def smart_crop(path, out_path, target=2.35, out_w=1800, out_h=766):
    img = cv2.imread(path)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 每行边缘强度（文字笔画 → 高梯度）
    sobel = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    row_energy = np.abs(sobel).mean(axis=1)  # 每行平均梯度
    # 找到留白区（低能量行），从顶部和底部各找连续留白
    blank_thresh = row_energy.mean() * 0.35
    blank = row_energy < blank_thresh
    # 顶部留白高度
    top_blank = 0
    for i in range(h):
        if blank[i]: top_blank += 1
        else: break
    # 底部留白高度
    bot_blank = 0
    for i in range(h-1, -1, -1):
        if blank[i]: bot_blank += 1
        else: break
    win_h = int(w / target)
    # 可用区域 = 去掉上下留白（但保留少量余量）
    usable_top = min(top_blank, max(0, h - win_h))  # 最靠上可放窗口的位置
    usable_bot = max(0, h - bot_blank - win_h)       # 最靠下可放窗口的位置
    usable_top = max(0, min(usable_top, usable_bot))
    # 在 [usable_top, usable_bot] 之间选居中位置（避开文字）
    y0 = int((usable_top + usable_bot) / 2)
    y0 = max(0, min(y0, h - win_h))
    crop = img[y0:y0+win_h, :]
    out = cv2.resize(crop, (out_w, out_h), interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(out_path, out)
    print(f"✅ {os.path.basename(path)}: 顶部留白{top_blank}px 底部留白{bot_blank}px 裁剪窗口y={y0}~{y0+win_h} 输出{out_w}x{out_h} 比例={out_w/out_h:.3f}")

if __name__ == "__main__":
    smart_crop(sys.argv[1], sys.argv[2])
