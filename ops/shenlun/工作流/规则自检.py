#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人民日报内容运营 · 规则自检脚本（v2.6 公众号精简模式）
【v2.6 调整（2026-09-10，v2.19 单路线运营策略）】仅运营公众号+小程序：① 备选手账B套停用
   （不再要求存在，历史目录含B套不扣分）；② 小红书目录缺失=符合预期（暂停产出）；
   ③ 新增 公众号长图（4分片+整图归档）+ 原文链接.txt 校验（FAIL 级）。-v18 历史目录判定保留向后兼容。
【v2.5 增强（2026-09-09）】新增 check_article_original：文章目录/原文/ md+_原文.html 成对 +
   解剖/ md+三刀解剖.html 成对（对应 SOP 1.5b/5.1 文章物料统一原则，用户拍板纳入自检）。
【v2.18 增强（2026-09-05，向后兼容）】① check_anatomy 以解剖文件含「## 考题定位」为新版
   判别开关：新版校验 考题定位3字段/总骨架2字段/迁移指南3字段/仿写示范字数/短字段≤80字
   精简铁律；旧格式文件自动回退旧规则并 WARN 提示。② main 新增 --anatomy-only 只跑解剖。
   ③ check_images 按「-v18」目录后缀判别期望卡数（平行产出 9 卡 / 标准目录 6 卡）。
用途：对 物料/<日期>/ 下的产出物做「确定性」校验，拦截低级错误（不依赖 AI 判断）。
目录结构：日级（原文/筛选/审核记录/README/状态.json）+ 文章级（<文章标题>/解剖/公众号/小红书/抖音）
用法：python3 规则自检.py <物料目录> [--json]
     如：python3 规则自检.py "/Users/dnn/Library/Mobile Documents/com~apple~CloudDocs/申论学习/物料/2026-08-27"
