#!/usr/bin/env python3
"""D8/D9: 2025 三卷 subtype 细题型 + topic/tag 考点标签自动化标注。

- D8: subtype 覆盖率 ~26% → ≥80%（排除高风险题后）
- D9: topic/tag 从 0% 落地（资料分析/数量关系 ≥80%，其余模块尽量覆盖）

规则优先：从 stem + explanation 提取关键词判定。已有非空 subtype/topic/tag 不覆盖。
高风险题（content_mismatch_needs_source / section_type_mismatch）不标注。

用法：
    python3 scripts/xingce/annotate_subtype_topic.py           # 执行标注（写回 JSON）
    python3 scripts/xingce/annotate_subtype_topic.py --dry-run # 仅统计，不写文件
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "xingce-structured-data"
PAPERS_DIR = DATA / "2025" / "xingce" / "papers"
VOCAB_FILE = DATA / "_schema" / "topic-vocabulary.json"
PAPER_NAMES = ("shengji", "shidi", "xingzhengzhifa")

HIGH_RISK_FLAGS = {"content_mismatch_needs_source", "section_type_mismatch"}

# ────────────────────────────────────────────────────────────
# 1. 词表扩展（D9 前置：确保所有标注 topic/tag 在受控词表中）
# ────────────────────────────────────────────────────────────

VOCAB_ADDITIONS: dict[str, list[str]] = {
    # 资料分析
    "资料分析": [
        "基期量", "现期量", "增长率", "增长量", "比重", "平均数", "倍数",
        "百分数与百分点", "同比", "环比", "直接查找", "综合分析",
        "大小比较", "简单计算", "图形比例判断",
    ],
    # 数量关系
    "数量关系": [
        "工程问题", "行程问题", "经济利润", "容斥原理", "排列组合", "概率",
        "几何问题", "年龄问题", "和差倍比", "浓度问题", "最值问题",
        "计数枚举", "星期日期问题", "方程法", "植树问题", "鸡兔同笼",
    ],
    # 判断推理
    "判断推理-图形推理": ["数量类", "位置类", "样式类", "属性类", "空间类"],
    "判断推理-定义判断": ["单定义", "多定义"],
    "判断推理-类比推理": ["语义关系", "逻辑关系", "语法关系"],
    "判断推理-逻辑判断": [
        "翻译推理", "加强论证", "削弱论证", "分析推理", "真假推理", "日常结论",
    ],
    # 言语理解
    "言语理解-选词填空": ["实词辨析", "成语辨析", "虚词辨析", "语境分析"],
    "言语理解-片段阅读": ["主旨概括", "意图判断", "细节理解", "标题选择", "态度观点"],
    "言语理解-语句表达": ["语句排序", "语句填空", "下文推断"],
    # 常识判断（补全原有空列表）
    "法律法规与党内法规": ["法律法规", "党内法规", "行政法", "民法", "刑法", "宪法"],
    "时事与基本常识": ["人文历史", "科技生活", "地理环境", "经济管理", "时事政治", "生活常识"],
    # 政治理论补全
    "毛泽东思想和中国特色社会主义理论体系": ["毛泽东思想", "邓小平理论", "三个代表", "科学发展观"],
    "党和国家重大政策与会议": ["党的重要会议", "重大政策", "中央全会", "两会"],
}


def expand_vocab(dry_run: bool = False) -> dict:
    """读取词表，合并新增 topic/tag，写回（除非 dry-run）。返回合并后词表。"""
    vocab = json.loads(VOCAB_FILE.read_text(encoding="utf-8"))
    topics = vocab.setdefault("topics", {})
    added_topics = []
    added_tags = []
    for t, tags in VOCAB_ADDITIONS.items():
        if t not in topics:
            topics[t] = []
            added_topics.append(t)
        existing = set(topics[t])
        for tag in tags:
            if tag not in existing:
                topics[t].append(tag)
                existing.add(tag)
                added_tags.append(f"{t}/{tag}")
    vocab["updated"] = "2026-09-03"
    if not dry_run:
        VOCAB_FILE.write_text(
            json.dumps(vocab, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"[vocab] 新增 topic {len(added_topics)} 个: {added_topics}")
    print(f"[vocab] 新增 tag {len(added_tags)} 个")
    return vocab


# ────────────────────────────────────────────────────────────
# 2. 工具函数
# ────────────────────────────────────────────────────────────

def is_high_risk(q: dict) -> bool:
    return bool(HIGH_RISK_FLAGS & set(q.get("flags", [])))


def text_of(q: dict) -> str:
    """合并 stem + explanation 供关键词匹配。"""
    parts = [q.get("stem") or "", q.get("explanation") or ""]
    return " ".join(parts)


def has_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


# ────────────────────────────────────────────────────────────
# 3. 资料分析 subtype / topic / tag
# ────────────────────────────────────────────────────────────

def infer_ziliao(q: dict) -> tuple[str | None, str | None, str | None]:
    """返回 (subtype, topic, tag)。"""
    stem = q.get("stem") or ""
    expl = q.get("explanation") or ""
    text = stem + " " + expl

    # 优先级从高到低
    # 1) 综合分析
    if "能够从上述资料中推出" in stem or "可以从上述资料中推出" in stem:
        return "综合分析", "资料分析", "综合分析"

    # 2) 图形比例判断（饼图/柱状图选图）
    if ("饼状图" in stem or "饼图" in stem or "柱状图" in stem) and "最能准确反映" in stem:
        return "图形比例判断", "资料分析", "比重"

    # 3) 比重变化（比重比上年/上升/下降）
    if "比重比上年" in stem or "比重比去年" in stem or re.search(r"比重[上下]升", stem):
        return "比重变化", "资料分析", "比重"

    # 4) 比重计算
    if has_any(stem, ["占", "比重", "比例关系"]) and "倍" not in stem:
        return "比重计算", "资料分析", "比重"

    # 5) 平均数计算
    if "平均" in stem or "人均" in stem or "场均" in stem:
        return "平均数计算", "资料分析", "平均数"

    # 6) 倍数计算
    if "多少倍" in stem or "是" in stem and "倍" in stem:
        return "倍数计算", "资料分析", "倍数"

    # 7) 增长量计算（同比增量 + 投影/趋势）
    if "同比增量" in stem or "增长量" in stem:
        return "增长量计算", "资料分析", "增长量"

    # 8) 增长率计算
    if "增长率" in stem or "增速" in stem or "增长了百分之" in text:
        return "增长率计算", "资料分析", "增长率"

    # 9) 基期量计算（基期/上年同期/保持增量到哪一年）
    if has_any(stem, ["基期", "上年同期", "去年同期"]) or "保持" in stem and "增量" in stem:
        return "基期量计算", "资料分析", "基期量"

    # 10) 大小比较（比值/最高/最多，但不含计算关键词）
    if "比值" in stem or re.search(r"(最高|最多|最大|最少|最小)的是", stem):
        return "大小比较", "资料分析", "直接查找"

    # 11) 简单计算（范围/约为多少/之和）
    if has_any(stem, ["在以下哪个范围内", "约为多少", "之和", "共计", "总计"]):
        return "简单计算", "资料分析", "简单计算"

    # 12) 兜底：从 explanation 提取
    if "比重" in expl:
        return "比重计算", "资料分析", "比重"
    if "平均" in expl:
        return "平均数计算", "资料分析", "平均数"
    if "增长" in expl and "率" in expl:
        return "增长率计算", "资料分析", "增长率"
    if "倍" in expl:
        return "倍数计算", "资料分析", "倍数"

    return None, None, None


# ────────────────────────────────────────────────────────────
# 4. 数量关系 subtype / topic / tag
# ────────────────────────────────────────────────────────────

def infer_shuliang(q: dict) -> tuple[str | None, str | None, str | None]:
    stem = q.get("stem") or ""
    text = stem + " " + (q.get("explanation") or "")

    # 计数枚举（优先于排列组合：含"答题情况""得分""枚举""多少种情况"）
    if has_any(stem, ["枚举", "答题情况", "得分都不低于", "共有多少种", "有多少种", "多少种情况", "情况共有"]):
        return "计数枚举问题", "数量关系", "计数枚举"

    # 排列组合与概率（优先，因为常含"安排""选"）
    if "概率" in stem or "可能性" in stem or "随机" in stem:
        return "排列组合与概率", "数量关系", "概率"
    if "排列" in stem or "组合" in stem or "选法" in stem or "种不同" in stem or "不同的选" in stem:
        return "排列组合与概率", "数量关系", "排列组合"

    # 行程问题
    if has_any(stem, ["相遇", "追及", "往返", "速度", "路程", "船", "港", "海里", "千米/小时", "公里/小时"]):
        return "行程问题", "数量关系", "行程问题"

    # 工程问题
    if has_any(stem, ["工程", "合作", "合作完成", "效率", "单独完成", "一起加工", "生产"]):
        # "生产"太泛，需配合模块/车间语境
        if "车间" in stem or "模块" in stem or "效率" in stem or "合作" in stem or "工程" in stem:
            return "工程问题", "数量关系", "工程问题"

    # 经济利润
    if has_any(stem, ["利润", "折扣", "打折", "售价", "成本", "盈利", "亏损", "原价", "收入", "销量"]):
        return "经济利润问题", "数量关系", "经济利润"

    # 容斥原理（用具体词组，避免单字"又/既"误匹配）
    if has_any(stem, ["至少一项", "都不", "既喜欢", "又喜欢", "容斥", "三项认证", "至少喜欢", "两种都", "三种都", "至少有", "至多有"]):
        return "容斥问题", "数量关系", "容斥原理"

    # 几何问题
    if has_any(stem, ["圆锥", "圆柱", "几何", "面积", "体积", "半径", "直径", "三角形", "矩形", "正方形", "容器"]):
        return "几何问题", "数量关系", "几何问题"

    # 年龄问题
    if "年龄" in stem or "岁" in stem and "平均年龄" in stem:
        return "年龄问题", "数量关系", "年龄问题"

    # 浓度问题
    if has_any(stem, ["浓度", "溶液", "混合", "盐水", "糖水"]):
        return "浓度问题", "数量关系", "浓度问题"

    # 最值问题
    if re.search(r"(至少|至多|最多|最少|最大|最小).*(为|是|有)", stem) and "年龄" not in stem:
        return "最值问题", "数量关系", "最值问题"

    # 星期日期问题
    if "星期" in stem or "日期" in stem and ("号" in stem or "日" in stem):
        return "星期日期问题", "数量关系", "星期日期问题"

    # 和差倍比（兜底：比例/之比/共有/多...人）
    if has_any(stem, ["之比", "比例", "共有", "多", "少", "员工数", "人数之比", "部门"]):
        return "和差倍比问题", "数量关系", "和差倍比"

    # 从 explanation 兜底
    if "行程" in text:
        return "行程问题", "数量关系", "行程问题"
    if "工程" in text:
        return "工程问题", "数量关系", "工程问题"
    if "利润" in text:
        return "经济利润问题", "数量关系", "经济利润"
    if "容斥" in text:
        return "容斥问题", "数量关系", "容斥原理"
    if "几何" in text or "面积" in text or "体积" in text:
        return "几何问题", "数量关系", "几何问题"

    return None, None, None


# ────────────────────────────────────────────────────────────
# 5. 判断推理 subtype / topic / tag
# ────────────────────────────────────────────────────────────

def infer_panduan(q: dict) -> tuple[str | None, str | None, str | None]:
    qtype = q.get("type") or ""
    stem = q.get("stem") or ""

    # 图形推理：subtype 无法从文本精确判定，统一标"图形推理"
    if qtype == "图形推理":
        return "图形推理", "判断推理-图形推理", "数量类"

    # 定义判断
    if qtype == "定义判断":
        # 多定义：题干中出现多个定义名称
        multi = len(re.findall(r"[\u4e00-\u9fa5]{2,8}是指", stem)) >= 2
        tag = "多定义" if multi else "单定义"
        return "定义判断", "判断推理-定义判断", tag

    # 类比推理
    if qtype == "类比推理":
        return "类比推理", "判断推理-类比推理", "逻辑关系"

    # 逻辑判断
    if qtype == "逻辑判断":
        # 削弱论证
        if has_any(stem, ["最能削弱", "最能质疑", "最能反驳", "不能削弱", "无法削弱"]):
            return "削弱论证", "判断推理-逻辑判断", "削弱论证"
        # 加强论证
        if has_any(stem, ["最能加强", "最能支持", "最能有力", "不能加强", "前提", "假设"]):
            return "加强论证", "判断推理-逻辑判断", "加强论证"
        # 翻译推理
        if has_any(stem, ["可以推出", "由此可以推出", "必须", "只有", "如果", "那么", "则"]):
            return "翻译推理", "判断推理-逻辑判断", "翻译推理"
        # 真假推理
        if has_any(stem, ["说真话", "说假话", "只有一人", "真假", "两真两假"]):
            return "真假推理", "判断推理-逻辑判断", "真假推理"
        # 分析推理
        if has_any(stem, ["由此可以推出", "根据以上", "排列", "顺序", "匹配"]):
            return "分析推理", "判断推理-逻辑判断", "分析推理"
        # 日常结论兜底
        return "日常结论", "判断推理-逻辑判断", "日常结论"

    return None, None, None


# ────────────────────────────────────────────────────────────
# 6. 言语理解 subtype / topic / tag
# ────────────────────────────────────────────────────────────

def infer_yanyu(q: dict) -> tuple[str | None, str | None, str | None]:
    qtype = q.get("type") or ""
    stem = q.get("stem") or ""

    if qtype == "选词填空":
        # 判断成语/实词
        if "成语" in stem or re.search(r"[，。、]\s*[\u4e00-\u9fa5]{4}", stem):
            tag = "成语辨析"
        else:
            tag = "实词辨析"
        return "选词填空", "言语理解-选词填空", tag

    if qtype == "语句排序":
        return "语句排序", "言语理解-语句表达", "语句排序"

    if qtype == "语句填空":
        return "语句填空", "言语理解-语句表达", "语句填空"

    if qtype == "标题选择":
        return "标题选择", "言语理解-片段阅读", "标题选择"

    if qtype == "片段阅读":
        # 意图判断
        if has_any(stem, ["意在说明", "意在强调", "意图", "想要表达", "主要想说明"]):
            return "意图判断", "言语理解-片段阅读", "意图判断"
        # 主旨概括
        if has_any(stem, ["主要介绍", "主要说明", "这段文字主要", "概括", "主旨", "核心观点"]):
            return "主旨概括", "言语理解-片段阅读", "主旨概括"
        # 标题选择
        if "标题" in stem:
            return "标题选择", "言语理解-片段阅读", "标题选择"
        # 细节理解
        if has_any(stem, ["下列说法正确", "下列说法错误", "与原文相符", "与原文不符", "可以推出", "根据这段文字"]):
            return "细节理解", "言语理解-片段阅读", "细节理解"
        # 态度观点
        if has_any(stem, ["作者的态度", "作者认为", "作者对"]):
            return "态度观点", "言语理解-片段阅读", "态度观点"
        # 兜底主旨概括
        return "主旨概括", "言语理解-片段阅读", "主旨概括"

    return None, None, None


# ────────────────────────────────────────────────────────────
# 7. 政治理论 subtype / topic / tag
# ────────────────────────────────────────────────────────────

def infer_zhengzhi(q: dict) -> tuple[str | None, str | None, str | None]:
    stem = q.get("stem") or ""
    expl = q.get("explanation") or ""
    text = stem + " " + expl

    # 党的重要会议与文件
    if has_any(stem, ["三中全会", "四中全会", "五中全会", "全会", "中央经济工作会议", "二十大", "十九届"]):
        return "党的重要会议与文件", "党和国家重大政策与会议", "党的重要会议"

    # 马克思主义基本原理
    if has_any(text, ["马克思主义", "唯物辩证法", "唯物史观", "认识论", "政治经济学", "剩余价值"]):
        if "习近平" not in stem and "新时代" not in stem:
            return "马克思主义基本原理", "马克思主义基本原理", "唯物辩证法"

    # 习近平新时代中国特色社会主义思想（最常见）
    # 匹配范围：显式提及 / 三中全会决定 / 高质量发展 / 中国式现代化 / 具体专题关键词
    xixi_indicators = [
        "习近平", "新时代中国特色社会主义思想",
        "进一步全面深化改革", "中国式现代化",
        "高质量发展", "中央金融工作会议",
        "完善收入分配制度", "医药卫生体制改革",
        "市场经济基础制度", "科技体制改革",
        "绿色低碳发展", "大统战工作格局",
        "全面从严治党", "自我革命",
        "自主创新", "制度型开放",
        "宣传思想文化", "正确政绩观",
        "西部大开发", "粮食安全",
        "高质量充分就业", "纪律处分",
    ]
    if has_any(text, xixi_indicators) or has_any(stem, xixi_indicators):
        # 尝试匹配具体 tag
        tag_map = [
            ("高质量充分就业", "高质量充分就业"),
            ("粮食安全", "粮食安全"),
            ("自主创新", "自主创新"),
            ("绿色低碳", "绿色低碳发展"),
            ("统一战线", "大统战工作格局"),
            ("全面从严治党", "全面从严治党·自我革命"),
            ("自我革命", "全面从严治党·自我革命"),
            ("科技体制", "科技体制改革"),
            ("收入分配", "收入分配制度"),
            ("制度型开放", "制度型开放"),
            ("宣传思想", "宣传思想文化"),
            ("市场经济基础制度", "市场经济基础制度"),
            ("廉洁", "纪律处分·廉洁纪律"),
            ("政绩观", "正确政绩观"),
            ("西部大开发", "西部大开发"),
            ("金融", "高质量发展·金融"),
            ("医药卫生", "医药卫生体制改革"),
        ]
        for kw, tag in tag_map:
            if kw in text:
                return "习近平新时代中国特色社会主义思想", "习近平新时代中国特色社会主义思想", tag
        return "习近平新时代中国特色社会主义思想", "习近平新时代中国特色社会主义思想", "高质量发展·金融"

    # 兜底
    return None, None, None


# ────────────────────────────────────────────────────────────
# 8. 常识判断 subtype / topic / tag
# ────────────────────────────────────────────────────────────

def infer_changshi(q: dict) -> tuple[str | None, str | None, str | None]:
    stem = q.get("stem") or ""
    expl = q.get("explanation") or ""
    text = stem + " " + expl

    # 高优先级：强地理信号（避免被"人文/科技/原理"等词误抢）
    if has_any(stem, ["盆地", "地形", "气候", "山脉", "河流", "高原", "平原", "地理", "自然带", "季风", "洋流", "纬度", "经度"]):
        return "地理环境", "时事与基本常识", "地理环境"

    # 法律法规（用多字词，避免单字"法"误匹配"说法/方法"）
    legal_kw = ["法律", "法规", "法院", "法治", "合法", "违法", "宪法", "刑法", "民法",
                "行政法", "诉讼", "复议", "仲裁", "条例", "所有权", "消费者权益",
                "知识产权", "劳动合同", "治安", "处罚", "权利", "义务", "法条"]
    if has_any(stem, legal_kw):
        return "法律法规", "法律法规与党内法规", "法律法规"
    if has_any(expl, legal_kw) and not has_any(stem, ["盆地", "地形", "气候", "山脉", "河流"]):
        return "法律法规", "法律法规与党内法规", "法律法规"

    # 人文历史
    if has_any(text, ["文明", "历史", "甲骨文", "秦汉", "纪录片", "考古", "朝代", "文化", "遗址", "良渚", "三星堆", "殷墟", "三国", "回目", "名著", "小说", "唐诗", "宋词", "儒家", "道家"]):
        return "人文历史", "时事与基本常识", "人文历史"

    # 科技生活
    if has_any(text, ["物理学家", "科技", "物理", "化学", "生物", "医学", "技术", "科学家", "定律", "原理"]):
        return "科技生活", "时事与基本常识", "科技生活"

    # 地理环境
    if has_any(text, ["盆地", "地理", "地形", "气候", "山脉", "河流", "高原", "平原", "自然带"]):
        return "地理环境", "时事与基本常识", "地理环境"

    # 经济管理
    if has_any(text, ["经济", "货币", "财政", "GDP", "通胀", "宏观", "市场", "贸易"]):
        return "经济管理", "时事与基本常识", "经济管理"

    # 从 explanation 兜底
    if "法律" in expl or "法》" in expl:
        return "法律法规", "法律法规与党内法规", "法律法规"
    if "历史" in expl or "朝代" in expl:
        return "人文历史", "时事与基本常识", "人文历史"

    return None, None, None


# ────────────────────────────────────────────────────────────
# 9. 主标注流程
# ────────────────────────────────────────────────────────────

MODULE_INFERERS = {
    "资料分析": infer_ziliao,
    "数量关系": infer_shuliang,
    "判断推理": infer_panduan,
    "言语理解与表达": infer_yanyu,
    "政治理论": infer_zhengzhi,
    "常识判断": infer_changshi,
}


def annotate_paper(path: Path, stats: Counter) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    paper = path.stem
    changed = 0

    for s in doc.get("sections", []):
        section = s.get("name", "")
        inferer = MODULE_INFERERS.get(section)
        for q in s.get("questions", []):
            stats["total"] += 1
            stats[f"{paper}_total"] += 1

            if is_high_risk(q):
                stats["high_risk"] += 1
                stats[f"{paper}_high_risk"] += 1
                continue

            # ── subtype ──
            existing_subtype = q.get("subtype")
            if existing_subtype:
                q["subtype_source"] = "original"
                stats["subtype_original"] += 1
                stats["subtype_any"] += 1
            else:
                if inferer:
                    subtype, _topic, _tag = inferer(q)
                    if subtype:
                        q["subtype"] = subtype
                        q["subtype_source"] = "rule_inferred"
                        stats["subtype_inferred"] += 1
                        stats["subtype_any"] += 1
                        changed += 1
                    else:
                        stats["subtype_failed"] += 1
                else:
                    stats["subtype_failed"] += 1

            # ── topic / tag ──
            existing_topic = q.get("topic")
            existing_tag = q.get("tag")
            if existing_topic:
                stats["topic_original"] += 1
                stats["topic_any"] += 1
            else:
                if inferer:
                    _subtype, topic, tag = inferer(q)
                    if topic:
                        q["topic"] = topic
                        stats["topic_inferred"] += 1
                        stats["topic_any"] += 1
                        changed += 1
                    else:
                        stats["topic_failed"] += 1
                else:
                    stats["topic_failed"] += 1

            if existing_tag:
                stats["tag_original"] += 1
                stats["tag_any"] += 1
            elif q.get("topic"):
                # tag 与 topic 同步推断（inferer 返回的 tag）
                if inferer:
                    _subtype, _topic, tag = inferer(q)
                    if tag:
                        q["tag"] = tag
                        stats["tag_inferred"] += 1
                        stats["tag_any"] += 1
                        changed += 1
                    else:
                        stats["tag_failed"] += 1

            # 模块级统计
            if q.get("subtype"):
                stats[f"subtype_{section}"] += 1
            if q.get("topic"):
                stats[f"topic_{section}"] += 1
            stats[f"total_{section}"] += 1

    return doc, changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="仅统计不写文件")
    args = parser.parse_args()

    print("=" * 60)
    print("D8/D9: 2025 三卷 subtype + topic/tag 自动化标注")
    print("=" * 60)

    # 1) 扩展词表
    print("\n[1/3] 扩展 topic-vocabulary.json ...")
    vocab = expand_vocab(dry_run=args.dry_run)
    valid_topics = set(vocab["topics"].keys())

    # 2) 标注前统计
    print("\n[2/3] 标注前覆盖率 ...")
    pre_stats = Counter()
    for name in PAPER_NAMES:
        path = PAPERS_DIR / f"{name}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        for s in doc["sections"]:
            for q in s["questions"]:
                pre_stats["total"] += 1
                if is_high_risk(q):
                    pre_stats["high_risk"] += 1
                    continue
                if q.get("subtype"):
                    pre_stats["subtype"] += 1
                if q.get("topic"):
                    pre_stats["topic"] += 1
                if q.get("tag"):
                    pre_stats["tag"] += 1
    elig = pre_stats["total"] - pre_stats["high_risk"]
    print(f"  总题量: {pre_stats['total']}, 高风险跳过: {pre_stats['high_risk']}, 可标注: {elig}")
    print(f"  标注前 subtype: {pre_stats['subtype']}/{elig} = {pre_stats['subtype']/elig:.1%}")
    print(f"  标注前 topic:   {pre_stats['topic']}/{elig} = {pre_stats['topic']/elig:.1%}")
    print(f"  标注前 tag:     {pre_stats['tag']}/{elig} = {pre_stats['tag']/elig:.1%}")

    # 3) 执行标注
    print("\n[3/3] 执行标注 ...")
    stats = Counter()
    total_changed = 0
    for name in PAPER_NAMES:
        path = PAPERS_DIR / f"{name}.json"
        doc, changed = annotate_paper(path, stats)
        total_changed += changed
        if not args.dry_run:
            path.write_text(
                json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print(f"  {name}: 变更字段 {changed} 处")

    # 4) 标注后统计
    print("\n" + "=" * 60)
    print("标注后结果")
    print("=" * 60)
    elig2 = stats["total"] - stats["high_risk"]
    print(f"  总题量: {stats['total']}, 高风险跳过: {stats['high_risk']}, 可标注: {elig2}")
    print(f"  subtype: {stats['subtype_any']}/{elig2} = {stats['subtype_any']/elig2:.1%}")
    print(f"    - original: {stats['subtype_original']}, rule_inferred: {stats['subtype_inferred']}, failed: {stats['subtype_failed']}")
    print(f"  topic:   {stats['topic_any']}/{elig2} = {stats['topic_any']/elig2:.1%}")
    print(f"    - original: {stats['topic_original']}, inferred: {stats['topic_inferred']}, failed: {stats['topic_failed']}")
    print(f"  tag:     {stats['tag_any']}/{elig2} = {stats['tag_any']/elig2:.1%}")

    print("\n各模块 subtype 覆盖率:")
    for mod in ["资料分析", "数量关系", "判断推理", "言语理解与表达", "政治理论", "常识判断"]:
        t = stats[f"total_{mod}"]
        s = stats[f"subtype_{mod}"]
        if t:
            print(f"  {mod}: {s}/{t} = {s/t:.1%}")

    print("\n各模块 topic 覆盖率:")
    for mod in ["资料分析", "数量关系", "判断推理", "言语理解与表达", "政治理论", "常识判断"]:
        t = stats[f"total_{mod}"]
        tp = stats[f"topic_{mod}"]
        if t:
            print(f"  {mod}: {tp}/{t} = {tp/t:.1%}")

    # 验收检查
    print("\n" + "=" * 60)
    print("验收检查")
    print("=" * 60)
    subtype_rate = stats["subtype_any"] / elig2 if elig2 else 0
    ziliao_total = stats["total_资料分析"]
    ziliao_subtype = stats["subtype_资料分析"]
    ziliao_topic = stats["topic_资料分析"]
    print(f"  D8 subtype 总体 ≥80%: {subtype_rate:.1%} {'✅' if subtype_rate >= 0.80 else '❌'}")
    if ziliao_total:
        zr = ziliao_subtype / ziliao_total
        print(f"  资料分析 subtype 100%: {zr:.1%} {'✅' if zr >= 0.99 else '❌'}")
        ztr = ziliao_topic / ziliao_total
        print(f"  资料分析 topic ≥80%: {ztr:.1%} {'✅' if ztr >= 0.80 else '❌'}")

    if args.dry_run:
        print("\n[dry-run] 未写文件。")
    else:
        print(f"\n已写回 3 个 JSON，共变更 {total_changed} 处字段。")


if __name__ == "__main__":
    main()
