#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智谱 CogView-4 可用性实测脚本
调用 https://open.bigmodel.cn/api/paas/v4/images/generations (OpenAI 兼容)
用法: python test_cogview.py --api-key <KEY> [--model cogview-4]
  Key 也可用环境变量 ZHIPU_API_KEY
输出: 保存 2 张测试卡(金句卡/规范词卡, 3:4 竖版)到 物料/2026-08-27/测试-智谱CogView/
"""
import argparse, base64, json, os, sys, time
import requests

ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/images/generations"
OUT_DIR = "/Users/dnn/Library/Mobile Documents/com~apple~CloudDocs/申论学习/物料/2026-08-27/测试-智谱CogView"

PROMPTS = {
    "金句卡": "一张小红书金句卡，竖版3比4。纯白背景，正中一个暗金色大引号，下方居中的深藏蓝粗体大字金句：“创新的领域天差地别，但其核心动力始终一致，那就是人对创造的冲动、对效率的追求、对梦想的执着”。底部一行暖橙色小字“申论创新主题金句·建议背诵”。极简优雅留白，文字准确清晰无错字。",
    "规范词卡": "一张小红书规范词卡，竖版3比4，暖米白背景。左上角深藏蓝粗体标题“今日必背规范词”。下方左对齐三个词条，每行“词语：白话解释”：厚植创新生态：培育创新环境与土壤；全谱系创新试验：容纳各层次创新尝试；新质生产力：科技创新主导的生产力。底部暗金色小字“三刀解剖法·人民日报时评拆解”。文字准确清晰无错字。",
}


def call_cogview(api_key, model, prompt, size, fname):
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": 1,
        "watermark": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(ENDPOINT, json=payload, headers=headers, timeout=120)
    except Exception as e:
        return f"[请求异常] {e}"
    if r.status_code != 200:
        return f"[HTTP {r.status_code}] {r.text[:300]}"
    data = r.json()
    if "data" not in data or not data["data"]:
        return f"[无图片返回] {json.dumps(data, ensure_ascii=False)[:300]}"
    os.makedirs(OUT_DIR, exist_ok=True)
    b64 = data["data"][0].get("b64_json")
    url = data["data"][0].get("url")
    if b64:
        img = base64.b64decode(b64)
        with open(fname, "wb") as f:
            f.write(img)
        return f"✅ 已保存 {os.path.basename(fname)} ({len(img)//1024}KB, b64)"
    if url:
        img = requests.get(url, timeout=60).content
        with open(fname, "wb") as f:
            f.write(img)
        return f"✅ 已保存 {os.path.basename(fname)} ({len(img)//1024}KB, url)"
    return f"[未知响应] {json.dumps(data, ensure_ascii=False)[:300]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.environ.get("ZHIPU_API_KEY", ""))
    ap.add_argument("--model", default="cogview-4")
    args = ap.parse_args()
    if not args.api_key:
        print("❌ 缺少 API Key：请用 --api-key <KEY> 传入，或设置环境变量 ZHIPU_API_KEY")
        sys.exit(1)
    print(f"模型: {args.model} | 尺寸: 864x1152 (3:4 竖版) | 端点: {ENDPOINT}\n")
    for name, prompt in PROMPTS.items():
        fname = os.path.join(OUT_DIR, f"{name}.png")
        print(f"生成 {name} ...")
        print(" ", call_cogview(args.api_key, args.model, prompt, "864x1152", fname))
        time.sleep(1)


if __name__ == "__main__":
    main()
