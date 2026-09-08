#!/usr/bin/env python3
"""
Q1 数据基线 — 2025 首批 50~100 题精标基准集构建脚本

从 2025 三卷真题中筛选有答案且无高风险 flag 的题目，
自动筛选 + 半自动精标（subtype/difficulty 规则推断，
knowledge_points/error_traps 从解析正则提取）。

用法:
    python3 scripts/xingce/build_benchmark.py
    python3 scripts/xingce/build_benchmark.py --dry-run   # 只统计不写文件
"""

import json
import re
import hashlib
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

# ── 路径 ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
PAPERS_DIR = REPO_ROOT / "xingce-structured-data" / "2025" / "xingce" / "papers"
OUTPUT_DIR = REPO_ROOT / "xingce-structured-data" / "2025" / "xingce" / "_extract" / "benchmark"

PAPER_FILES = {
    "shengji": PAPERS_DIR / "shengji.json",
    "shidi": PAPERS_DIR / "shidi.json",
    "xingzhengzhifa": PAPERS_DIR / "xingzhengzhifa.json",
}

PAPER_LABELS = {
    "shengji": "省级",
    "shidi": "市地",
    "xingzhengzhifa": "执法",
}

# ── 高风险 flags ──────────────────────────────────────
HIGH_RISK_FLAGS = {
    "content_mismatch_needs_source",
    "section_type_mismatch",
    "type_inferred_from_stem",
    "material_borrowed",
    "duplicate_in_paper",
}

# ── 已知解析错配题（题干与解析完全不对应，人工核验确认）──
# 格式: (paper_id, question_number)
KNOWN_EXPLANATION_MISMATCHES = {
    # 省级数量关系 Q66-75 系统性解析偏移（解析属于其他题目）
    ("shengji", 66), ("shengji", 67), ("shengji", 68),
    ("shengji", 69), ("shengji", 70), ("shengji", 71),
    ("shengji", 72), ("shengji", 73), ("shengji", 74),
    ("shengji", 75),
    # 执法卷独有题解析错配
    ("xingzhengzhifa", 68), # 夜跑问题，解析是稀树草原类比推理
    ("xingzhengzhifa", 71), # 长方体问题，解析是拔河实验逻辑判断
    # 省级判断推理 Q101/Q103/Q104 解析是会议安排分析推理
    ("shengji", 101), ("shengji", 103), ("shengji", 104),
    # 注：市地/执法卷 Q106/Q108/Q109 与上述省级题共享，去重后已排除
    # 省级 Q105 / 市地执法 Q110 题干本身就是会议安排，解析匹配，不排除
}

# ── 模块选题配额（总计约 70 题）──────────────────────
MODULE_QUOTAS = {
    "资料分析": 20,      # 全部来自执法卷（省级/市地 material_borrowed）
    "数量关系": 10,
    "判断推理": 12,
    "言语理解与表达": 12,
    "常识判断": 8,
    "政治理论": 8,
}
# 总计 = 20+10+12+12+8+8 = 70