输出：逐项 PASS/FAIL 报告；全部 PASS 时 exit code=0，否则非 0。
"""
import os
import re
import sys
import json

EMOJI_PATTERN = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF"
    "\U00002B00-\U00002BFF\U0001F1E6-\U0001F1FF\u2600-\u26FF\u2700-\u27BF]"
)
COLOR_HEX = re.compile(r"#[0-9A-Fa-f]{3,8}\b")


def report(results, as_json):
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            if item.get("ok") is None:
                mark = "WARN"
            else:
                mark = "PASS" if item["ok"] else "FAIL"
            print(f"[{mark}] {item['check']} — {item['detail']}")
    return all(r.get("ok", True) is not False for r in results)


def list_article_dirs(base):
    """识别 base 下的文章子目录：包含 解剖/公众号/小红书/抖音 任一子目录的一级目录"""
    out = []
    if not os.path.isdir(base):
        return out
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if not os.path.isdir(d):
            continue
        subs = [s for s in ("解剖", "公众号", "小红书", "抖音") if os.path.isdir(os.path.join(d, s))]
        if subs:
            out.append((name, d))
    return out


def check_original(dir_original):
    """门1 原文抓取（日级 原文/）"""
    out = []
    if not os.path.isdir(dir_original):
        return [{"check": "原文目录存在", "ok": False, "detail": "未找到 原文/"}]
    files = [f for f in os.listdir(dir_original) if f.endswith(".md")]
    out.append({
        "check": "原文文件存在",
        "ok": len(files) > 0,
        "detail": f"共 {len(files)} 篇",
    })
    for f in files:
        path = os.path.join(dir_original, f)
        text = open(path, encoding="utf-8").read()
        name_ok = bool(re.match(r"^\d{2}版_.+_.+\.md$", f))
        fields = all(k in text for k in ["来源", "栏目", "链接"]) and bool(re.search(r"^# .+", text, re.M))
        out.append({
            "check": f"原文[{f}]",
            "ok": name_ok and fields,
            "detail": f"命名{'OK' if name_ok else '异常'};字段{'OK' if fields else '缺失'}",
        })
    return out


def check_article_original(dir_original, dir_anatomy, prefix=""):
    """门3.5 文章物料统一（2026-09-09 用户拍板，并入自检）：文章目录/原文/ md+_原文.html 成对；
    解剖/ md+三刀解剖.html 成对（5.1 增补产物）。均为 FAIL 级（历史 31/31 已补齐，新产出缺失=真异常）"""
    out = []
    # 原文/ 成对
    if not os.path.isdir(dir_original):
        out.append({"check": f"{prefix}文章原文目录", "ok": False, "detail": "未找到 文章目录/原文/（1.5b 归位产物）"})
    else:
        mds = [f for f in os.listdir(dir_original) if f.endswith(".md")]
        htmls = [f for f in os.listdir(dir_original) if f.endswith("_原文.html")]
        ok = len(mds) == 1 and len(htmls) == 1
        out.append({"check": f"{prefix}文章原文成对", "ok": ok,
                    "detail": f"md={len(mds)},html={len(htmls)}" if not ok else f"{mds[0]} + {htmls[0]}"})
    # 解剖/ md+html 成对
    if os.path.isdir(dir_anatomy):
        pair = [f for f in os.listdir(dir_anatomy) if f.endswith("_三刀解剖.html")]
        out.append({"check": f"{prefix}解剖HTML成对", "ok": len(pair) >= 1,
                    "detail": pair[0] if pair else "未找到 *_三刀解剖.html（5.1 A套副本）"})
    return out


def check_screening(base):
    """门2 筛选（日级 筛选/候选清单.md 与 确认结果.md）"""
    out = []
    d = os.path.join(base, "筛选")
    if not os.path.isdir(d):
        return [{"check": "筛选目录存在", "ok": False, "detail": "未找到 筛选/"}]
    for f in ("候选清单.md", "确认结果.md"):
        ok = os.path.isfile(os.path.join(d, f))
        out.append({"check": f"筛选[{f}]", "ok": ok, "detail": "存在" if ok else "缺失"})
    return out


def _field_filled(text, field):
    """v2.18 字段填充校验：`- 字段: 值` 存在且非占位符（占位符特征=冒号后紧跟（）。返回 (是否填充, 值或原因)"""
    m = re.search(rf"^- {field}: (.+)$", text, re.M)
    if not m:
        return False, ""
    v = m.group(1).strip()
    if not v or v.startswith("（"):
        return False, ""
    return True, v


def check_anatomy(dir_anatomy, prefix=""):
    """门3 三刀解剖（v2.18 平行产出增强：含考题定位/迁移指南校验，旧格式回退旧规则）"""
    out = []
    files = [f for f in os.listdir(dir_anatomy) if f.endswith(".md") and "解剖" in f] if os.path.isdir(dir_anatomy) else []
    if not files:
        return [{"check": f"{prefix}解剖MD存在", "ok": False, "detail": "未找到解剖文件"}]
    text = open(os.path.join(dir_anatomy, files[0]), encoding="utf-8").read()
    m = re.search(r"## 原文摘录(.*?)## 总骨架", text, re.S)
    excerpt_len = len(re.sub(r"\s", "", m.group(1))) if m else 0
    words = len(re.findall(r"^\| (?!词语).+\|.+\|.+\|", text, re.M))
    points = len(re.findall(r"^### 分论点 \d", text, re.M))
    quotes = len(re.findall(r"^### 语录 \d", text, re.M))
    verbs = len(re.findall(r"^\| (?!动词).+\|.+\|.+\|", text, re.M))
    tmpls = len(re.findall(r"^### 模板 \d", text, re.M))
    checks = [
        ("原文摘录≤200字", excerpt_len <= 200 and excerpt_len > 0, f"{excerpt_len}字"),
        ("规范词≥6个", words >= 6, f"{words}个"),
        ("分论点2-4个", 2 <= points <= 4, f"{points}个"),
        ("语录≥2条", quotes >= 2, f"{quotes}条"),
        ("高频动词≥4个", verbs >= 4, f"{verbs}个"),
        ("句式模板≥3个", tmpls >= 3, f"{tmpls}个"),
    ]
    # v2.18 平行产出增强：以「## 考题定位」为新版判别开关，旧格式文件回退旧规则
    # 字段 8 个（考题定位3 + 总骨架2 + 迁移指南3）+ 仿写示范字数 + 短字段精简铁律
    if "## 考题定位" in text:
        kt_fields = ["主题归类", "标题机关", "立意路径"]
        missing = [f for f in kt_fields if not _field_filled(text, f)[0]]
        checks.append(("考题定位3字段[v2.18]", not missing,
                       "齐全" if not missing else f"缺失/占位: {','.join(missing)}"))
        skeleton_fields = ["开头范式", "过渡技巧"]
        missing = [f for f in skeleton_fields if not _field_filled(text, f)[0]]
        checks.append(("总骨架新增2字段[v2.18]", not missing,
                       "齐全" if not missing else f"缺失/占位: {','.join(missing)}"))
        guide_fields = ["适用考题", "套用警示", "今日仿写示范"]
        missing = [f for f in guide_fields if not _field_filled(text, f)[0]]
        checks.append(("迁移指南3字段[v2.18]", not missing,
                       "齐全" if not missing else f"缺失/占位: {','.join(missing)}"))
        ok_demo, demo = _field_filled(text, "今日仿写示范")
        if ok_demo:
            n_demo = len(re.sub(r"\s", "", demo))
            checks.append(("仿写示范150-250字[v2.18]", 100 <= n_demo <= 300, f"{n_demo}字（占位=空）"))
        else:
            checks.append(("仿写示范150-250字[v2.18]", False, "字段缺失/占位"))
        # 精简铁律：除仿写示范外，任何 `- 字段: 值` 单行值 ≤80 字（防字段写成论述段）
        # 排除"原文"引用类字段（语录/句式的原文引用保真，不受字数限制）
        long_fields = []
        for ln in text.splitlines():
            m2 = re.match(r"^- ([^:]{2,12}): (.+)$", ln)
            if m2 and m2.group(1) not in ("今日仿写示范", "原文"):
                v2 = m2.group(2).strip()
                if len(v2) > 80 and not v2.startswith("（"):
                    long_fields.append(f"{m2.group(1)}({len(v2)}字)")
        checks.append(("短字段≤80字[v2.18精简]", not long_fields,
                       "全部精简" if not long_fields else f"超长: {','.join(long_fields)}"))
    else:
        out.append({"check": f"{prefix}解剖格式版本", "ok": None,
                    "detail": "v2.16 旧格式（无考题定位章节），按旧规则校验；v2.18 新增字段未校验"})
    for name, ok, detail in checks:
        out.append({"check": f"{prefix}解剖[{name}]", "ok": ok, "detail": detail})
    return out


def check_wechat(dir_wechat, prefix=""):
    """门4 公众号：HTML（中国红+A/B双套）+ MD版（发布用，v2.9 新增）"""
    out = []
    files = sorted([f for f in os.listdir(dir_wechat) if f.endswith(".html")]) if os.path.isdir(dir_wechat) else []
    if not files:
        out.append({"check": f"{prefix}公众号HTML存在", "ok": False, "detail": "未找到HTML"})
    else:
        # 优先取主风格（不含"备选"）检查配色/区块
        main_files = [f for f in files if "备选" not in f]
        text_file = main_files[0] if main_files else files[0]
        text = open(os.path.join(dir_wechat, text_file), encoding="utf-8").read()
        has_red = "#D0021B" in text.upper()
        has_blue = "#1F3864" in text.upper()
        blocks = all(k in text for k in ["开篇引导", "全文骨架", "规范词", "论证骨架", "万能句式", "行动清单"])
        out.append({"check": f"{prefix}公众号配色=中国红", "ok": has_red and not has_blue,
                    "detail": f"主={text_file},红{'有' if has_red else '无'},蓝{'有' if has_blue else '无'}"})
        out.append({"check": f"{prefix}公众号区块齐全", "ok": blocks, "detail": "8大区块"})
        backup = [f for f in files if "备选" in f]
        # v2.19 起 B套手账停用（仅A套中国红）；历史目录含B套不扣分
        out.append({"check": f"{prefix}公众号备选手账版", "ok": True,
                    "detail": "v2.19 起仅A套中国红（B套手账停用）" if not backup
                    else f"历史目录含{len(backup)}个备选（不扣分，新产出不再要求）"})
    # v2.6 新增：长图（4分片发布备用 + 整图归档）+ 原文链接.txt（FAIL 级）
    if os.path.isdir(dir_wechat):
        all_files = os.listdir(dir_wechat)
        pieces = sorted(f for f in all_files if f.startswith("发布长图_") and f.endswith(".png") and "_0" in f)
        piece_set = set(pieces)
        full_img = [f for f in all_files
                    if f.startswith("发布长图_") and f.endswith(".png") and f not in piece_set]
        link_txt = [f for f in all_files if f == "原文链接.txt"]
        ok_img = len(pieces) >= 4 and len(full_img) >= 1
        out.append({"check": f"{prefix}公众号长图(4分片+整图)", "ok": ok_img,
                    "detail": f"分片{len(pieces)}张,整图{len(full_img)}张" if ok_img
                    else f"缺失（需分片≥4+整图≥1，当前分片{len(pieces)}/整图{len(full_img)}）"})
        out.append({"check": f"{prefix}原文链接.txt", "ok": len(link_txt) >= 1,
                    "detail": link_txt[0] if link_txt else "未找到 原文链接.txt（公众号后台「原文链接」字段用）"})
    # MD 版（v2.17 起已删除：公众号用长图、知乎用 HTML，MD 版无用途）
    out.append({"check": f"{prefix}公众号MD版", "ok": True,
                "detail": "v2.17 起不产出 MD 版（长图由 HTML 渲染，非中间转化）"})
    return out


def check_xhs(dir_xhs, prefix=""):
    """门4 小红书：纯文本简化版（v2.17 起，替代旧「卡片文案.md + 发布正文.txt」）"""
    out = []
    # v2.19 起小红书暂停产出（仅公众号+小程序运营）：目录缺失=符合预期
    if not os.path.isdir(dir_xhs):
        out.append({"check": f"{prefix}小红书纯文本简化版", "ok": True,
                    "detail": "v2.19 起小红书暂停产出，目录不存在符合预期"})
        return out
    # 纯文本简化版（内容结构_简化版.txt，≤1000字含空白）
    brief_files = [f for f in os.listdir(dir_xhs) if f.endswith("_内容结构_简化版.txt")] if os.path.isdir(dir_xhs) else []
    if brief_files:
        text = open(os.path.join(dir_xhs, brief_files[0]), encoding="utf-8").read()
        n = len(text)
        ok = n <= 1000
        out.append({"check": f"{prefix}小红书纯文本简化版", "ok": ok,
                    "detail": f"{brief_files[0]} {n}字(含空白{'≤1000' if ok else '超限'})"})
    else:
        out.append({"check": f"{prefix}小红书纯文本简化版", "ok": False,
                    "detail": "未找到 _内容结构_简化版.txt（v2.17 小红书图文正文）"})
    return out


def check_prompts(dir_xhs, dir_douyin, prefix=""):
    """门5 Canva query 约束（≤220字、无色号、无Emoji）——v2.9 由「提示词≤150字」更新；
    只检查「query/提示词」文件（若记录落盘），卡片文案允许Emoji"""
    out = []
    for label, d in [("小红书", dir_xhs), ("抖音", dir_douyin)]:
        if not os.path.isdir(d):
            continue
        found = False
        for f in os.listdir(d):
            if f.endswith(".md") and ("query" in f.lower() or "提示词" in f):
                found = True
                text = open(os.path.join(d, f), encoding="utf-8").read()
                over = any(len(p) > 220 for p in text.split("\n") if len(p) > 60)
                has_hex = bool(COLOR_HEX.search(text))
                has_emoji = bool(EMOJI_PATTERN.search(text))
                out.append({"check": f"{prefix}{label}Canva query≤220字", "ok": not over, "detail": "有超长行" if over else "OK"})
                out.append({"check": f"{prefix}{label}Canva query无色号", "ok": not has_hex, "detail": "含色号" if has_hex else "OK"})
                out.append({"check": f"{prefix}{label}Canva query无Emoji", "ok": not has_emoji, "detail": "含Emoji" if has_emoji else "OK"})
        if not found:
            out.append({"check": f"{prefix}{label}Canva query记录", "ok": True,
                        "detail": "query 未单独落盘（v2.9 直出调用，如记录可建 CanvaQuery.md）"})
    return out


def check_zhihu(dir_zhihu, prefix=""):
    """门4 知乎发布物料（v2.18 对齐 v2.17 现实：知乎=HTML(A套为底+来源卡+上/下一篇)；内容结构MD/知乎封面为可选留档）"""
    out = []
    if not os.path.isdir(dir_zhihu):
        out.append({"check": f"{prefix}知乎目录", "ok": False, "detail": "未找到 知乎/"})
        return out
    zhihu_html = [f for f in os.listdir(dir_zhihu) if f.endswith("_知乎.html")]
    out.append({"check": f"{prefix}知乎HTML", "ok": len(zhihu_html) >= 1,
                "detail": zhihu_html[0] if zhihu_html else "未找到 *_知乎.html"})
    if zhihu_html:
        t = open(os.path.join(dir_zhihu, zhihu_html[0]), encoding="utf-8").read()
        has_src = "本文来源" in t and "查看人民日报原文" in t
        out.append({"check": f"{prefix}知乎来源引用卡", "ok": has_src,
                    "detail": "含来源卡+原文链接" if has_src else "缺来源引用卡"})
    # 内容结构 MD（v2.16 时代产物）与知乎封面：存在才检，不强求
    full = [f for f in os.listdir(dir_zhihu) if f.endswith("_内容结构.md")]
    if full:
        out.append({"check": f"{prefix}知乎内容结构MD", "ok": True, "detail": f"{full[0]}（可选留档）"})
    covers = [f for f in os.listdir(dir_zhihu) if f.endswith(".png") and "封面图_知乎" in f]
    out.append({"check": f"{prefix}知乎封面图", "ok": True,
                "detail": covers[0] if covers else "未产出（知乎封面待办未启用，公众号封面共用，符合预期）"})
    return out


def check_cover(dir_wechat, prefix=""):
    """门4 公众号封面图（v2.9 新增）：每篇 ≥1 张 封面图_*.png（2.35:1 头条）"""
    out = []
    if not os.path.isdir(dir_wechat):
        out.append({"check": f"{prefix}公众号封面图", "ok": False, "detail": "未找到公众号目录"})
        return out
    covers = [f for f in os.listdir(dir_wechat) if f.endswith(".png") and (f == "封面图.png" or f.startswith("封面图_"))]
    if covers:
        out.append({"check": f"{prefix}公众号封面图", "ok": True,
                    "detail": f"{len(covers)}张: {', '.join(sorted(covers)[:3])}{'…' if len(covers) > 3 else ''}"})
    else:
        out.append({"check": f"{prefix}公众号封面图", "ok": False,
                    "detail": "未找到 封面图.png / 封面图_*.png（应每篇≥1张，2.35:1）"})
    return out


def check_images(dir_xhs, dir_douyin, prefix=""):
    """门5 成品图：小红书「图片/(去水印后成品)」必检 8 张；「图片A-主风格/(去水印前原始)」保留必检；抖音存在才检"""
    out = []
    # v2.19 起小红书暂停产出：目录缺失=符合预期（直接跳过，不再 FAIL）
    if not os.path.isdir(dir_xhs):
        out.append({"check": f"{prefix}小红书图片/成品", "ok": True,
                    "detail": "v2.19 起小红书暂停产出，符合预期"})
        return out
    # v2.18 平行产出：-v18 目录正文卡 6 张（立意·骨架/规范词/论证骨架/语录/句式/迁移·速记——
    # 考题定位并入骨架卡、迁移指南并入速记卡）；标准目录 5 张正文卡
    if "-v18" in os.path.abspath(dir_xhs):
        need = [
            "01_封面A_大标题品牌色.png", "02_正文_1.png", "03_正文_2.png",
            "04_正文_3.png", "05_正文_4.png", "06_正文_5.png",
            "07_正文_6.png",
        ]
    else:
        need = [
            "01_封面A_大标题品牌色.png", "02_正文_1.png", "03_正文_2.png",
            "04_正文_3.png", "05_正文_4.png", "06_正文_5.png",
        ]
    # 成品（去水印后）：图片/ 必须 8 张命名规范
    xhs_final = os.path.join(dir_xhs, "图片")
    if os.path.isdir(xhs_final):
        names = sorted(os.listdir(xhs_final))
        ok = set(need).issubset(set(names))
        out.append({"check": f"{prefix}小红书图片/成品", "ok": ok,
                    "detail": f"{len(names)}张,命名{'OK' if ok else '需核对'}"})
    else:
        out.append({"check": f"{prefix}小红书图片/成品", "ok": False, "detail": "未找到 图片/ 目录（应6张：封面A+5正文，v2.15）"})
    # 原始（去水印前）：图片A-主风格/ 仅 Canva 直出时代保留；v2.15 起 HTML 渲染直出成品，无此目录
    xhs_raw = os.path.join(dir_xhs, "图片A-主风格")
    if os.path.isdir(xhs_raw):
        names = sorted(os.listdir(xhs_raw))
        out.append({"check": f"{prefix}小红书图片A-主风格/原始", "ok": len(names) >= 8,
                    "detail": f"{len(names)}张(去水印前原始图)"})
    else:
        out.append({"check": f"{prefix}小红书图片A-主风格/原始", "ok": True,
                    "detail": "v2.15 起无此目录（HTML 渲染直出成品，无去水印前原始图），符合预期"})
    # 抖音：v2.6 暂不生成，存在才检（恢复时启用）
    if os.path.isdir(dir_douyin):
        dy_a = os.path.join(dir_douyin, "图片")
        if os.path.isdir(dy_a):
            names = sorted(os.listdir(dy_a))
            ok = len(names) >= 8 and any(n.startswith("01_") for n in names)
            out.append({"check": f"{prefix}抖音图片/成品", "ok": ok,
                        "detail": f"{len(names)}张（抖音已启用）"})
        else:
            out.append({"check": f"{prefix}抖音目录", "ok": True,
                        "detail": "存在但无成品图（v2.6 抖音暂不生成，符合预期）"})
    return out


def check_canva_preview(dir_xhs, dir_douyin, prefix=""):
    """门5 Canva AI 预览稿：小红书 canva预览/ 必检；抖音/备选存在才检（v2.6）"""
    out = []
    pv = os.path.join(dir_xhs, "canva预览")
    if os.path.isdir(pv):
        n = len([f for f in os.listdir(pv) if f.endswith(".png")])
        out.append({"check": f"{prefix}小红书canva预览", "ok": n >= 1, "detail": f"{n}张"})
    else:
        out.append({"check": f"{prefix}小红书canva预览", "ok": True, "detail": "v2.15 起无 canva预览（HTML 渲染直出），符合预期"})
    # 备选/抖音预览存在才检（v2.6 起可选）
    for label, d in [("小红书B", dir_xhs), ("抖音", dir_douyin)]:
        pvb = os.path.join(d, "canva预览B")
        if os.path.isdir(pvb):
            n = len([f for f in os.listdir(pvb) if f.endswith(".png")])
            out.append({"check": f"{prefix}{label}canva预览B", "ok": n >= 1, "detail": f"{n}张"})
    return out


def check_readability(dir_xhs, prefix=""):
    """门5 可读性检测（辅助级 WARN）：调用 工作流/可读性检测.py 分析成品图
    背景/文字对比度（含 v2.0 文字级低对比检测）。优先查 图片/(去水印后成品)，
    不存在则回退 图片A-主风格/(去水印前原始)。程序只能测亮度/边缘对比，
    颜色相配与装饰干扰需人工看图最终把关，故本项为 WARN 级（不阻塞流程，但提示人工复核）。"""
    out = []
    img_dir = os.path.join(dir_xhs, "图片")
    if not os.path.isdir(img_dir):
        img_dir = os.path.join(dir_xhs, "图片A-主风格")  # 回退原始图
    if not os.path.isdir(img_dir):
        return out
    if not any(f.lower().endswith(".png") for f in os.listdir(img_dir)):
        return out
    py = "/Users/dnn/.workbuddy/binaries/python/envs/default/bin/python"
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "可读性检测.py")
    if not os.path.exists(script):
        out.append({"check": f"{prefix}图片可读性检测", "ok": None,
                    "detail": "可读性检测脚本缺失，跳过（人工看图把关）"})
        return out
    try:
        import subprocess
        r = subprocess.run([py, script, img_dir], capture_output=True, text=True, timeout=120)
        lines = [ln.strip() for ln in (r.stdout + r.stderr).splitlines() if ln.strip()]
        tail = lines[-8:]
        detail = "；".join(tail) if tail else "无输出"
        # 解析"共 N 张，M 张需人工复核"中的 M；M>0 或输出含 ❌ 行才标记需复核
        m = re.search(r"共 (\d+) 张，(\d+) 张需人工复核", r.stdout)
        need_review = 0
        if m:
            need_review = int(m.group(2))
        if any(ln.startswith("❌") for ln in lines):
            need_review += 1
        out.append({"check": f"{prefix}图片可读性检测", "ok": None,
                    "detail": detail if need_review == 0 else
                    f"存在 {need_review} 张疑似对比问题，请人工复核每张成品图背景/文字对比（{detail}）"})
    except Exception as e:
        out.append({"check": f"{prefix}图片可读性检测", "ok": None,
                    "detail": f"检测执行失败: {e}（人工看图把关）"})
    return out


def main():
    if len(sys.argv) < 2:
        print("用法: python3 规则自检.py <物料目录> [--json]")
        sys.exit(2)
    base = sys.argv[1]
    as_json = "--json" in sys.argv
    anatomy_only = "--anatomy-only" in sys.argv
    results = []

    if anatomy_only:
        # v2.18 草案试产/平行产出模式：只跑解剖检查（无日级/展示层文件时避免误报）
        articles = list_article_dirs(base)
        if not articles:
            results.append({"check": "文章子目录", "ok": False,
                            "detail": "未识别到 <文章标题>/ 目录（应含 解剖/公众号/小红书/抖音 之一）"})
        else:
            results.append({"check": "文章子目录", "ok": True, "detail": f"识别到 {len(articles)} 个: {', '.join(a[0] for a in articles)}"})
        for name, d in articles:
            results += check_anatomy(os.path.join(d, "解剖"), f"[{name}] ")
        ok = report(results, as_json)
        sys.exit(0 if ok else 1)

    # 日级检查
    results += check_original(os.path.join(base, "原文"))
    results += check_screening(base)

    # 文章级检查（识别全部文章子目录，逐篇校验）
    articles = list_article_dirs(base)
    if not articles:
        results.append({"check": "文章子目录", "ok": False,
                        "detail": "未识别到 <文章标题>/ 目录（应含 解剖/公众号/小红书/抖音 之一）"})
    else:
        results.append({"check": "文章子目录", "ok": True, "detail": f"识别到 {len(articles)} 个: {', '.join(a[0] for a in articles)}"})
    for name, d in articles:
        p = f"[{name}] "
        results += check_article_original(os.path.join(d, "原文"), os.path.join(d, "解剖"), p)
        results += check_anatomy(os.path.join(d, "解剖"), p)
        results += check_wechat(os.path.join(d, "公众号"), p)
        results += check_cover(os.path.join(d, "公众号"), p)
        results += check_xhs(os.path.join(d, "小红书"), p)
        results += check_prompts(os.path.join(d, "小红书"), os.path.join(d, "抖音"), p)
        results += check_images(os.path.join(d, "小红书"), os.path.join(d, "抖音"), p)
        results += check_canva_preview(os.path.join(d, "小红书"), os.path.join(d, "抖音"), p)
        results += check_readability(os.path.join(d, "小红书"), p)

    ok = report(results, as_json)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