# ── 题型关键词映射（用于 subtype 自动推断）────────────
SUBTYPE_RULES = {
    "资料分析": [
        (r"增长率|增长了|增速|增幅|同比增长|环比增长", "增长率计算"),
        (r"基期|上年同期|去年.*是|2019年.*2020", "基期量计算"),
        (r"比重|占.*的|占比", "比重计算"),
        (r"平均|人均|每.*平均", "平均数计算"),
        (r"倍数|是.*的多少倍|.*倍", "倍数计算"),
        (r"增长量|增加了.*家|增加量", "增长量计算"),
        (r"间隔|隔年|两年.*增长", "间隔增长率"),
        (r"混合|整体.*部分|增速.*介于", "混合增长率"),
        (r"比较|最大|最小|最高|最低|排序", "大小比较"),
        (r"饼状图|比例关系", "图形比例判断"),
        (r"之和|合计|总计|总和|相加", "简单计算"),
        (r"推出|能够.*推出|可以推出", "综合分析"),
    ],
    "数量关系": [
        (r"工程|工作量|效率|合作完成", "工程问题"),
        (r"行程|速度|距离|相遇|追及", "行程问题"),
        (r"利润|成本|售价|折扣|利润率", "经济利润问题"),
        (r"排列|组合|概率", "排列组合与概率"),
        (r"浓度|溶液|混合", "浓度问题"),
        (r"年龄|岁数", "年龄问题"),
        (r"容斥|都.*都不|至少", "容斥问题"),
        (r"几何|面积|体积|周长", "几何问题"),
        (r"最值|最多|最少|至少.*保证", "最值问题"),
        (r"周期|循环|星期", "周期问题"),
        (r"方程|设.*为|列方程", "方程法问题"),
        (r"货物|运输|载货|大车|小车", "和差倍比问题"),
        (r"部门|员工|人数.*比|分配.*人", "和差倍比问题"),
        (r"竞赛|得分|答题|答对|答错", "计数枚举问题"),
    ],
    "判断推理": [
        (r"定义|根据上述定义|下列属于|下列不属于", "定义判断"),
        (r"如果.*那么|只有.*才|除非|否则|充分条件|必要条件", "翻译推理"),
        (r"真假|谁说的|矛盾|反对", "真假推理"),
        (r"加强|支持|前提|假设|上述论证基于", "加强论证"),
        (r"削弱|质疑|反驳|反对", "削弱论证"),
        (r"图形|从所给.*图形|封闭区域|对称轴", "图形推理"),
        (r"类比|相当于|对于", "类比推理"),
        (r"排序|先后顺序|排列", "事件排序"),
        (r"分析推理|匹配|对应|安排", "分析推理"),
    ],
    "言语理解与表达": [
        (r"主旨|主要说明|主要讲述|概括|中心", "主旨概括"),
        (r"意在|意图|想要说明|启示", "意图判断"),
        (r"标题|最适合做本段文字标题", "标题填入"),
        (r"态度|观点|作者认为", "态度观点"),
        (r"细节|下列说法正确|下列说法错误|与原文相符", "细节理解"),
        (r"词句|划线|指代|文中.*指的是", "词句理解"),
        (r"排序|语句排序|依次填入", "语句排序"),
        (r"填空|填入划横线|____|________", "选词填空"),
        (r"接语|接下来|下文", "下文推断"),
    ],
    "常识判断": [
        (r"法律|宪法|民法|刑法|行政法|诉讼", "法律法规"),
        (r"党史|建国|建党|革命|长征", "党史国史"),
        (r"传统|文化|文学|诗词|成语|历史|王朝|朝代|秦汉|帝王|考古|文明", "人文历史"),
        (r"科技|科学|技术|物理|化学|生物|医学", "科技生活"),
        (r"地理|气候|地形|河流|山脉|资源", "地理环境"),
        (r"经济|金融|货币|财政|税收|市场", "经济管理"),
        (r"时事|时政|最新|近期", "时事政治"),
    ],
    "政治理论": [
        (r"习近平|总书记|重要讲话|重要文章", "习近平新时代中国特色社会主义思想"),
        (r"马克思主义|唯物|辩证法|认识论", "马克思主义基本原理"),
        (r"二十大|党代会|全会|中央", "党的重要会议与文件"),
        (r"中国式现代化|高质量发展|新发展|新质生产力", "中国式现代化与发展理念"),
        (r"党建|全面从严治党|党风|廉政", "党的建设"),
        (r"国家安全|总体国家安全观|国防|军队", "国家安全与国防"),
        (r"文化|自信|意识形态|价值观", "文化与意识形态"),
    ],
}

# ── 解题方法关键词 ────────────────────────────────────
SOLUTION_METHOD_RULES = [
    (r"公式|根据.*公式|代入公式", "公式法"),
    (r"估算|约|近似|大致", "估算法"),
    (r"代入|将.*代入|验证选项", "代入排除法"),
    (r"方程|设.*为|列方程|解方程", "方程法"),
    (r"赋值|设.*为1|特殊值", "赋值法"),
    (r"画图|画.*图|行程图|线段图", "画图法"),
    (r"枚举|列举|逐一", "枚举法"),
    (r"十字交叉|交叉法", "十字交叉法"),
    (r"尾数|尾数法", "尾数法"),
    (r"比例|份数", "比例法"),
    (r"逆向|反过来|倒推", "逆向思维法"),
    (r"定义要点|关键信息|符合定义", "定义要点法"),
    (r"翻译|逻辑表达式|推出", "翻译推理法"),
    (r"找主旨句|主题句|重点句", "主旨句法"),
    (r"关联词|转折|递进|因果", "关联词法"),
]

# ── 常见错误陷阱关键词 ────────────────────────────────
ERROR_TRAP_RULES = [
    (r"时间|年份|基期|现期|同比|环比", "时间点混淆/基期现期颠倒"),
    (r"单位|换算|万|亿|百分比|百分点", "单位换算/百分号混淆"),
    (r"范围|全国|全省|部分|整体", "范围扩大/缩小"),
    (r"增长|增长率|增长量", "增长率与增长量混淆"),
    (r"比重|占比|百分点", "比重与百分比混淆"),
    (r"平均|人均", "平均数基数错误"),
    (r"倍数|是.*倍|多.*倍", "是几倍与多几倍混淆"),
    (r"最大|最小|最高|最低", "极值方向错误"),
    (r"正确|错误|属于|不属于|符合|不符合", "选非题误选"),
    (r"偷换|概念|主体", "概念偷换/主体不一致"),
    (r"无中生有|未提及|原文没有", "无中生有"),
    (r"过度推断|引申|过度", "过度推断"),
    (r"以偏概全|部分.*整体", "以偏概全"),
    (r"因果|导致|因为", "因果倒置/强加因果"),
    (r"绝对|一定|必须|所有|全部", "绝对化表述"),
]

# ── 考点关键词（knowledge_points）─────────────────────
KNOWLEDGE_KEYWORDS = {
    "资料分析": [
        ("增长率", ["增长率", "增速", "增幅", "同比增长", "环比增长"]),
        ("基期量", ["基期", "上年", "去年"]),
        ("现期量", ["现期", "今年", "本年"]),
        ("增长量", ["增长量", "增加量", "增长了"]),
        ("比重", ["比重", "占比", "占.*的"]),
        ("平均数", ["平均", "人均", "每"]),
        ("倍数", ["倍数", "是.*倍"]),
        ("同比", ["同比"]),
        ("环比", ["环比"]),
        ("百分数与百分点", ["百分点", "百分比"]),
        ("直接查找", ["由图可知", "由表可知", "由材料可知"]),
        ("简单计算", ["计算", "合计", "总计"]),
    ],
    "数量关系": [
        ("工程问题", ["工程", "工作量", "效率"]),
        ("行程问题", ["行程", "速度", "相遇", "追及"]),
        ("经济利润", ["利润", "成本", "售价", "折扣"]),
        ("排列组合", ["排列", "组合", "选.*种"]),
        ("概率", ["概率", "可能性"]),
        ("方程法", ["设.*为", "列方程"]),
        ("代入排除", ["代入", "验证"]),
        ("赋值法", ["赋值", "设为1"]),
        ("和差倍比", ["倍", "比.*多", "比.*少"]),
    ],
    "判断推理": [
        ("定义判断", ["定义", "符合定义", "属于"]),
        ("翻译推理", ["如果", "那么", "只有", "才", "除非"]),
        ("加强论证", ["加强", "支持", "前提"]),
        ("削弱论证", ["削弱", "质疑", "反驳"]),
        ("图形推理-数量类", ["封闭区域", "数量", "交点", "线条"]),
        ("图形推理-属性类", ["对称", "曲直", "开闭"]),
        ("图形推理-位置类", ["旋转", "翻转", "平移"]),
        ("类比推理", ["相当于", "对于"]),
    ],
    "言语理解与表达": [
        ("主旨概括", ["主旨", "主要", "概括", "中心"]),
        ("意图判断", ["意在", "意图", "启示"]),
        ("细节理解", ["细节", "正确", "错误", "相符"]),
        ("选词填空", ["填空", "填入", "横线"]),
        ("语句排序", ["排序", "顺序"]),
        ("标题填入", ["标题"]),
        ("下文推断", ["接下来", "下文"]),
    ],
    "常识判断": [
        ("法律常识", ["法律", "宪法", "民法", "刑法"]),
        ("历史人文", ["历史", "文化", "文学", "传统"]),
        ("科技常识", ["科技", "科学", "技术", "物理", "化学"]),
        ("地理常识", ["地理", "气候", "地形"]),
        ("经济常识", ["经济", "金融", "货币"]),
    ],
    "政治理论": [
        ("习近平新时代中国特色社会主义思想", ["习近平", "总书记"]),
        ("马克思主义基本原理", ["马克思主义", "唯物", "辩证"]),
        ("党的重要会议", ["二十大", "全会", "中央"]),
        ("中国式现代化", ["中国式现代化", "高质量发展"]),
        ("党的建设", ["党建", "从严治党"]),
    ],
}


def load_papers():
    """加载三卷真题数据"""
    papers = {}
    for pid, path in PAPER_FILES.items():
        with open(path, encoding="utf-8") as f:
            papers[pid] = json.load(f)
    return papers


def question_fingerprint(q):
    """生成题目指纹用于去重（基于题干前80字符 + 选项）"""
    stem = (q.get("stem") or "")[:80].strip()
    opts = q.get("options")
    opt_str = ""
    if isinstance(opts, dict):
        opt_str = "|".join(str(opts.get(k, ""))[:30] for k in "ABCD")
    raw = f"{stem}::{opt_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def passes_filter(q, paper_id=None):
    """检查题目是否通过筛选标准"""
    # 1. answer 非空
    if not q.get("answer"):
        return False, "no_answer"
    # 2. 无高风险 flag
    flags = set(q.get("flags") or [])
    if flags & HIGH_RISK_FLAGS:
        return False, f"high_risk:{','.join(flags & HIGH_RISK_FLAGS)}"
    # 3. stem 非空且 > 10 字符
    stem = q.get("stem") or ""
    if len(stem) <= 10:
        return False, "stem_too_short"
    # 4. options 为 dict 且含 A/B/C/D
    opts = q.get("options")
    if not isinstance(opts, dict) or not all(k in opts for k in "ABCD"):
        return False, "options_invalid"
    # 5. 已知解析错配题排除
    if paper_id and (paper_id, q.get("number")) in KNOWN_EXPLANATION_MISMATCHES:
        return False, "known_explanation_mismatch"
    # 6. 数量关系题解析必须含数学内容（排除解析错配）
    if q.get("section") == "数量关系":
        expl = str(q.get("explanation") or "")
        if not re.search(r"[\d=+\-×÷/％%]", expl):
            return False, "quantity_no_math_in_explanation"
    return True, "ok"


def collect_candidates(papers):
    """收集所有通过筛选的候选题，去重（共享题以省级为准）"""
    # 按优先级处理：省级 > 市地 > 执法
    priority = ["shengji", "shidi", "xingzhengzhifa"]
    seen_fps = set()
    candidates = []  # (paper_id, question, fingerprint)

    for pid in priority:
        data = papers[pid]
        for sec in data.get("sections", []):
            for q in sec.get("questions", []):
                ok, reason = passes_filter(q, pid)
                if not ok:
                    continue
                fp = question_fingerprint(q)
                if fp in seen_fps:
                    continue
                seen_fps.add(fp)
                candidates.append((pid, q, fp))

    return candidates


def infer_subtype(q, module):
    """从题干和解析推断细题型（优先题干设问）"""
    stem = q.get("stem") or ""
    expl = str(q.get("explanation") or "")
    rules = SUBTYPE_RULES.get(module, [])

    # 优先从题干推断（反映题目真正设问）
    for pattern, subtype in rules:
        if re.search(pattern, stem):
            return subtype

    # 题干未命中时，从题干+解析推断
    text = stem + " " + expl
    for pattern, subtype in rules:
        if re.search(pattern, text):
            return subtype

    # 兜底：用 type 字段
    if q.get("type"):
        return q["type"]
    return f"{module}-其他"


def infer_difficulty(q, module):
    """
    推断难度 1-5：
    1=简单直接套公式/直接查找
    2=较简单一步计算
    3=中等需两步/多条件
    4=较复杂多步/陷阱
    5=复杂多步综合/强陷阱
    """
    stem = q.get("stem") or ""
    expl = str(q.get("explanation")) or ""
    text = stem + " " + expl

    # 直接查找类（资料分析"由图可知""由表可知"后直接读数）
    if module == "资料分析":
        if re.search(r"由[图表格材料]可知.*?[有是为共].*?[。\n]", expl) and not re.search(r"[=×÷+\-]", expl):
            return 1
        # 含公式且一步计算
        calc_count = len(re.findall(r"[=×÷+\-]", expl))
        if calc_count <= 3:
            return 2
        if calc_count <= 6:
            return 3
        if calc_count <= 10:
            return 4
        return 5

    if module == "数量关系":
        # 方程法一步
        if re.search(r"设.*?为.*?[，,].*?则", expl) and len(re.findall(r"[=×÷+\-]", expl)) <= 5:
            return 2
        if len(re.findall(r"[=×÷+\-]", expl)) <= 4:
            return 2
        if len(re.findall(r"[=×÷+\-]", expl)) <= 8:
            return 3
        if len(re.findall(r"[=×÷+\-]", expl)) <= 14:
            return 4
        return 5

    if module == "判断推理":
        # 定义判断通常较易
        if "定义" in (q.get("type") or "") or re.search(r"根据上述定义", stem):
            return 2
        # 翻译推理
        if re.search(r"如果.*那么|只有.*才|除非", stem):
            return 3
        # 加强削弱
        if re.search(r"加强|削弱|支持|质疑", stem):
            return 3
        return 3

    if module == "言语理解与表达":
        if "填空" in (q.get("type") or "") or re.search(r"填入|横线|____", stem):
            return 2
        if re.search(r"主旨|主要|概括", stem):
            return 2
        if re.search(r"细节|正确|错误|相符", stem):
            return 3
        if re.search(r"排序", stem):
            return 3
        return 2

    if module == "常识判断":
        return 2  # 常识通常知道就会，不知道就蒙

    if module == "政治理论":
        # 组合选择题（①②③④）通常较难
        if re.search(r"[①②③④⑤⑥]", stem):
            return 3
        return 2

    return 3


def infer_solution_method(q, module):
    """推断解题方法（按模块适配）"""
    text = (q.get("stem") or "") + " " + (str(q.get("explanation")) or "")

    # 数学类模块方法
    if module in ("资料分析", "数量关系"):
        MATH_METHODS = [
            (r"公式|根据.*公式|代入公式", "公式法"),
            (r"估算|约|近似|大致", "估算法"),
            (r"代入|将.*代入|验证选项", "代入排除法"),
            (r"方程|设.*为|列方程|解方程", "方程法"),
            (r"赋值|设.*为1|特殊值", "赋值法"),
            (r"画图|画.*图|行程图|线段图", "画图法"),
            (r"枚举|列举|逐一|树状图", "枚举法"),
            (r"十字交叉|交叉法", "十字交叉法"),
            (r"尾数|尾数法", "尾数法"),
            (r"比例|份数", "比例法"),
            (r"逆向|反过来|倒推", "逆向思维法"),
        ]
        for pattern, method in MATH_METHODS:
            if re.search(pattern, text):
                return method
        return "公式法"

    # 判断推理方法
    if module == "判断推理":
        LOGIC_METHODS = [
            (r"定义要点|关键信息|符合定义", "定义要点法"),
            (r"翻译|逻辑表达式|推出|充分条件|必要条件", "翻译推理法"),
            (r"加强|支持|前提|假设", "加强论证法"),
            (r"削弱|质疑|反驳", "削弱论证法"),
            (r"代入|排除", "代入排除法"),
            (r"画图|列表|连线", "图表法"),
        ]
        for pattern, method in LOGIC_METHODS:
            if re.search(pattern, text):
                return method
        return "逻辑推理法"

    # 言语理解方法
    if module == "言语理解与表达":
        VERBAL_METHODS = [
            (r"找主旨句|主题句|重点句|中心句", "主旨句法"),
            (r"关联词|转折|递进|因果|并列", "关联词法"),
            (r"语境|上下文|前后文", "语境分析法"),
            (r"搭配|固定搭配", "搭配判断法"),
            (r"感情色彩|褒义|贬义", "感情色彩法"),
        ]
        for pattern, method in VERBAL_METHODS:
            if re.search(pattern, text):
                return method
        return "语境分析法"

    # 常识/政治理论方法
    return "知识判断法"


def extract_knowledge_points(q, module):
    """从题干和解析提取考点标签"""
    text = (q.get("stem") or "") + " " + (str(q.get("explanation")) or "")
    points = []
    for point, keywords in KNOWLEDGE_KEYWORDS.get(module, []):
        for kw in keywords:
            if re.search(kw, text):
                points.append(point)
                break
    if not points:
        points = [module]
    return points[:4]  # 最多4个考点


def extract_error_traps(q, module):
    """从解析中提取常见错误陷阱（按模块适配）"""
    text = (q.get("stem") or "") + " " + (str(q.get("explanation")) or "")
    traps = []

    # 数学类模块专用陷阱
    if module in ("资料分析", "数量关系"):
        MATH_TRAPS = [
            (r"时间|年份|基期|现期|同比|环比", "时间点混淆/基期现期颠倒"),
            (r"单位|换算|万|亿|百分比|百分点", "单位换算/百分号混淆"),
            (r"范围|全国|全省|部分|整体", "范围扩大/缩小"),
            (r"增长|增长率|增长量", "增长率与增长量混淆"),
            (r"比重|占比|百分点", "比重与百分比混淆"),
            (r"平均|人均", "平均数基数错误"),
            (r"倍数|是.*倍|多.*倍", "是几倍与多几倍混淆"),
            (r"最大|最小|最高|最低", "极值方向错误"),
        ]
        for pattern, trap in MATH_TRAPS:
            if re.search(pattern, text):
                traps.append(trap)

    # 通用陷阱（所有模块）
    GENERAL_TRAPS = [
        (r"正确|错误|属于|不属于|符合|不符合", "选非题误选"),
        (r"偷换|概念|主体", "概念偷换/主体不一致"),
        (r"无中生有|未提及|原文没有", "无中生有"),
        (r"过度推断|引申|过度", "过度推断"),
        (r"以偏概全|部分.*整体", "以偏概全"),
        (r"因果|导致|因为", "因果倒置/强加因果"),
        (r"绝对|一定|必须|所有|全部", "绝对化表述"),
        (r"无关|没有关系|不相关", "无关选项"),
        (r"不能推出|无法推出|不能确定", "条件不足/无法推出"),
    ]
    for pattern, trap in GENERAL_TRAPS:
        if re.search(pattern, text):
            traps.append(trap)

    # 去重保序
    seen = set()
    unique = []
    for t in traps:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:3]  # 最多3个陷阱


def build_calc_tree(q, module):
    """
    为资料分析/数量关系题构建计算步骤树。
    从解析中提取计算表达式，结构化每步。
    """
    if module not in ("资料分析", "数量关系"):
        return None

    expl = str(q.get("explanation") or "")
    steps = []
    seen_exprs = set()

    def add_step(operation, inputs, result):
        key = f"{operation}={result}"
        if key in seen_exprs:
            return
        seen_exprs.add(key)
        steps.append({
            "operation": operation,
            "inputs": inputs,
            "result": result,
        })

    # 模式1: 带括号的复杂表达式，如 (39+198+229+282+134)×5%=44.1
    paren_pattern = re.compile(
        r"\(([^)]+)\)\s*([×÷*/])\s*([\d\.\,]+%?)\s*=\s*([\d\.\,]+%?)"
    )
    for m in paren_pattern.finditer(expl):
        inner = m.group(1).strip()
        op = m.group(2)
        factor = m.group(3).strip()
        result = m.group(4).strip()
        add_step(f"({inner}){op}{factor}", [inner, factor], result)

    # 模式2: 方括号嵌套表达式，如 [1.84/(1+12.6%)×(56.6%-4.9%)]
    bracket_pattern = re.compile(
        r"\[([^\]]+)\]"
    )
    for m in bracket_pattern.finditer(expl):
        expr = m.group(1).strip()
        if re.search(r"[+\-×÷*/%]", expr):
            # 拆分子步骤
            sub_parts = re.split(r"\s*([×÷*/])\s*", expr)
            sub_inputs = []
            for i, part in enumerate(sub_parts):
                if i % 2 == 0:  # operand
                    sub_inputs.append(part.strip())
            add_step(expr, sub_inputs, "见解析")

    # 模式2b: 数字-括号表达式，如 200-(60+60)=80
    num_paren_pattern = re.compile(
        r"([\d\.\,]+)\s*-\s*\(([^)]+)\)\s*=\s*([\d\.\,]+)"
    )
    for m in num_paren_pattern.finditer(expl):
        num = m.group(1).strip()
        inner = m.group(2).strip()
        result = m.group(3).strip()
        add_step(f"{num}-({inner})", [num, inner], result)

    # 模式2c: 变量表达式，如 y=0.2ax, 0.5ax-18a
    var_expr_pattern = re.compile(
        r"([a-zA-Z])\s*=\s*([\d\.]+\s*[a-zA-Z](?:\s*[+\-]\s*[\d\.]+\s*[a-zA-Z]+)*)"
    )
    for m in var_expr_pattern.finditer(expl):
        var = m.group(1)
        expr = m.group(2).strip()
        add_step(f"{var}={expr}", [expr], var)

    # 模式2d: 含变量的等式，如 60/v-3=60√3/(2√3v)
    var_eq_pattern = re.compile(
        r"([\d\.\,]+/[a-zA-Z]+[\-+\d\.]*)=\s*([\d\.\,√]+/[\(\)√\d\.\,a-zA-Z]+)"
    )
    for m in var_eq_pattern.finditer(expl):
        left = m.group(1).strip()
        right = m.group(2).strip()
        add_step(f"{left}={right}", [left, right], "解方程")

    # 模式3: 普通连续计算，如 39+198+229+282+134=882
    calc_pattern = re.compile(
        r"([\d\.\,]+\s*(?:[+\-×÷*/]\s*[\d\.\,]+)+)\s*=\s*([\d\.\,]+%?)"
    )
    for m in calc_pattern.finditer(expl):
        expr = m.group(1).strip()
        result = m.group(2).strip()
        parts = re.split(r"\s*([+\-×÷*/])\s*", expr)
        operands = [p.strip() for p in parts[::2] if p.strip()]
        add_step(expr, operands, result)

    # 模式4: 简单除法/乘法，如 3537/300=11.X 或 882×5%=44.1
    simple_pattern = re.compile(
        r"([\d\.\,]+)\s*([/÷×*])\s*([\d\.\,]+%?)\s*[≈=]?\s*([\d\.\,]+%?|[A-D])"
    )
    for m in simple_pattern.finditer(expl):
        a, op, b, r = m.group(1), m.group(2), m.group(3), m.group(4)
        add_step(f"{a}{op}{b}", [a, b], r)

    # 模式5: 比重/平均数公式描述，如 "比重=部分值/整体值"
    formula_pattern = re.compile(
        r'"([^"]*?=[^"]*?)"'
    )
    for m in formula_pattern.finditer(expl):
        formula = m.group(1).strip()
        if "=" in formula and len(formula) < 40:
            add_step(formula, [formula.split("=")[0].strip()], formula.split("=", 1)[1].strip())

    # 模式6: 文字描述的计算步骤，如 "所求为3537/300"
    text_calc = re.findall(
        r"所求为\s*([\d\.\,]+\s*[+\-×÷*/]\s*[\d\.\,]+(?:\s*[+\-×÷*/]\s*[\d\.\,]+)*)",
        expl
    )
    for expr in text_calc:
        parts = re.split(r"\s*([+\-×÷*/])\s*", expr)
        operands = [p.strip() for p in parts[::2] if p.strip()]
        add_step(expr, operands, "见解析")

    return steps if steps else None


def assess_quality_score(q, module):
    """
    数据质量分 1-5：
    题干完整度、选项规范性、解析详尽度
    """
    score = 5
    stem = q.get("stem") or ""
    expl = str(q.get("explanation") or "")
    opts = q.get("options") or {}

    # 题干长度
    if len(stem) < 20:
        score -= 1
    # 解析长度
    if len(expl) < 50:
        score -= 1
    elif len(expl) < 100:
        score -= 0.5
    # 选项规范性
    opt_lengths = [len(str(opts.get(k, ""))) for k in "ABCD"]
    if max(opt_lengths) == 0:
        score -= 2
    # 图形题缺图
    if q.get("options_in_media") or (module == "判断推理" and "图形" in (q.get("type") or "")):
        score -= 1
    # anchor_pending 不影响质量分（仅解析册格式）

    return max(1, min(5, int(round(score))))


def annotate_question(q, paper_id, fp, seq_num):
    """对单道题进行完整精标"""
    module = q.get("section", "未知")
    paper_label = PAPER_LABELS.get(paper_id, paper_id)
    qnum = q.get("number", 0)

    benchmark_id = f"BM2025-{paper_id}-{qnum:03d}"

    annotated = dict(q)  # 复制原题所有字段
    annotated["benchmark_id"] = benchmark_id
    annotated["module"] = module
    annotated["subtype"] = infer_subtype(q, module)
    annotated["knowledge_points"] = extract_knowledge_points(q, module)
    annotated["difficulty"] = infer_difficulty(q, module)
    annotated["solution_method"] = infer_solution_method(q, module)
    annotated["error_traps"] = extract_error_traps(q, module)
    annotated["calc_tree"] = build_calc_tree(q, module)
    annotated["quality_score"] = assess_quality_score(q, module)
    annotated["source_paper"] = paper_label
    annotated["source_paper_id"] = paper_id
    annotated["source_number"] = qnum
    annotated["fingerprint"] = fp

    return annotated


def select_questions(candidates):
    """
    按模块配额选题。
    策略：每个模块内按题目质量分排序，优先选高质量题；
    资料分析全部来自执法卷（其他卷 material_borrowed）。
    """
    by_module = defaultdict(list)
    for pid, q, fp in candidates:
        module = q.get("section", "未知")
        by_module[module].append((pid, q, fp))

    selected = []
    selection_log = {}

    for module, quota in MODULE_QUOTAS.items():
        pool = by_module.get(module, [])
        # 按质量分排序（质量分由题干/解析长度等决定）
        def quality_key(item):
            pid, q, fp = item
            stem_len = len(q.get("stem") or "")
            expl_len = len(str(q.get("explanation") or ""))
            return (stem_len + expl_len, q.get("number", 0))

        pool_sorted = sorted(pool, key=quality_key, reverse=True)
        chosen = pool_sorted[:quota]
        selected.extend(chosen)
        selection_log[module] = {
            "pool_size": len(pool),
            "selected": len(chosen),
            "quota": quota,
        }

    return selected, selection_log


def build_index_markdown(questions, selection_log):
    """生成精标清单 Markdown"""
    lines = []
    lines.append("# 2025 首批精标基准集 v1 — 选题清单")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 总题数：{len(questions)}")
    lines.append(f"> 来源：2025 国考三卷（省级/市地/行政执法）")
    lines.append("")

    # 模块分布表
    lines.append("## 一、模块分布")
    lines.append("")
    lines.append("| 模块 | 选题数 | 配额 | 候选池 |")
    lines.append("|------|--------|------|--------|")
    module_count = Counter(q["module"] for q in questions)
    for module in MODULE_QUOTAS:
        log = selection_log.get(module, {})
        lines.append(f"| {module} | {module_count.get(module, 0)} | {log.get('quota', '-')} | {log.get('pool_size', '-')} |")
    lines.append(f"| **合计** | **{len(questions)}** | **{sum(MODULE_QUOTAS.values())}** | |")
    lines.append("")

    # 来源卷分布
    lines.append("## 二、来源卷分布")
    lines.append("")
    paper_count = Counter(q["source_paper"] for q in questions)
    lines.append("| 来源卷 | 题数 | 占比 |")
    lines.append("|--------|------|------|")
    for paper in ["省级", "市地", "执法"]:
        cnt = paper_count.get(paper, 0)
        pct = f"{cnt/len(questions)*100:.1f}%" if questions else "0%"
        lines.append(f"| {paper} | {cnt} | {pct} |")
    lines.append("")

    # subtype 分布
    lines.append("## 三、细题型（subtype）分布")
    lines.append("")
    subtype_count = Counter(q["subtype"] for q in questions)
    lines.append("| 模块 | subtype | 题数 |")
    lines.append("|------|---------|------|")
    by_module_sub = defaultdict(Counter)
    for q in questions:
        by_module_sub[q["module"]][q["subtype"]] += 1
    for module in MODULE_QUOTAS:
        for subtype, cnt in by_module_sub[module].most_common():
            lines.append(f"| {module} | {subtype} | {cnt} |")
    lines.append("")

    # 难度分布
    lines.append("## 四、难度分布")
    lines.append("")
    diff_count = Counter(q["difficulty"] for q in questions)
    lines.append("| 难度 | 题数 | 占比 |")
    lines.append("|------|------|------|")
    for d in range(1, 6):
        cnt = diff_count.get(d, 0)
        pct = f"{cnt/len(questions)*100:.1f}%" if questions else "0%"
        lines.append(f"| {d} ({['简单','较易','中等','较难','复杂'][d-1]}) | {cnt} | {pct} |")
    lines.append("")

    # 资料分析 calc_tree 覆盖率
    zi_liao = [q for q in questions if q["module"] == "资料分析"]
    calc_count = sum(1 for q in zi_liao if q.get("calc_tree"))
    lines.append("## 五、资料分析 calc_tree 覆盖率")
    lines.append("")
    lines.append(f"- 资料分析题数：{len(zi_liao)}")
    lines.append(f"- 有 calc_tree：{calc_count}")
    lines.append(f"- 覆盖率：{calc_count/len(zi_liao)*100:.1f}%" if zi_liao else "- 覆盖率：N/A")
    lines.append("")

    # 逐题清单
    lines.append("## 六、逐题清单")
    lines.append("")
    lines.append("| benchmark_id | 模块 | subtype | 难度 | 来源 | 题号 | quality |")
    lines.append("|-------------|------|---------|------|------|------|---------|")
    for q in sorted(questions, key=lambda x: (x["module"], x["source_paper_id"], x["source_number"])):
        lines.append(
            f"| {q['benchmark_id']} | {q['module']} | {q['subtype']} | "
            f"{q['difficulty']} | {q['source_paper']} | {q['source_number']} | {q['quality_score']} |"
        )
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="构建 2025 精标基准集 v1")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写文件")
    args = parser.parse_args()

    print("=" * 60)
    print("Q1 数据基线 — 2025 首批精标基准集构建")
    print("=" * 60)

    # 1. 加载数据
    print("\n[1/5] 加载三卷真题...")
    papers = load_papers()
    for pid, data in papers.items():
        total = sum(len(s.get("questions", [])) for s in data.get("sections", []))
        print(f"  {PAPER_LABELS[pid]}: {total} 题")

    # 2. 筛选候选
    print("\n[2/5] 筛选候选题（去重 + 高风险排除）...")
    candidates = collect_candidates(papers)
    print(f"  通过筛选的去重候选题: {len(candidates)} 题")
    by_mod = Counter(q.get("section", "?") for _, q, _ in candidates)
    for mod in MODULE_QUOTAS:
        print(f"    {mod}: {by_mod.get(mod, 0)} 题候选")

    # 3. 按配额选题
    print("\n[3/5] 按模块配额选题...")
    selected, selection_log = select_questions(candidates)
    print(f"  选中: {len(selected)} 题")
    for mod, log in selection_log.items():
        print(f"    {mod}: {log['selected']}/{log['quota']} (候选池 {log['pool_size']})")

    # 4. 精标
    print("\n[4/5] 精标（subtype/difficulty/knowledge_points/calc_tree 等）...")
    annotated = []
    for i, (pid, q, fp) in enumerate(selected):
        ann = annotate_question(q, pid, fp, i + 1)
        annotated.append(ann)

    # 统计精标覆盖
    subtype_ok = sum(1 for q in annotated if q.get("subtype"))
    calc_ok = sum(1 for q in annotated if q["module"] in ("资料分析", "数量关系") and q.get("calc_tree"))
    calc_total = sum(1 for q in annotated if q["module"] in ("资料分析", "数量关系"))
    print(f"  subtype 覆盖率: {subtype_ok}/{len(annotated)} = {subtype_ok/len(annotated)*100:.1f}%")
    print(f"  calc_tree 覆盖率(资料+数量): {calc_ok}/{calc_total} = {calc_ok/calc_total*100:.1f}%" if calc_total else "")

    # 5. 输出
    if args.dry_run:
        print("\n[dry-run] 不写文件，完成。")
        return

    print("\n[5/5] 输出文件...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    benchmark = {
        "version": "v1",
        "created_at": datetime.now().isoformat(),
        "total": len(annotated),
        "selection_criteria": {
            "answer_non_empty": True,
            "exclude_high_risk_flags": sorted(HIGH_RISK_FLAGS),
            "anchor_pending_not_excluded": True,
            "stem_min_length": 10,
            "options_require_ABCD": True,
            "deduplication": "shared questions selected once, prefer 省级",
            "module_quotas": MODULE_QUOTAS,
        },
        "questions": annotated,
    }

    json_path = OUTPUT_DIR / "benchmark_v1.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(benchmark, f, ensure_ascii=False, indent=2)
    print(f"  JSON: {json_path} ({json_path.stat().st_size} bytes)")

    # Markdown 清单
    md_path = OUTPUT_DIR / "benchmark_index.md"
    md_content = build_index_markdown(annotated, selection_log)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"  MD:   {md_path} ({md_path.stat().st_size} bytes)")

    # 验证
    print("\n--- 验证 ---")
    errors = []
    for q in annotated:
        if not q.get("answer"):
            errors.append(f"{q['benchmark_id']}: answer empty")
        flags = set(q.get("flags") or [])
        if flags & HIGH_RISK_FLAGS:
            errors.append(f"{q['benchmark_id']}: high risk flag {flags & HIGH_RISK_FLAGS}")
        if not q.get("subtype"):
            errors.append(f"{q['benchmark_id']}: subtype missing")
        if q["module"] == "资料分析" and not q.get("calc_tree"):
            errors.append(f"{q['benchmark_id']}: 资料分析 missing calc_tree")

    if errors:
        print(f"  发现 {len(errors)} 个问题:")
        for e in errors[:10]:
            print(f"    - {e}")
    else:
        print("  全部通过 ✓")

    print(f"\n完成！基准集共 {len(annotated)} 题。")


if __name__ == "__main__":
    main()
