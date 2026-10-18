"""服务端速算训练：管理发布规则、生成可校验题目并保存练习闭环数据。"""
from __future__ import annotations

import json
import random
from datetime import timedelta
from functools import cmp_to_key

from sqlalchemy.orm import Session

from app.models import ZiliaoQuickMethod, ZiliaoQuickMethodVersion, ZiliaoQuickSession, gen_id
from app.schemas.ziliao import ZiliaoQuickMethodUpsert
from app.services.activity_service import record_event
from app.timezone import now

METHODS = [
    dict(code="fraction-compare", name="分数比较", category="比较", scene="比较两个分数的大小；题目按分子分母关系生成，解析推荐更快的比较方法。", knowledgePath="资料分析 / 快速比较方法", nodeTitle="快速比较方法", nodeParent="资料分析", sortOrder=10),
    dict(code="growth-amount", name="增长量", category="计算", scene="已知现期量和增长率，计算增长量；解析按数据特征推荐速算方法。", knowledgePath="资料分析 / 增长 / 增长量（X）", nodeTitle="增长量（X）", nodeParent="增长", sortOrder=20),
    dict(code="growth-rate", name="增长率", category="计算", scene="已知现期量、基期量，求增长量占基期量的比例。", knowledgePath="资料分析 / 增长 / 增长率（R）", nodeTitle="增长率（R）", nodeParent="增长", sortOrder=30),
    dict(code="base", name="基期量", category="计算", scene="已知现期量和增长率，反推基期量。", knowledgePath="资料分析 / 增长 / 基期值（A）", nodeTitle="基期值（A）", nodeParent="增长", sortOrder=40),
    dict(code="share", name="比重与比重变化", category="计算", scene="练现期比重、基期比重及两期比重变化；作答后区分百分点与百分比。", knowledgePath="资料分析 / 比重 | 倍数 | 平均数（比值）", nodeTitle="比重 | 倍数 | 平均数（比值）", nodeParent="资料分析", sortOrder=50),
    dict(code="average", name="平均数", category="计算", scene="练单位量、平均数变化和平均数增速；优先辨清总量、份数及单位换算。", knowledgePath="资料分析 / 比重 | 倍数 | 平均数（比值）", nodeTitle="比重 | 倍数 | 平均数（比值）", nodeParent="资料分析", sortOrder=60),
    dict(code="multiple", name="倍数", category="计算", scene="区分“是几倍”和“多几倍”，并练不同时期的倍数比较。", knowledgePath="资料分析 / 比重 | 倍数 | 平均数（比值）", nodeTitle="比重 | 倍数 | 平均数（比值）", nodeParent="资料分析", sortOrder=70),
    dict(code="mixed-growth", name="混合增长率", category="计算", scene="根据组成部分的基期权重合成整体增速；平均增速不能直接作算术平均。", knowledgePath="资料分析 / 混合问题", nodeTitle="混合问题", nodeParent="资料分析", sortOrder=80),
    dict(code="interval-growth", name="隔年增长率", category="计算", scene="已知连续两年的同比增速，求末期相对隔年基期的累计增速。", knowledgePath="资料分析 / 隔年增长 / 隔年增长率", nodeTitle="隔年增长率", nodeParent="隔年增长", sortOrder=90),
    dict(code="period-growth", name="年均增长", category="计算", scene="分别训练年均复合增长率和年均增长量；年均复合增速按题目条件建议估算与选项代入。", knowledgePath="资料分析 / 年均增长", nodeTitle="年均增长", nodeParent="资料分析", sortOrder=100),
    dict(code="contribution", name="贡献率与拉动", category="计算", scene="分别计算部分增长量占整体增长量的贡献率，以及对整体增速的拉动百分点。", knowledgePath="资料分析 / 贡献率", nodeTitle="贡献率", nodeParent="资料分析", sortOrder=110),
]

LEGACY_COMPARE_CODES = {"direct", "difference", "position", "split"}
LEGACY_TO_CONCEPT = {code: "fraction-compare" for code in LEGACY_COMPARE_CODES}
# 已存在的扩展规则曾使用该路径，但知识框架 Markdown 的实际标题包含空格、竖线和“（比值）”。
# 仅对完全匹配这一旧默认值的记录做一次性修复，管理员自定义的路径不覆盖。
LEGACY_DEFAULT_KNOWLEDGE_PATHS = {
    "share": "资料分析 / 比重/倍数/平均数",
    "average": "资料分析 / 比重/倍数/平均数",
    "multiple": "资料分析 / 比重/倍数/平均数",
}
COMPARE_STRATEGIES = {
    "direct": ("分数性质", "分子更大且分母更小，直接判断大小关系。"),
    "difference": ("差分比较", "分子、分母同向增加且差值关系清楚，可比较差分数与原分数。"),
    "position": ("同位比较", "分子和分母跨过同一倍数界线的方向相反，可直接判断。"),
    "split": ("分母拆分", "两个正分数接近 1，可改比部分与剩余量。"),
}
FRACTION_FORMS = ("pair", "pair", "multi-extrema", "multi-sort")
CALCULATION_FORMS = ("calculation-correct", "calculation-incorrect")
CALCULATION_FORM_SEQUENCE = ("calculation", "calculation", "calculation-correct", "calculation", "calculation-incorrect")
FORM_LABELS = {
    "pair": "两个分数比较",
    "multi-extrema": "多个分数选最大/最小",
    "multi-sort": "多个分数排序",
    "calculation-correct": "计算辨析·选正确项",
    "calculation-incorrect": "计算辨析·选错误项",
    "calculation": "直接计算",
    "material-correct": "综合材料·选正确项",
    "material-incorrect": "综合材料·选错误项",
    "share-current": "现期比重",
    "share-base": "基期比重",
    "share-change": "两期比重差",
    "average-current": "单位平均数",
    "average-change": "平均数变化量",
    "average-growth": "平均数增长率",
    "multiple-current": "现期倍数",
    "multiple-base": "基期倍数",
    "multiple-excess": "多几倍辨析",
    "mixed-rate": "加权混合增长率",
    "interval-growth": "隔年增长率",
    "annual-growth": "年均增长率",
    "annual-amount": "年均增长量",
    "contribution-rate": "贡献率",
    "growth-pull": "拉动百分点",
}

EXTENDED_CODES = {"share", "average", "multiple", "mixed-growth", "interval-growth", "period-growth", "contribution"}
EXTENDED_FORMS = {
    "share": ("share-current", "share-base", "share-change"),
    "average": ("average-current", "average-change", "average-growth"),
    "multiple": ("multiple-current", "multiple-base", "multiple-excess"),
    "mixed-growth": ("mixed-rate",),
    "interval-growth": ("interval-growth",),
    "period-growth": ("annual-growth", "annual-amount"),
    "contribution": ("contribution-rate", "growth-pull"),
}


class UnusableQuickCalcSample(ValueError):
    """A sample cannot form four distinct, defensible options at supported precision."""


# 2023、2024 年国家统计局国民经济和社会发展统计公报中的真实金额。
# 直接成对使用两年公报数值，不从增速反推基期量；题目是按真实统计数据改编。
GROWTH_RATE_FACTS = [
    {"base": 417568, "current": 438468, "context": "全国货物进出口总额"},
    {"base": 237726, "current": 254545, "context": "全国货物出口额"},
    {"base": 179842, "current": 183923, "context": "全国货物进口额"},
    {"base": 139196, "current": 151246, "context": "全国机电产品出口金额"},
    {"base": 117042, "current": 114827, "context": "全国一般贸易进口金额"},
    {"base": 5929, "current": 5950, "context": "全国钢材出口金额"},
    {"base": 9454, "current": 10102, "context": "全国纺织纱线、织物及其制品出口金额"},
    {"base": 11206, "current": 11326, "context": "全国服装及衣着附件出口金额"},
    {"base": 3470, "current": 3336, "context": "全国鞋靴出口金额"},
    {"base": 4517, "current": 4830, "context": "全国家具及其零件出口金额"},
    {"base": 2512, "current": 2458, "context": "全国箱包及类似容器出口金额"},
    {"base": 2858, "current": 2837, "context": "全国玩具出口金额"},
    {"base": 7090, "current": 7549, "context": "全国塑料制品出口金额"},
    {"base": 9568, "current": 11352, "context": "全国集成电路出口金额"},
    {"base": 13187, "current": 14661, "context": "全国自动数据处理设备及其零部件出口金额"},
    {"base": 9797, "current": 9559, "context": "全国手机出口金额"},
    {"base": 581, "current": 1213, "context": "全国集装箱出口金额"},
    {"base": 1873, "current": 2066, "context": "全国液晶平板显示模组出口金额"},
    {"base": 7165, "current": 8347, "context": "全国汽车（包括底盘）出口金额"},
    {"base": 4199, "current": 3751, "context": "全国大豆进口金额"},
    {"base": 734, "current": 528, "context": "全国食用植物油进口金额"},
    {"base": 9418, "current": 9406, "context": "全国铁矿砂及其精矿进口金额"},
    {"base": 3723, "current": 3705, "context": "全国煤及褐煤进口金额"},
    {"base": 23733, "current": 23108, "context": "全国原油进口金额"},
    {"base": 1965, "current": 2083, "context": "全国成品油进口金额"},
    {"base": 4523, "current": 4637, "context": "全国天然气进口金额"},
    {"base": 3182, "current": 3117, "context": "全国初级形状的塑料进口金额"},
    {"base": 1665, "current": 1593, "context": "全国纸浆进口金额"},
    {"base": 891, "current": 819, "context": "全国钢材进口金额"},
    {"base": 3356, "current": 3848, "context": "全国未锻轧铜及铜材进口金额"},
    {"base": 24591, "current": 27445, "context": "全国集成电路进口金额"},
    {"base": 3321, "current": 2785, "context": "全国汽车（包括底盘）进口金额"},
]

# 有明确题源的真题数据，补足真实统计指标中较少出现的典型速算场景。
# 2019 年国考地市级第 121 题：2011 年二手车交易量 682 万辆，同比增长 12.4%。
GROWTH_AMOUNT_REFERENCE_FACTS = [
    {"base": 682 / 1.124, "current": 682, "rate": 12.4, "context": "二手车交易量",
     "period": "2011 年", "unit": "万辆", "sourceLabel": "2019 年国考地市级第 121 题"},
    {"base": 9654 / (1 - 0.051), "current": 9654, "rate": -5.1, "context": "慈善超市数量",
     "period": "2017 年", "unit": "个", "sourceLabel": "2017 年浙江省考 B 卷第 116 题"},
]

# 国家统计局 / 海关总署公布的同口径公开数据。训练题保留来源说明；不把派生题称为原题。
TRADE_CONCEPT_SOURCE = "国家统计局2023、2024年国民经济和社会发展统计公报（货物贸易数据来自海关总署）"
TRADE_CONCEPT_SOURCE_URLS = [
    "https://www.stats.gov.cn/sj/zxfb/202402/t20240228_1947915.html",
    "https://www.stats.gov.cn/zwfwck/sjfb/202502/t20250228_1958817.html",
]
TRADE_CONCEPT_FACTS = {
    2023: {"total": 417568, "export": 237726, "import": 179842},
    2024: {"total": 438468, "export": 254545, "import": 183923},
}
GRAIN_YIELD_SOURCE = "国家统计局2022、2023、2024年全国粮食产量公告"
GRAIN_PRODUCTION_SOURCE = "国家统计局2022—2024年全国粮食产量公告及公告附表"
PER_CAPITA_GDP_SOURCE = "国家统计局2022、2023、2024年国民经济和社会发展统计公报公布的人均GDP"
PER_CAPITA_GDP_SOURCE_URLS = [
    "https://www.stats.gov.cn/sj/zxfb/202302/t20230228_1919011.html",
    "https://www.stats.gov.cn/sj/zxfb/202402/t20240228_1947915.html",
    "https://www.stats.gov.cn/zwfwck/sjfb/202502/t20250228_1958817.html",
]
PER_CAPITA_GDP_FACTS = {2022: 85698, 2023: 89358, 2024: 95749}  # 元/人，按公报公布值计算
GDP_COMPOSITION_SOURCE = "国家统计局2023年GDP最终核实数据与2024年国民经济和社会发展统计公报现价增加值"
GDP_COMPOSITION_SOURCE_URLS = [
    "https://www.stats.gov.cn/sj/zxfb/202412/t20241227_1957915.html",
    "https://www.stats.gov.cn/sj/zxfbhjd/202512/t20251226_1962144.html",
]
GDP_COMPOSITION_FACTS = {
    2023: {"total": 1294272, "primary": 89169, "secondary": 475936, "tertiary": 729167},
    2024: {"total": 1348066, "primary": 91636, "secondary": 490305, "tertiary": 766125},
}
GRAIN_YIELD_FACTS_BY_LABEL = {
    "全国粮食": {"value": 5921.1, "unit": "公斤/公顷"},
    "夏粮": {"value": 5632.2, "unit": "公斤/公顷"},
    "早稻": {"value": 5925.4, "unit": "公斤/公顷"},
    "秋粮": {"value": 6008.3, "unit": "公斤/公顷"},
    "谷物": {"value": 6493.1, "unit": "公斤/公顷"},
    "稻谷": {"value": 7154.7, "unit": "公斤/公顷"},
    "小麦": {"value": 5939.6, "unit": "公斤/公顷"},
    "玉米": {"value": 6591.7, "unit": "公斤/公顷"},
    "豆类": {"value": 1998.6, "unit": "公斤/公顷"},
    "薯类": {"value": 4344.8, "unit": "公斤/公顷"},
    "吉林省粮食": {"value": 7287.5, "unit": "公斤/公顷"},
    "黑龙江省粮食": {"value": 5423.4, "unit": "公斤/公顷"},
    "河南省粮食": {"value": 6234.8, "unit": "公斤/公顷"},
    "新疆维吾尔自治区粮食": {"value": 7872.4, "unit": "公斤/公顷"},
    "贵州省粮食": {"value": 4135.5, "unit": "公斤/公顷"},
}
GRAIN_YIELD_SOURCE_URLS = [
    "https://www.stats.gov.cn/xxgk/sjfb/zxfb2020/202212/t20221212_1890928.html",
    "https://www.stats.gov.cn/sj/zxfb/202312/t20231211_1945417.html",
    "https://www.stats.gov.cn/zwfwck/sjfb/202412/t20241213_1957744.html",
]
# 省级播种面积、产量和单产按国家统计局2022、2023、2024年公告表逐项录入。
# tuple: 地区、产量2022/23/24（万吨）、单产2022/23/24（公斤/公顷）。
GRAIN_PROVINCE_FACTS = [
    ("北京", 45.4, 47.8, 57.6, 5910.9, 5340.6, 6115.5), ("天津", 256.2, 255.7, 270.6, 6802.1, 6556.7, 6780.5),
    ("河北", 3865.1, 3809.9, 3908.8, 5998.1, 5902.1, 6050.6), ("山西", 1464.3, 1478.1, 1468.7, 4647.9, 4676.1, 4660.0),
    ("内蒙古", 3900.6, 3957.8, 4100.5, 5610.9, 5666.4, 5847.9), ("辽宁", 2484.5, 2563.4, 2500.3, 6976.1, 7163.5, 6989.1),
    ("吉林", 4080.8, 4186.5, 4266.0, 7053.9, 7186.4, 7287.5), ("黑龙江", 7763.1, 7788.2, 8001.7, 5287.1, 5282.6, 5423.4),
    ("上海", 95.6, 101.9, 98.3, 7782.1, 8010.1, 7542.6), ("江苏", 3769.1, 3797.7, 3810.1, 6922.9, 6956.8, 6958.4),
    ("浙江", 621.0, 638.8, 650.2, 6085.3, 6234.1, 6210.2), ("安徽", 4100.1, 4150.8, 4184.3, 5605.7, 5659.2, 5696.9),
    ("福建", 508.7, 511.0, 514.4, 6073.2, 6074.9, 6091.6), ("江西", 2151.9, 2198.3, 2196.0, 5698.4, 5824.4, 5818.0),
    ("山东", 5543.8, 5655.3, 5710.2, 6621.6, 6742.2, 6787.7), ("河南", 6789.4, 6624.3, 6719.4, 6299.1, 6142.0, 6234.8),
    ("湖北", 2741.1, 2777.0, 2785.3, 5846.0, 5899.9, 5897.9), ("湖南", 3018.0, 3068.0, 3078.1, 6333.0, 6440.7, 6448.4),
    ("广东", 1291.5, 1285.2, 1313.4, 5790.9, 5764.4, 5872.0), ("广西", 1393.1, 1395.4, 1403.8, 4924.0, 4922.4, 4939.7),
    ("海南", 146.6, 147.0, 142.4, 5368.9, 5373.8, 5222.1), ("重庆", 1072.8, 1095.9, 1100.7, 5241.8, 5409.3, 5417.2),
    ("四川", 3510.5, 3593.8, 3633.8, 5431.4, 5611.8, 5672.6), ("贵州", 1114.6, 1119.7, 1146.1, 3997.0, 4036.6, 4135.5),
    ("云南", 1958.0, 1974.0, 1993.5, 4649.7, 4652.1, 4694.0), ("西藏", 107.3, 108.9, 112.9, 5573.6, 5594.8, 5664.7),
    ("陕西", 1297.9, 1323.7, 1352.3, 4301.2, 4378.7, 4460.2), ("甘肃", 1265.0, 1272.9, 1296.1, 4685.5, 4695.4, 4772.3),
    ("青海", 107.3, 116.2, 118.3, 3534.8, 3812.0, 3866.2), ("宁夏", 375.8, 378.8, 385.9, 5428.8, 5459.1, 5559.2),
    ("新疆", 1813.5, 2119.2, 2330.2, 7451.0, 7502.1, 7872.4),
]
# Use the one-decimal values in the official detailed tables (the bulletin prose
# rounds 2024 to 70,650 万吨); keep the national series precision consistent.
GRAIN_NATIONAL_PRODUCTION = {2022: 68652.8, 2023: 69541.0, 2024: 70649.9}
GRAIN_SEASON_COMPONENTS_BY_YEAR = {
    2022: [("夏粮", 14740.3), ("早稻", 2812.3), ("秋粮", 51100.1)],
    2023: [("夏粮", 14615.2), ("早稻", 2833.7), ("秋粮", 52092.0)],
    2024: [("夏粮", 14989.0), ("早稻", 2817.4), ("秋粮", 52843.4)],
}
GRAIN_TYPE_COMPONENTS_BY_YEAR = {
    2022: [("谷物", 63324.3), ("豆类", 2351.0), ("薯类", 2977.4)],
    2023: [("谷物", 64143.0), ("豆类", 2384.1), ("薯类", 3013.9)],
    2024: [("谷物", 65228.7), ("豆类", 2362.8), ("薯类", 3058.4)],
}
TRADE_EXPORT_ITEMS = [
    fact for fact in GROWTH_RATE_FACTS
    if "出口" in fact["context"] and "进出口总额" not in fact["context"]
    and fact["context"] != "全国货物出口额"
]
TRADE_IMPORT_ITEMS = [
    fact for fact in GROWTH_RATE_FACTS
    if "进口" in fact["context"] and "进出口总额" not in fact["context"]
    and fact["context"] != "全国货物进口额"
]


def _trade_source() -> dict:
    return {"kind": "trade", "baseYear": 2023, "currentYear": 2024,
            "base": TRADE_CONCEPT_FACTS[2023], "current": TRADE_CONCEPT_FACTS[2024],
            "sourceLabel": TRADE_CONCEPT_SOURCE, "sourceUrls": TRADE_CONCEPT_SOURCE_URLS}


def _cycle_choice(items: list[dict], config: dict, rng: random.Random) -> dict:
    if not items:
        raise ValueError("没有可用的真实统计样本")
    source_index = config.get("_sourceIndex")
    if source_index is not None:
        return items[int(source_index) % len(items)]
    return rng.choice(items)


def _grain_province_label(name: str) -> str:
    special = {
        "北京": "北京市", "天津": "天津市", "上海": "上海市", "重庆": "重庆市",
        "内蒙古": "内蒙古自治区", "广西": "广西壮族自治区", "西藏": "西藏自治区",
        "宁夏": "宁夏回族自治区", "新疆": "新疆维吾尔自治区",
    }
    region = special.get(name, f"{name}省")
    return f"{region}粮食"


def _grain_yield_series() -> list[dict]:
    rows = [{"label": "全国粮食", "unit": "公斤/公顷", "values": {2022: 5801.7, 2023: 5845.3, 2024: 5921.1}}]
    rows.extend({"label": _grain_province_label(name), "unit": "公斤/公顷",
                 "values": {2022: y22, 2023: y23, 2024: y24}}
                for name, _, _, _, y22, y23, y24 in GRAIN_PROVINCE_FACTS)
    return rows


def _official_grain_growth_facts() -> list[dict]:
    """Convert the official production/yield time series into real two-period facts."""
    year_pairs = ((2022, 2023), (2023, 2024))
    production_series = [
        {"label": "全国粮食产量", "unit": "万吨", "values": GRAIN_NATIONAL_PRODUCTION},
        *[{"label": f"{_grain_province_label(name)}产量", "unit": "万吨",
           "values": {2022: p22, 2023: p23, 2024: p24}}
          for name, p22, p23, p24, *_ in GRAIN_PROVINCE_FACTS],
    ]
    yield_series = [{**item, "label": f"{item['label']}单产"} for item in _grain_yield_series()]
    facts = []
    for series, source_label in ((production_series, GRAIN_PRODUCTION_SOURCE),
                                 (yield_series, GRAIN_YIELD_SOURCE)):
        for item in series:
            for base_year, current_year in year_pairs:
                base, current = item["values"][base_year], item["values"][current_year]
                facts.append({
                    "base": base, "current": current,
                    "rate": (current - base) / base * 100,
                    "context": item["label"], "period": f"{base_year}—{current_year}年",
                    "unit": item["unit"], "baseYear": base_year, "currentYear": current_year,
                    "sourceLabel": source_label, "sourceUrls": GRAIN_YIELD_SOURCE_URLS,
                })
    return facts


def _official_trade_growth_facts() -> list[dict]:
    return [{
        **fact, "rate": (fact["current"] - fact["base"]) / fact["base"] * 100,
        "period": "2023—2024年", "unit": "亿元", "baseYear": 2023, "currentYear": 2024,
        "sourceLabel": TRADE_CONCEPT_SOURCE, "sourceUrls": TRADE_CONCEPT_SOURCE_URLS,
    } for fact in GROWTH_RATE_FACTS]


def _grain_yield_period_sources() -> list[dict]:
    series = _grain_yield_series()
    periods = [(2022, 2023), (2023, 2024), (2022, 2024)]
    sources = []
    for item in series:
        for start_year, end_year in periods:
            sources.append({"kind": "grain-yield-period", "label": item["label"],
                            "startYear": start_year, "endYear": end_year,
                            "startValue": item["values"][start_year], "endValue": item["values"][end_year],
                            "periods": end_year - start_year, "unit": item["unit"],
                            "sourceLabel": GRAIN_YIELD_SOURCE, "sourceUrls": GRAIN_YIELD_SOURCE_URLS})
    return sources


def _published_period_sources() -> list[dict]:
    sources = _grain_yield_period_sources()
    for start_year, end_year in ((2022, 2023), (2023, 2024), (2022, 2024)):
        sources.append({"kind": "per-capita-gdp", "label": "全国人均GDP", "unit": "元/人",
                        "startYear": start_year, "endYear": end_year,
                        "startValue": PER_CAPITA_GDP_FACTS[start_year],
                        "endValue": PER_CAPITA_GDP_FACTS[end_year], "periods": end_year - start_year,
                        "sourceLabel": PER_CAPITA_GDP_SOURCE, "sourceUrls": PER_CAPITA_GDP_SOURCE_URLS})
    return sources


def _interval_growth_sources() -> list[dict]:
    """Build true隔年题: consecutive annual rates compose across the 2022→2024 interval."""
    series = [{"label": "全国粮食产量", "unit": "万吨", "values": GRAIN_NATIONAL_PRODUCTION}]
    series.extend({"label": f"{_grain_province_label(name)}产量", "unit": "万吨",
                   "values": {2022: p22, 2023: p23, 2024: p24}}
                  for name, p22, p23, p24, *_ in GRAIN_PROVINCE_FACTS)
    series.extend({**item, "label": f"{item['label']}单产"} for item in _grain_yield_series())
    result = []
    for item in series:
        start, middle, end = (item["values"][year] for year in (2022, 2023, 2024))
        first_rate = (middle / start - 1) * 100
        second_rate = (end / middle - 1) * 100
        target = ((1 + first_rate / 100) * (1 + second_rate / 100) - 1) * 100
        potential = [target, first_rate + second_rate,
                     first_rate + second_rate - first_rate * second_rate / 100,
                     -target, first_rate * second_rate / 100]
        if not any(len({round(value, precision) for value in potential}) >= 4
                   for precision in (1, 2)):
            continue
        result.append({"kind": "interval-growth", "label": item["label"], "unit": item["unit"],
                       "startYear": 2022, "middleYear": 2023, "endYear": 2024,
                       "startValue": start, "middleValue": middle, "endValue": end,
                       "firstRate": first_rate, "secondRate": second_rate,
                       "sourceLabel": GRAIN_PRODUCTION_SOURCE if item["unit"] == "万吨" else GRAIN_YIELD_SOURCE,
                       "sourceUrls": GRAIN_YIELD_SOURCE_URLS})
    return result


def _grain_production_ratio_sources() -> list[dict]:
    sources = []
    for name, p22, p23, p24, *_ in GRAIN_PROVINCE_FACTS:
        for base_year, current_year in ((2022, 2023), (2023, 2024), (2022, 2024)):
            production = {2022: p22, 2023: p23, 2024: p24}
            sources.append({"kind": "published-ratio", "baseYear": base_year, "currentYear": current_year,
                            "numeratorLabel": "全国粮食总产量", "denominatorLabel": f"{name}粮食产量",
                            "baseNumerator": GRAIN_NATIONAL_PRODUCTION[base_year],
                            "currentNumerator": GRAIN_NATIONAL_PRODUCTION[current_year],
                            "baseDenominator": production[base_year], "currentDenominator": production[current_year],
                            "sourceLabel": GRAIN_YIELD_SOURCE, "sourceUrls": GRAIN_YIELD_SOURCE_URLS})
    return sources


def _mixed_growth_sources() -> list[dict]:
    sources = []
    for dataset_name, dataset, source_label, source_urls in (
        ("分季节粮食产量", GRAIN_SEASON_COMPONENTS_BY_YEAR, GRAIN_YIELD_SOURCE, GRAIN_YIELD_SOURCE_URLS),
        ("分品种粮食产量", GRAIN_TYPE_COMPONENTS_BY_YEAR, GRAIN_YIELD_SOURCE, GRAIN_YIELD_SOURCE_URLS),
    ):
        for base_year, current_year in ((2022, 2023), (2023, 2024), (2022, 2024)):
            base_items = dict(dataset[base_year])
            current_items = dict(dataset[current_year])
            labels = list(base_items)
            subsets = [(labels[i], labels[j]) for i in range(len(labels)) for j in range(i + 1, len(labels))]
            subsets.append(tuple(labels))
            for subset in subsets:
                components = [{"label": label, "base": base_items[label], "current": current_items[label]}
                              for label in subset]
                sources.append({"kind": "statistical-mix", "aggregateLabel": dataset_name,
                                "baseYear": base_year, "currentYear": current_year,
                                "components": components,
                                "baseTotal": sum(item["base"] for item in components),
                                "currentTotal": sum(item["current"] for item in components),
                                "measureUnit": "万吨", "sourceLabel": source_label,
                                "sourceUrls": source_urls, "priceBasis": "同口径粮食产量"})
    gdp = GDP_COMPOSITION_FACTS
    sectors = {"第一产业": "primary", "第二产业": "secondary", "第三产业": "tertiary"}
    labels = list(sectors)
    subsets = [(labels[i], labels[j]) for i in range(len(labels)) for j in range(i + 1, len(labels))]
    subsets.append(tuple(labels))
    for subset in subsets:
        components = [{"label": label, "base": gdp[2023][sectors[label]], "current": gdp[2024][sectors[label]]}
                      for label in subset]
        sources.append({"kind": "statistical-mix", "aggregateLabel": "国内生产总值产业分项（现价）",
                        "baseYear": 2023, "currentYear": 2024, "components": components,
                        "baseTotal": sum(item["base"] for item in components),
                        "currentTotal": sum(item["current"] for item in components),
                        "measureUnit": "亿元", "sourceLabel": GDP_COMPOSITION_SOURCE,
                        "sourceUrls": GDP_COMPOSITION_SOURCE_URLS, "priceBasis": "现价"})
    return sources


def _data_concept_question(code: str, config: dict, rng: random.Random) -> dict:
    """按正式统计数据生成概念训练题；题面不预告解法，答后给出推导。"""
    form = config.get("_questionForm") or rng.choice(EXTENDED_FORMS[code])
    candidates: list[float]
    source: dict
    precision = 1

    if code == "share":
        item = _cycle_choice(TRADE_EXPORT_ITEMS, config, rng)
        base_total, current_total = TRADE_CONCEPT_FACTS[2023]["export"], TRADE_CONCEPT_FACTS[2024]["export"]
        source = {
            "kind": "trade-export-share", "baseYear": 2023, "currentYear": 2024,
            "label": item["context"], "basePart": item["base"], "currentPart": item["current"],
            "baseTotal": base_total, "currentTotal": current_total,
            "totalLabel": "全国货物出口额", "unit": "亿元",
            "sourceLabel": TRADE_CONCEPT_SOURCE, "sourceUrls": TRADE_CONCEPT_SOURCE_URLS,
        }
        base_share = source["basePart"] / base_total * 100
        current_share = source["currentPart"] / current_total * 100
        if form == "share-current":
            target = current_share
            unit = "%"
            stem = f"2024年{source['label']}占全国货物出口额的比重约为多少？（保留一位小数）"
            latex = rf"\frac{{{source['currentPart']}}}{{{current_total}}}\times100\%"
            candidates = [base_share, 100 - current_share, source["currentPart"] / base_total * 100,
                          source["basePart"] / current_total * 100,
                          (source["currentPart"] - source["basePart"]) / source["basePart"] * 100]
            steps = [{"text": f"比重＝部分量÷整体量。两者均为2024年现价出口金额，单位相同；数据来源：{source['sourceLabel']}。",
                      "latex": rf"\frac{{{source['currentPart']}}}{{{current_total}}}\times100\%={target:.1f}\%"}]
        elif form == "share-base":
            target = base_share
            unit = "%"
            stem = f"2023年{source['label']}占全国货物出口额的比重约为多少？（保留一位小数）"
            latex = rf"\frac{{{source['basePart']}}}{{{base_total}}}\times100\%"
            candidates = [current_share, 100 - base_share, source["basePart"] / current_total * 100,
                          source["currentPart"] / base_total * 100,
                          (source["currentPart"] - source["basePart"]) / source["basePart"] * 100]
            steps = [{"text": f"基期比重用同一基期的部分量除以整体量；不要把现期部分量与基期整体量混用。数据来源：{source['sourceLabel']}。",
                      "latex": rf"\frac{{{source['basePart']}}}{{{base_total}}}\times100\%={target:.1f}\%"}]
        elif form == "share-change":
            target = current_share - base_share
            unit = "个百分点"
            stem = f"2024年{source['label']}占全国货物出口额的比重较2023年变化约多少个百分点？（保留一位小数）"
            latex = rf"\frac{{{source['currentPart']}}}{{{current_total}}}-\frac{{{source['basePart']}}}{{{base_total}}}"
            candidates = [base_share - current_share, current_share - base_share * 100 / max(base_share, 0.1),
                          (source["currentPart"] - source["basePart"]) / source["basePart"] * 100,
                          source["currentPart"] / base_total * 100 - base_share,
                          current_share - source["basePart"] / current_total * 100]
            steps = [{"text": f"先分别算两期比重，再用现期减基期；差值以百分点表示，不能直接用部分量增速替代。数据来源：{source['sourceLabel']}。",
                      "latex": rf"{current_share:.1f}\%-{base_share:.1f}\%={target:.1f}\text{{个百分点}}"}]
        else:
            raise ValueError("比重题型形式无效")
        pitfall = "两期比重变化用百分点表示；先核对部分量和整体量是否属于同一时期、同一口径。"

    elif code == "average":
        if form == "average-current":
            points_by_label = {label: {"label": label, **item}
                               for label, item in GRAIN_YIELD_FACTS_BY_LABEL.items()}
            points_by_label.update({_grain_province_label(name): {"label": _grain_province_label(name),
                                                                   "value": y24, "unit": "公斤/公顷"}
                                    for name, _, _, _, _, _, y24 in GRAIN_PROVINCE_FACTS})
            points = list(points_by_label.values())
            item = _cycle_choice(points, config, rng)
            label = item["label"]
            source = {"kind": "grain-yield-point", "year": 2024, "label": label,
                      "value": item["value"], "unit": item["unit"],
                      "sourceLabel": GRAIN_YIELD_SOURCE, "sourceUrls": GRAIN_YIELD_SOURCE_URLS}
            target = item["value"]
            unit = item["unit"]
            stem = f"2024年{label}单位面积产量约为多少公斤/公顷？"
            latex = rf"\text{{{label}单产}}={target:.1f}\text{{公斤/公顷}}"
            candidates = [point["value"] for point in points if point["label"] != label]
            steps = [{"text": f"单位平均数/单产可用总产量÷播种面积计算。此题采用国家统计局公告直接公布的单产值，避免对四舍五入后的总量二次推算。来源：{source['sourceLabel']}。",
                      "latex": latex}]
        else:
            source = _cycle_choice(_grain_yield_period_sources(), config, rng)
            base_yield, current_yield = source["startValue"], source["endValue"]
            unit = source["unit"]
            period_label = source["label"]
            if form == "average-change":
                target = current_yield - base_yield
                stem = f"{source['endYear']}年{period_label}单位面积产量比{source['startYear']}年增加约多少{unit}？"
                latex = rf"{current_yield:.1f}-{base_yield:.1f}"
                candidates = [base_yield - current_yield, target / 10, (current_yield / base_yield - 1) * 100]
                steps = [{"text": f"平均数变化量＝现期平均数－基期平均数。两期单产为国家统计局公告值。来源：{source['sourceLabel']}。",
                          "latex": rf"{current_yield:.1f}-{base_yield:.1f}={target:.1f}\text{{{unit}}}"}]
            elif form == "average-growth":
                target = (current_yield / base_yield - 1) * 100
                unit = "%"
                precision = 2 if abs(target) < 0.5 else 1
                precision_label = "两位" if precision == 2 else "一位"
                stem = f"{source['endYear']}年{period_label}单位面积产量比{source['startYear']}年约增长多少？（保留{precision_label}小数）"
                latex = rf"\left(\frac{{{current_yield}}}{{{base_yield}}}-1\right)\times100\%"
                candidates = [(current_yield - base_yield) / current_yield * 100,
                              current_yield / base_yield * 100, (base_yield / current_yield - 1) * 100,
                              base_yield / current_yield * 100,
                              (current_yield - base_yield) / base_yield]
                steps = [{"text": f"平均数增速＝现期平均数÷基期平均数－1；不能直接用总产量增速替代。数据来源：{source['sourceLabel']}。",
                          "latex": rf"\left(\frac{{{current_yield}}}{{{base_yield}}}-1\right)\times100\%={target:.{precision}f}\%"}]
            else:
                raise ValueError("平均数题型形式无效")
        pitfall = "先确认平均数的分子、分母及单位；求变化量做差，求增速则以基期平均数为分母。"

    elif code == "multiple":
        gdp = GDP_COMPOSITION_FACTS
        choices = [
            ("全国GDP", "第三产业增加值", gdp[2023]["total"], gdp[2024]["total"],
             gdp[2023]["tertiary"], gdp[2024]["tertiary"], GDP_COMPOSITION_SOURCE, GDP_COMPOSITION_SOURCE_URLS),
            ("全国GDP", "第二产业增加值", gdp[2023]["total"], gdp[2024]["total"],
             gdp[2023]["secondary"], gdp[2024]["secondary"], GDP_COMPOSITION_SOURCE, GDP_COMPOSITION_SOURCE_URLS),
            ("第二产业增加值", "第一产业增加值", gdp[2023]["secondary"], gdp[2024]["secondary"],
             gdp[2023]["primary"], gdp[2024]["primary"], GDP_COMPOSITION_SOURCE, GDP_COMPOSITION_SOURCE_URLS),
            ("第三产业增加值", "第二产业增加值", gdp[2023]["tertiary"], gdp[2024]["tertiary"],
             gdp[2023]["secondary"], gdp[2024]["secondary"], GDP_COMPOSITION_SOURCE, GDP_COMPOSITION_SOURCE_URLS),
            ("货物出口额", "货物进口额", TRADE_CONCEPT_FACTS[2023]["export"], TRADE_CONCEPT_FACTS[2024]["export"],
             TRADE_CONCEPT_FACTS[2023]["import"], TRADE_CONCEPT_FACTS[2024]["import"], TRADE_CONCEPT_SOURCE, TRADE_CONCEPT_SOURCE_URLS),
        ]
        choices = [
            {"kind": "published-ratio", "baseYear": 2023, "currentYear": 2024,
             "numeratorLabel": row[0], "denominatorLabel": row[1],
             "baseNumerator": row[2], "currentNumerator": row[3],
             "baseDenominator": row[4], "currentDenominator": row[5],
             "sourceLabel": row[6], "sourceUrls": row[7]}
            for row in choices
        ] + _grain_production_ratio_sources()
        source = _cycle_choice(choices, config, rng)
        numerator_label, denominator_label = source["numeratorLabel"], source["denominatorLabel"]
        base_num, current_num = source["baseNumerator"], source["currentNumerator"]
        base_den, current_den = source["baseDenominator"], source["currentDenominator"]
        source_label = source["sourceLabel"]
        base_ratio, current_ratio = base_num / base_den, current_num / current_den
        unit = "倍"
        if form == "multiple-current":
            target = current_ratio
            stem = f"{source['currentYear']}年{numerator_label}约是{denominator_label}的多少倍？（保留一位小数）"
            latex = rf"\frac{{{current_num}}}{{{current_den}}}"
            candidates = [base_ratio, 1 / current_ratio, current_ratio - 1,
                          current_num / base_den, base_num / current_den]
            explanation = f"“是……的几倍”直接用前者除以后者。数据来源：{source_label}。"
        elif form == "multiple-base":
            target = base_ratio
            stem = f"{source['baseYear']}年{numerator_label}约是{denominator_label}的多少倍？（保留一位小数）"
            latex = rf"\frac{{{base_num}}}{{{base_den}}}"
            candidates = [current_ratio, 1 / base_ratio, base_ratio - 1,
                          current_num / base_den, base_num / current_den]
            explanation = f"基期倍数使用同一时期的数据相除。数据来源：{source_label}。"
        elif form == "multiple-excess":
            target = current_ratio - 1
            stem = f"{source['currentYear']}年{numerator_label}比{denominator_label}约多几倍？（保留一位小数）"
            latex = rf"\frac{{{current_num}-{current_den}}}{{{current_den}}}"
            candidates = [current_ratio, base_ratio - 1, (current_num - current_den) / current_num,
                          current_num / base_den, base_num / current_den]
            explanation = f"“比……多几倍”＝前者÷后者－1，与“是……的几倍”相差1。数据来源：{source_label}。"
        else:
            raise ValueError("倍数题型形式无效")
        steps = [{"text": explanation, "latex": f"{latex}={target:.1f}\\text{{倍}}"}]
        pitfall = "区分“是几倍”和“多几倍”；比值的分子、分母要按题目比较关系排列。"

    elif code == "mixed-growth":
        source = _cycle_choice(_mixed_growth_sources(), config, rng)
        components = source["components"]
        target = (source["currentTotal"] / source["baseTotal"] - 1) * 100
        unit = "%"
        component_text = "、".join(item["label"] for item in components)
        shown = "；".join(f"{item['label']}：{source['baseYear']}年{item['base']}{source['measureUnit']}，{source['currentYear']}年{item['current']}{source['measureUnit']}"
                          for item in components)
        stem = f"根据以下{source['aggregateLabel']}数据，所列部分合计同比增速约为多少？（保留一位小数）{shown}"
        latex = rf"\left(\frac{{{source['currentTotal']}}}{{{source['baseTotal']}}}-1\right)\times100\%"
        component_rates = [(item["current"] / item["base"] - 1) * 100 for item in components]
        current_weighted_rate = sum(item["current"] * rate for item, rate in zip(components, component_rates)) / source["currentTotal"]
        current_denominator_rate = (source["currentTotal"] - source["baseTotal"]) / source["currentTotal"] * 100
        candidates = [sum(component_rates) / len(component_rates), min(component_rates), max(component_rates),
                      current_weighted_rate, current_denominator_rate, *component_rates]
        basis_note = ("采用现价增加值，只训练合计增速的权重计算，不等同于官方按不变价核算的实际GDP增速。"
                      if source["priceBasis"] == "现价" else "所列项目来自同一统计口径，组合增速按基期量加权计算。")
        steps = [{"text": f"混合增速按各部分基期量加权，不能把各部分增速直接作算术平均。{basis_note}来源：{source['sourceLabel']}。",
                  "latex": latex + f"={target:.1f}\\%"}]
        pitfall = "各部分增速要按基期量加权；现价总量增速不能冒充不变价实际GDP增速。"

    elif code == "interval-growth":
        source = _cycle_choice(_interval_growth_sources(), config, rng)
        first_rate, second_rate = source["firstRate"], source["secondRate"]
        target = ((1 + first_rate / 100) * (1 + second_rate / 100) - 1) * 100
        unit = "%"
        stem = (f"按国家统计局公布值，{source['endYear']}年{source['label']}较{source['startYear']}年"
                "隔年增长率约为多少？（保留一位小数）")
        latex = rf"\left[(1+{first_rate:.2f}\%)(1+{second_rate:.2f}\%)-1\right]\times100\%"
        candidates = [first_rate + second_rate,
                      first_rate + second_rate - first_rate * second_rate / 100,
                      -target, first_rate * second_rate / 100,
                      (source["endValue"] / source["startValue"] - 1) * 100]
        explanation = (f"隔年增速＝（1＋前一年增速）×（1＋后一年的增速）－1。"
                       f"最快判断：两年增速幅度较小时，可先将 {first_rate:.1f}% 与 {second_rate:.1f}% 相加，"
                       "再用两者乘积项微调；不能把隔年增速直接当作年均增速。")
        steps = [{"text": explanation + f"数据来源：{source['sourceLabel']}。",
                  "latex": latex + f"={target:.1f}\\%"}]
        pitfall = "隔年增长率由连续两期同比增速复合而成；年均复合增长率还要按增长次数开方，两者不可混用。"
    elif code == "period-growth":
        sources = [item for item in _published_period_sources() if item["periods"] > 1]
        source = _cycle_choice(sources, config, rng)
        start_year, end_year = source["startYear"], source["endYear"]
        start_value, end_value, periods = source["startValue"], source["endValue"], source["periods"]
        value_label, value_unit = source["label"], source["unit"]
        unit = "%" if form == "annual-growth" else f"{value_unit}/年"
        if form == "annual-growth":
            target = ((end_value / start_value) ** (1 / periods) - 1) * 100
            stem = f"按国家统计局公布值，{start_year}—{end_year}年{value_label}年均复合增长率约为多少？（保留一位小数）"
            latex = rf"\left(\sqrt[{periods}]{{\frac{{{end_value}}}{{{start_value}}}}}-1\right)\times100\%"
            candidates = [(end_value / start_value - 1) * 100,
                          (end_value - start_value) / start_value / periods * 100,
                          ((end_value / start_value) ** (1 / (periods + 1)) - 1) * 100,
                          ((end_value / start_value) ** (1 / max(periods - 1, 1)) - 1) * 100,
                          (start_value / end_value - 1) * 100,
                          (end_value - start_value) / end_value * 100,
                          end_value / start_value * 100]
            ratio = end_value / start_value
            symmetric_estimate = (ratio - 1 / ratio) / (2 * periods) * 100
            linear_estimate = (ratio - 1) / periods * 100
            steps = [{"text": f"精确公式需开{periods}次方根。快捷估算可用（末期/初期－初期/末期）÷（2×增长次数），约为{symmetric_estimate:.1f}%；"
                                f"若只用累计增幅÷年数（约{linear_estimate:.1f}%），结果通常偏高。也可将选项代入(1+r)^{periods}与末期/初期比较。来源：{source['sourceLabel']}。",
                      "latex": latex + f"={target:.1f}\\%"}]
        elif form == "annual-amount":
            target = (end_value - start_value) / periods
            stem = f"按国家统计局公布值，{start_year}—{end_year}年{value_label}年均增加约多少{value_unit}？"
            latex = rf"\frac{{{end_value}-{start_value}}}{{{periods}}}"
            candidates = [end_value - start_value, (end_value - start_value) / (periods + 1),
                          start_value / periods, end_value / periods,
                          start_value / (periods + 1), end_value / (periods + 1)]
            steps = [{"text": f"年均增长量＝（末期值－初期值）÷增长次数；本题有{periods}个增长年度。来源：{source['sourceLabel']}。",
                      "latex": latex + f"={target:.1f}\\text{{{value_unit}/年}}"}]
        else:
            raise ValueError("跨期增长题型形式无效")
        pitfall = "年均增长量是绝对量均分，年均复合增长率是复合比例开方；增长次数按端点年份差计算。"

    elif code == "contribution":
        trade = _trade_source()
        all_items = [(item, "export", TRADE_CONCEPT_FACTS[2023]["export"],
                      TRADE_CONCEPT_FACTS[2024]["export"], "全国货物出口额")
                     for item in TRADE_EXPORT_ITEMS]
        all_items += [(item, "import", TRADE_CONCEPT_FACTS[2023]["import"],
                       TRADE_CONCEPT_FACTS[2024]["import"], "全国货物进口额")
                      for item in TRADE_IMPORT_ITEMS]
        selected_item = _cycle_choice(
            [{"item": item, "side": side, "baseTotal": base_total, "currentTotal": current_total,
              "totalLabel": total_label}
             for item, side, base_total, current_total, total_label in all_items], config, rng
        )
        item, side = selected_item["item"], selected_item["side"]
        base_total, current_total = selected_item["baseTotal"], selected_item["currentTotal"]
        total_label = selected_item["totalLabel"]
        source = {"kind": "trade-contribution", "baseYear": 2023, "currentYear": 2024,
                  "label": item["context"], "basePart": item["base"], "currentPart": item["current"],
                  "baseTotal": base_total, "currentTotal": current_total, "totalLabel": total_label,
                  "sourceLabel": trade["sourceLabel"], "sourceUrls": trade["sourceUrls"]}
        part_change = source["currentPart"] - source["basePart"]
        total_change = current_total - base_total
        if form == "contribution-rate":
            target = part_change / total_change * 100
            unit = "%"
            stem = f"2024年全国货物贸易增长中，{source['label']}增长量对{total_label}增长量的贡献率约为多少？（保留一位小数）"
            latex = rf"\frac{{{source['currentPart']}-{source['basePart']}}}{{{current_total}-{base_total}}}\times100\%"
            candidates = [source["currentPart"] / current_total * 100,
                          part_change / base_total * 100, part_change / current_total * 100,
                          part_change / source["basePart"] * 100,
                          total_change / base_total * 100]
            explanation = "贡献率＝部分增长量÷整体增长量；必须使用同一比较期的增量。"
        elif form == "growth-pull":
            target = part_change / base_total * 100
            unit = "个百分点"
            stem = f"2024年{source['label']}增长拉动{total_label}增长约多少个百分点？（保留一位小数）"
            latex = rf"\frac{{{source['currentPart']}-{source['basePart']}}}{{{base_total}}}\times100\%"
            candidates = [part_change / current_total * 100,
                          part_change / total_change * 100,
                          total_change / base_total * 100,
                          part_change / source["basePart"] * 100,
                          part_change / base_total]
            explanation = "拉动百分点＝部分增长量÷整体基期量×100；整体基期量应与部分增量的期间相匹配。"
        else:
            raise ValueError("贡献率题型形式无效")
        result_unit_latex = r"\%" if unit == "%" else r"\text{个百分点}"
        steps = [{"text": explanation + f"这里按公开贸易金额的现价变化改编，不代表国民经济核算中的实际增长贡献。数据来源：{source['sourceLabel']}。",
                  "latex": latex + f"={target:.1f}{result_unit_latex}"}]
        pitfall = "贡献率以整体增量为分母；拉动百分点以整体基期量为分母。负贡献或超过100%的贡献率都可能出现。"

    else:
        raise ValueError("不支持的数据概念题型")

    raw_target = float(target)
    values: list[float] = []
    display_precision = precision
    for candidate_precision in range(precision, 3):
        target = round(raw_target + 1e-10, candidate_precision)
        values = [target]
        for candidate in candidates:
            value = round(float(candidate) + 1e-10, candidate_precision)
            if value not in values:
                values.append(value)
            if len(values) == 4:
                break
        if len(values) == 4:
            display_precision = candidate_precision
            break
    if len(values) != 4:
        raise UnusableQuickCalcSample(f"{code} / {form} 的统计样本无法形成四个不同且可解释的选项")
    if display_precision > precision:
        precision_label = "两位" if display_precision == 2 else "三位"
        stem = stem.replace("保留一位小数", f"保留{precision_label}小数")
        old_value, new_value = f"{raw_target:.{precision}f}", f"{target:.{display_precision}f}"
        for step in steps:
            if step.get("latex"):
                step["latex"] = step["latex"].replace(old_value, new_value)
    rng.shuffle(values)
    option_text = [f"{value:.{display_precision}f}{unit}" for value in values]
    source["form"] = form
    source["sourceType"] = "official-statistics-adaptation"
    return {"method": code, "questionForm": form, "stem": stem, "latex": latex, "plain": stem,
            "options": option_text, "answer": values.index(target), "steps": steps, "pitfall": pitfall,
            "check": "data-concept", "target": target, "values": values, "unit": unit,
            "precision": display_precision, "source": source}


def _expected_data_concept_value(code: str, form: str, source: dict) -> float:
    """Independent公式复核；并验证题目引用的指标、口径和总分项关系。"""
    if code == "share":
        if source.get("kind") != "trade-export-share":
            raise ValueError("比重题源类型无效")
        if source["basePart"] > source["baseTotal"] or source["currentPart"] > source["currentTotal"]:
            raise ValueError("比重题部分量超过整体量")
        base_share = source["basePart"] / source["baseTotal"] * 100
        current_share = source["currentPart"] / source["currentTotal"] * 100
        return {"share-current": current_share, "share-base": base_share,
                "share-change": current_share - base_share}[form]
    if code == "average":
        if source.get("kind") == "grain-yield-point":
            if form != "average-current" or source.get("value", 0) <= 0:
                raise ValueError("单期单产题数据或题型无效")
            return source["value"]
        if source.get("kind") != "grain-yield-period":
            raise ValueError("平均数材料来源无效")
        base, current = source["startValue"], source["endValue"]
        return {"average-change": current - base, "average-growth": (current / base - 1) * 100}[form]
    if code == "multiple":
        if source.get("kind") != "published-ratio":
            raise ValueError("倍数题源类型无效")
        base_ratio = source["baseNumerator"] / source["baseDenominator"]
        current_ratio = source["currentNumerator"] / source["currentDenominator"]
        return {"multiple-current": current_ratio, "multiple-base": base_ratio,
                "multiple-excess": current_ratio - 1}[form]
    if code == "mixed-growth":
        components = source.get("components", [])
        if source.get("kind") != "statistical-mix" or len(components) < 2:
            raise ValueError("混合增长率需至少两个同口径统计组成部分")
        if any(item["base"] <= 0 or item["current"] < 0 for item in components):
            raise ValueError("混合增长率分项值无效")
        if sum(item["base"] for item in components) != source.get("baseTotal") or sum(item["current"] for item in components) != source.get("currentTotal"):
            raise ValueError("混合增长率分项与合计不一致")
        return (source["currentTotal"] / source["baseTotal"] - 1) * 100
    if code == "interval-growth":
        if source.get("kind") != "interval-growth":
            raise ValueError("隔年增长率材料来源无效")
        first = source["middleValue"] / source["startValue"] - 1
        second = source["endValue"] / source["middleValue"] - 1
        if abs(first * 100 - source["firstRate"]) > 1e-8 or abs(second * 100 - source["secondRate"]) > 1e-8:
            raise ValueError("隔年增长率与连续两期公开数据不一致")
        return ((1 + first) * (1 + second) - 1) * 100
    if code == "period-growth":
        start, end, periods = source.get("startValue", 0), source.get("endValue", 0), source.get("periods", 0)
        if source.get("kind") not in {"grain-yield-period", "per-capita-gdp"} or start <= 0 or periods <= 0 or source.get("endYear", 0) - source.get("startYear", 0) != periods:
            raise ValueError("跨期增长材料的年份或增长次数无效")
        if periods <= 1:
            raise ValueError("年均增长训练至少需要两个增长年度")
        return {"annual-growth": ((end / start) ** (1 / periods) - 1) * 100,
                "annual-amount": (end - start) / periods}[form]
    if code == "contribution":
        if source.get("kind") != "trade-contribution":
            raise ValueError("贡献率题源类型无效")
        part_change = source["currentPart"] - source["basePart"]
        total_change = source["currentTotal"] - source["baseTotal"]
        if total_change == 0:
            raise ValueError("整体增量不能为零")
        return {"contribution-rate": part_change / total_change * 100,
                "growth-pull": part_change / source["baseTotal"] * 100}[form]
    raise ValueError("未知的数据概念类型")

def _json(value, fallback):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _out(row: ZiliaoQuickMethod) -> dict:
    name = row.name
    scene = row.scene
    if row.code == "growth-amount":
        if name in {"增长量 · n＋1", "增长量 · n+1"}:
            name = "增长量"
        if scene in {"正增长率为 1/n，增长量＝现期量 / (n＋1)。", "正增长率为 1/n，增长量＝现期量 / (n+1)。"}:
            scene = "已知现期量和增长率，计算增长量；解析按数据特征推荐速算方法。"
    return {"id": row.id, "code": row.code, "name": name, "category": row.category,
            "scene": scene, "knowledgePath": row.knowledge_path, "nodeTitle": row.node_title,
            "nodeParent": row.node_parent, "config": _json(row.config_json, {}), "enabled": row.enabled,
            "status": row.status, "version": row.version, "sortOrder": row.sort_order}


def _snapshot(row: ZiliaoQuickMethod) -> dict:
    return {"code": row.code, "name": row.name, "category": row.category, "scene": row.scene,
            "knowledgePath": row.knowledge_path, "nodeTitle": row.node_title, "nodeParent": row.node_parent,
            "config": _json(row.config_json, {}), "enabled": row.enabled, "sortOrder": row.sort_order}


def ensure_seeded(db: Session) -> None:
    known = {x.code for x in db.query(ZiliaoQuickMethod.code).all()}
    # 旧比较方法及版本保留供历史记录使用；新训练入口按概念单独发布。
    for item in METHODS:
        if item["code"] in known:
            continue
        db.add(ZiliaoQuickMethod(
            code=item["code"], name=item["name"], category=item["category"], scene=item["scene"],
            knowledge_path=item["knowledgePath"], node_title=item["nodeTitle"], node_parent=item["nodeParent"],
            config_json=json.dumps({"min": 1000, "max": 9000, "difficulty": 2}), enabled=True,
            status="draft", version=0, sort_order=item["sortOrder"],
        ))
    db.flush()
    for row in db.query(ZiliaoQuickMethod).filter(
        ZiliaoQuickMethod.code.in_(LEGACY_DEFAULT_KNOWLEDGE_PATHS)
    ).all():
        if row.knowledge_path != LEGACY_DEFAULT_KNOWLEDGE_PATHS[row.code]:
            continue
        # 旧路径失效时，先把旧发布状态降为草稿，避免继续向学员暴露未关联到有效节点的规则。
        # 已发布快照仍保留，可通过版本记录追溯；发布新规则仍需管理员预览并显式发布。
        if row.status == "published":
            row.status = "draft"
        method = next(item for item in METHODS if item["code"] == row.code)
        row.knowledge_path = method["knowledgePath"]
        row.node_title = method["nodeTitle"]
        row.node_parent = method["nodeParent"]
    # Earlier releases grouped cumulative interval growth and annual averages
    # under one label. Keep the stable code/history, but make the admin entry
    # accurately describe its current annual-average-only training forms.
    for row in db.query(ZiliaoQuickMethod).filter_by(code="period-growth").all():
        if row.name == "间隔与年均增长":
            if row.status == "published":
                row.status = "draft"
            row.name = "年均增长"
            row.scene = "分别训练年均复合增长率和年均增长量；年均复合增速按题目条件建议估算与选项代入。"
    for row in db.query(ZiliaoQuickMethod).filter_by(status="published").all():
        version = db.query(ZiliaoQuickMethodVersion.id).filter_by(method_id=row.id, version=row.version).first()
        if not version:
            db.add(ZiliaoQuickMethodVersion(method_id=row.id, version=row.version,
                snapshot_json=json.dumps(_snapshot(row), ensure_ascii=False)))
    db.commit()


def list_methods(db: Session, *, published_only: bool = False) -> list[dict]:
    ensure_seeded(db)
    q = db.query(ZiliaoQuickMethod).filter(ZiliaoQuickMethod.code.in_([item["code"] for item in METHODS]))
    if published_only:
        q = q.filter(ZiliaoQuickMethod.status == "published", ZiliaoQuickMethod.enabled.is_(True))
    rows = q.order_by(ZiliaoQuickMethod.sort_order, ZiliaoQuickMethod.code).all()
    return [{**_out(row), **_knowledge_path_state(db, row.knowledge_path)} for row in rows]


def upsert_method(db: Session, data: ZiliaoQuickMethodUpsert, method_id: str | None = None) -> dict | None:
    if data.code not in {item["code"] for item in METHODS}:
        raise ValueError("方法编码不受支持")
    if not data.name.strip() or not data.scene.strip() or not data.knowledgePath.strip() or not data.nodeTitle.strip():
        raise ValueError("方法名称、适用场景和知识框架关联不能为空")
    try:
        minimum = int(data.config.get("min", 1000))
        maximum = int(data.config.get("max", 9000))
        difficulty = int(data.config.get("difficulty", 2))
    except (TypeError, ValueError):
        raise ValueError("出题规则参数必须是整数") from None
    if minimum < 100 or maximum > 100000 or minimum >= maximum:
        raise ValueError("数值范围须满足 100 ≤ 下限 < 上限 ≤ 100000")
    if not 1 <= difficulty <= 5:
        raise ValueError("难度级别须为 1 至 5")
    config = {"min": minimum, "max": maximum, "difficulty": difficulty}
    row = db.get(ZiliaoQuickMethod, method_id) if method_id else db.query(ZiliaoQuickMethod).filter_by(code=data.code).first()
    if method_id and not row:
        return None
    if not row:
        row = ZiliaoQuickMethod(id=gen_id("zqm"), code=data.code)
        db.add(row)
    if row.code != data.code and db.query(ZiliaoQuickMethod).filter(ZiliaoQuickMethod.code == data.code, ZiliaoQuickMethod.id != row.id).first():
        raise ValueError("方法编码已存在")
    was_published = row.status == "published"
    for attr, value in (("code", data.code), ("name", data.name), ("category", data.category),
                        ("scene", data.scene), ("knowledge_path", data.knowledgePath),
                        ("node_title", data.nodeTitle), ("node_parent", data.nodeParent),
                        ("config_json", json.dumps(config, ensure_ascii=False)),
                        ("enabled", data.enabled), ("sort_order", data.sortOrder)):
        setattr(row, attr, value)
    row.status = "draft" if was_published else (row.status or "draft")
    db.commit()
    db.refresh(row)
    return _out(row)


def publish_method(db: Session, method_id: str) -> dict | None:
    row = db.get(ZiliaoQuickMethod, method_id)
    if not row:
        return None
    if row.code in LEGACY_COMPARE_CODES:
        raise ValueError("原比较方法已合并为「分数比较」题型，请刷新列表后发布新题型。")
    if not row.enabled:
        raise ValueError("停用的方法不能发布")
    if row.status == "published":
        raise ValueError("方法已发布；请先编辑并保存为草稿，再发布新版本")
    knowledge_state = _knowledge_path_state(db, row.knowledge_path)
    if not knowledge_state["knowledgeResolved"]:
        raise ValueError(knowledge_state["knowledgeMessage"])
    validate_method(row.code, _json(row.config_json, {}))
    row.version += 1
    row.status = "published"
    db.add(ZiliaoQuickMethodVersion(method_id=row.id, version=row.version,
        snapshot_json=json.dumps(_snapshot(row), ensure_ascii=False)))
    db.commit()
    db.refresh(row)
    return _out(row)


def list_method_versions(db: Session, method_id: str) -> list[dict] | None:
    row = db.get(ZiliaoQuickMethod, method_id)
    if not row:
        return None
    return [{"version": item.version, "publishedAt": item.published_at.isoformat(),
             "snapshot": _json(item.snapshot_json, {})}
            for item in db.query(ZiliaoQuickMethodVersion).filter_by(method_id=method_id)
            .order_by(ZiliaoQuickMethodVersion.version.desc()).all()]


def rollback_method(db: Session, method_id: str, version_number: int) -> dict | None:
    row = db.get(ZiliaoQuickMethod, method_id)
    version = db.query(ZiliaoQuickMethodVersion).filter_by(method_id=method_id, version=version_number).first()
    if not row or not version:
        return None
    snapshot = _json(version.snapshot_json, {})
    row.code = snapshot["code"]; row.name = snapshot["name"]; row.category = snapshot["category"]
    row.scene = snapshot["scene"]; row.knowledge_path = snapshot["knowledgePath"]
    row.node_title = snapshot["nodeTitle"]; row.node_parent = snapshot["nodeParent"]
    row.config_json = json.dumps(snapshot["config"], ensure_ascii=False)
    row.enabled = snapshot["enabled"]; row.sort_order = snapshot["sortOrder"]
    row.status = "draft"
    db.commit()
    return publish_method(db, method_id)


def _options(correct: str, distractors: list[str], rng: random.Random) -> tuple[list[str], int]:
    values = list(dict.fromkeys([correct, *distractors]))
    fallbacks = [">", "<", "=", "无法判断"]
    step = 0
    while len(values) < 4:
        candidate = fallbacks[step]
        step += 1
        if candidate not in values:
            values.append(candidate)
    values = values[:4]
    rng.shuffle(values)
    return values, values.index(correct)


def _fraction_value(numerator: int, denominator: int) -> tuple[int, int]:
    return numerator, denominator


def _fraction_multi_question(form: str, config: dict, rng: random.Random) -> dict:
    """构造四个数值接近但顺序唯一的分数，题干选项都可独立精确校验。"""
    low = max(1000, int(config.get("min", 1000)))
    high = max(low + 100, min(100000, int(config.get("max", 9000))))
    difficulty = max(1, min(5, int(config.get("difficulty", 2))))
    for _ in range(100):
        anchor = rng.randint(25, 105) / 100
        fractions = []
        for _index in range(4):
            denominator = rng.randint(low, high)
            spread = max(2, 9 - difficulty)
            numerator = max(1, round(denominator * (anchor + rng.randint(-spread, spread) / 1000)))
            fractions.append((numerator, denominator))
        # 按整数交叉乘积排序，避开等值和近似相同的选项。
        order = sorted(range(4), key=cmp_to_key(lambda i, j: fractions[i][0] * fractions[j][1] - fractions[j][0] * fractions[i][1]))
        ratios = [fractions[i][0] / fractions[i][1] for i in order]
        if len({(a, b) for a, b in fractions}) == 4 and all(
            abs(ratios[i + 1] - ratios[i]) > 0.00005 for i in range(3)
        ):
            break
    else:
        raise ValueError("无法生成顺序明确的分数比较题")

    labels = "ABCD"
    values_latex = ",\\quad ".join(
        f"{labels[i]}=\\frac{{{numerator}}}{{{denominator}}}"
        for i, (numerator, denominator) in enumerate(fractions)
    )
    if form == "multi-extrema":
        pick_largest = rng.choice([True, False])
        target_index = order[-1] if pick_largest else order[0]
        options = list(labels)
        rng.shuffle(options)
        answer = options.index(labels[target_index])
        verb = "最大" if pick_largest else "最小"
        neighbor_index = order[-2] if pick_largest else order[1]
        target_num, target_den = fractions[target_index]
        neighbor_num, neighbor_den = fractions[neighbor_index]
        relation = ">" if pick_largest else "<"
        product_relation = ">" if target_num * neighbor_den > neighbor_num * target_den else "<"
        steps = [
            {"text": f"解题技巧：先比较数量级接近的候选项，再用交叉乘积核验边界；{labels[target_index]} 对应分数{verb}。",
             "latex": (f"\\frac{{{target_num}}}{{{target_den}}}{relation}"
                       f"\\frac{{{neighbor_num}}}{{{neighbor_den}}}"
                       f"\\Longleftrightarrow {target_num}\\times {neighbor_den}"
                       f"{product_relation} {neighbor_num}\\times {target_den}")},
        ]
        stem = f"比较四个分数，选出数值{verb}的一项。"
        source = {"labels": list(labels), "fractions": fractions, "order": order, "pickLargest": pick_largest}
        pitfall = "分子更大不代表分数更大；请同时考虑分母，临界关系用交叉乘积确认。"
    else:
        descending = rng.choice([True, False])
        correct_order = list(reversed(order)) if descending else list(order)
        permutations = [list(correct_order)]
        for i in range(3):
            candidate = list(correct_order)
            left = (i + (1 if descending else 0)) % 3
            candidate[left], candidate[left + 1] = candidate[left + 1], candidate[left]
            if candidate not in permutations:
                permutations.append(candidate)
        # 四个选项必须互不相同；必要时从相邻交换组合补齐。
        for i, j in ((0, 2), (1, 3), (0, 3), (1, 2), (0, 1), (2, 3)):
            if len(permutations) == 4:
                break
            candidate = list(correct_order)
            candidate[i], candidate[j] = candidate[j], candidate[i]
            if candidate not in permutations:
                permutations.append(candidate)
        options = [" ".join(labels[i] for i in candidate) for candidate in permutations]
        correct = options[0]
        rng.shuffle(options)
        answer = options.index(correct)
        relation = "从大到小" if descending else "从小到大"
        chain = (" > " if descending else " < ").join(labels[i] for i in correct_order)
        adjacent_checks = []
        for left_index, right_index in zip(correct_order, correct_order[1:]):
            left_num, left_den = fractions[left_index]
            right_num, right_den = fractions[right_index]
            product_relation = "<" if left_num * right_den < right_num * left_den else ">"
            adjacent_checks.append(
                f"\\frac{{{left_num}}}{{{left_den}}} {product_relation} "
                f"\\frac{{{right_num}}}{{{right_den}}}"
                f"\\;({left_num}\\times{right_den} {product_relation} {right_num}\\times{left_den})"
            )
        steps = [{"text": "解题技巧：先按接近程度估出顺序，再逐对核验相邻分数；完整排序必须确认每一对相邻项。",
                  "latex": chain + r"\quad " + r"\;".join(adjacent_checks)}]
        stem = f"将四个分数按数值{relation}排列，选择正确顺序。"
        source = {"labels": list(labels), "fractions": fractions, "order": correct_order, "descending": descending}
        pitfall = "排序题需要确认相邻项关系；只找到最大或最小项还不足以确定完整顺序。"

    source["sourceType"] = "teaching-simulation"
    return {
        "method": "fraction-compare", "questionForm": form,
        "stem": stem, "latex": values_latex,
        "plain": "; ".join(f"{labels[i]}={a}/{b}" for i, (a, b) in enumerate(fractions)),
        "options": options, "answer": answer, "steps": steps, "pitfall": pitfall,
        "check": "fraction-multi", "source": source,
    }


def _calculation_audit_question(question: dict, form: str, rng: random.Random) -> dict:
    """把同一组数据改造成四个计算表述辨析，后台保留逐项真值供校验和复盘。"""
    source = question["source"]
    precision = 1 if question.get("unit") in {"%", "万吨", "公斤/公顷"} else 0
    if question["method"] == "growth-amount":
        current, rate = source["current"], source["rate"] / 100
        target = question["target"]
        stem = "根据题干数据，以下哪一项对增长量的计算正确？" if form == "calculation-correct" else "根据题干数据，以下哪一项对增长量的计算错误？"
        steps = [{"text": "增长量＝现期量×增长率÷（1＋增长率）。逐项代入后，核对公式结构和计算结果。",
                  "latex": f"X=\\frac{{{current:g}\\times {rate:g}}}{{1+{rate:g}}}\\approx {target:g}"}]
    elif question["method"] == "growth-rate":
        current, base = source["current"], source["base"]
        target = question["target"]
        stem = "根据题干数据，以下哪一项对增长率的计算正确？" if form == "calculation-correct" else "根据题干数据，以下哪一项对增长率的计算错误？"
        steps = [{"text": "增长率＝（现期量－基期量）÷基期量。重点检查分母是否为基期量，以及增减方向。",
                  "latex": f"R=\\frac{{{current:g}-{base:g}}}{{{base:g}}}\\times100\\%={target:g}\\%"}]
    else:
        current, rate = source["current"], source["rate"] / 100
        target = question["target"]
        stem = "根据题干数据，以下哪一项对基期量的计算正确？" if form == "calculation-correct" else "根据题干数据，以下哪一项对基期量的计算错误？"
        steps = [{"text": "基期量＝现期量÷（1＋增长率）。核对选项是否按题干给出的增减方向还原。",
                  "latex": f"A=\\frac{{{current:g}}}{{1+{rate:g}}}\\approx {target:g}"}]

    precision = 1 if question.get("unit") in {"%", "万吨", "公斤/公顷"} else 0
    if question["method"] == "growth-amount":
        current, rate = source["current"], source["rate"] / 100
        # 增长量题给学员的是按一位小数展示的增速；基期由该展示值反推，确保题面数据自洽。
        base = current / (1 + rate)
        correct_candidates = [
            (f"现期量×增长率÷（1＋增长率）≈{target:g}", target),
            (f"现期量－基期量＝{current:g}－{base:g}＝{_material_number(current - base, precision)}", current - base),
            (f"基期量×增长率≈{target:g}", target),
            (f"现期量－现期量÷（1＋增长率）≈{target:g}", target),
        ]
        wrong_candidates = [
            (f"现期量×增长率≈{_material_number(current * rate, precision)}", current * rate),
            (f"现期量×增长率÷（1－增长率）≈{_material_number(current * rate / (1 - rate), precision)}", current * rate / (1 - rate)),
            (f"现期量×增长率×（1＋增长率）≈{_material_number(current * rate * (1 + rate), precision)}", current * rate * (1 + rate)),
            (f"现期量×增长率×（1＋2×增长率）≈{_material_number(current * rate * (1 + 2 * rate), precision)}", current * rate * (1 + 2 * rate)),
            (f"现期量×增长率÷（1＋2×增长率）≈{_material_number(current * rate / (1 + 2 * rate), precision)}", current * rate / (1 + 2 * rate)),
        ]
    elif question["method"] == "growth-rate":
        current, base = source["current"], source["base"]
        delta = current - base
        correct_candidates = [
            (f"（现期量－基期量）÷基期量×100%＝{target:g}%", target),
            (f"（现期量÷基期量－1）×100%≈{target:g}%", target),
            (f"增长量×100%÷基期量≈{target:g}%", target),
            (f"现期量×100%÷基期量－100%≈{target:g}%", target),
        ]
        wrong_candidates = [
            (f"增长量÷现期量×100%＝{round(delta / current * 100, 1):g}%", delta / current * 100),
            (f"（基期量－现期量）÷基期量×100%＝{round(-delta / base * 100, 1):g}%", -delta / base * 100),
            (f"现期量÷基期量×100%＝{round(current / base * 100, 1):g}%", current / base * 100),
            (f"增长量÷（基期量＋现期量）×100%＝{round(delta / (base + current) * 100, 1):g}%", delta / (base + current) * 100),
            (f"增长量÷（2×基期量）×100%＝{round(delta / (2 * base) * 100, 1):g}%", delta / (2 * base) * 100),
        ]
    else:
        current, rate = source["current"], source["rate"] / 100
        correct_candidates = [
            (f"现期量÷（1＋增长率）≈{_material_number(target, precision)}", target),
            (f"现期量－增长量≈{_material_number(target, precision)}", target),
            (f"现期量×100%÷（100%＋增长率）≈{_material_number(target, precision)}", target),
            (f"现期量÷（现期量÷基期量）≈{_material_number(target, precision)}", target),
        ]
        wrong_candidates = [
            (f"现期量×（1－增长率）≈{_material_number(current * (1 - rate), precision)}", current * (1 - rate)),
            (f"现期量÷（1－增长率）≈{_material_number(current / (1 - rate), precision)}", current / (1 - rate)),
            (f"现期量×（1＋增长率）≈{_material_number(current * (1 + rate), precision)}", current * (1 + rate)),
            (f"现期量÷（1＋2×增长率）≈{_material_number(current / (1 + 2 * rate), precision)}", current / (1 + 2 * rate)),
            (f"现期量×（1＋2×增长率）≈{_material_number(current * (1 + 2 * rate), precision)}", current * (1 + 2 * rate)),
        ]

    target_value = round(float(target) + 1e-10, precision)
    if form == "calculation-correct":
        candidates = [correct_candidates[0]]
        used_values = {target_value}
        for candidate in wrong_candidates:
            rounded = round(float(candidate[1]) + 1e-10, precision)
            if rounded not in used_values:
                candidates.append(candidate)
                used_values.add(rounded)
            if len(candidates) == 4:
                break
        if len(candidates) != 4:
            raise ValueError("计算辨析题干扰项舍入后无法区分")
    else:
        candidates = [*correct_candidates[:3]]
        wrong = next((item for item in wrong_candidates
                      if round(float(item[1]) + 1e-10, precision) != target_value), None)
        if wrong is None:
            raise ValueError("计算辨析题无法构造唯一错误项")
        candidates.append(wrong)
    normalized = [(label, round(float(value) + 1e-10, precision)) for label, value in candidates]
    truth = [value == target_value for _, value in normalized]
    if len(set(label for label, _ in normalized)) < 4:
        raise ValueError("计算辨析题选项文本重复")
    answer_truth = True if form == "calculation-correct" else False
    answer_indices = [i for i, is_true in enumerate(truth) if is_true == answer_truth]
    if len(answer_indices) != 1:
        raise ValueError("计算辨析题正确/错误项数量不唯一")
    pairs = [(label, truth_value, value) for (label, value), truth_value in zip(normalized, truth)]
    rng.shuffle(pairs)
    result = {
        **question, "questionForm": form, "stem": stem,
        "latex": question["latex"], "plain": question["stem"],
        "options": [label for label, _, _ in pairs], "answer": next(i for i, (_, truth_value, _) in enumerate(pairs) if truth_value == answer_truth),
        "steps": steps, "claims": [truth_value for _, truth_value, _ in pairs], "claimValues": [value for _, _, value in pairs],
        "check": "calculation-audit", "pitfall": "先辨认目标量对应的公式，再逐项检查分母、运算方向和单位。",
    }
    return result


MATERIAL_CONCEPTS = ("growth-amount", "growth-rate", "base", "current")
MATERIAL_CORRECT_FORMULAS = {
    "growth-amount": "amount-difference",
    "growth-rate": "rate-base",
    "base": "base-divide",
    "current": "current-multiply",
}


def _material_number(value: float, precision: int = 0) -> str:
    rounded = round(float(value) + 1e-10, precision)
    return f"{rounded:,.{precision}f}" if precision else f"{int(rounded):,}"


def _material_formula_value(concept: str, row: dict, formula: str) -> tuple[float, int]:
    base, current = row["base"], row["current"]
    rate = row["rateDisplayed"] / 100
    delta = current - base
    if concept == "growth-amount":
        formulas = {
            "amount-difference": (delta, 0),
            "amount-current-rate": (current * rate, 0),
            "amount-current-rate-wrong-denominator": (current * rate / (1 - rate), 0),
            "amount-arithmetic-slip": (delta + 1, 0),
        }
    elif concept == "growth-rate":
        formulas = {
            "rate-base": (delta / base * 100, 1),
            "rate-current": (delta / current * 100, 1),
            "rate-reversed": (-delta / base * 100, 1),
            "rate-arithmetic-slip": (delta / base * 100 + 1, 1),
        }
    elif concept == "base":
        formulas = {
            "base-divide": (current / (1 + rate), 0),
            "base-multiply-complement": (current * (1 - rate), 0),
            "base-divide-complement": (current / (1 - rate), 0),
            "base-divide-double-rate": (current / (1 + 2 * rate), 0),
            "base-arithmetic-slip": (current / (1 + rate) + 1, 0),
        }
    else:
        formulas = {
            "current-multiply": (base * (1 + rate), 0),
            "current-multiply-complement": (base * (1 - rate), 0),
            "current-divide": (base / (1 + rate), 0),
            "current-multiply-double-rate": (base * (1 + 2 * rate), 0),
            "current-arithmetic-slip": (base * (1 + rate) + 1, 0),
        }
    if formula not in formulas:
        raise ValueError("综合材料题公式编码无效")
    value, precision = formulas[formula]
    return round(float(value) + 1e-10, precision), precision


def _material_option(concept: str, row: dict, formula: str) -> tuple[str, float, int]:
    base, current = row["base"], row["current"]
    rate = row["rateDisplayed"]
    rate_text = f"{abs(rate):.2f}%"
    signed_rate_text = f"{'−' if rate < 0 else ''}{rate_text}"
    signed_factor = f"1{'+' if rate >= 0 else '−'}{rate_text}"
    name = row["context"]
    if concept == "growth-amount":
        if formula in {"amount-difference", "amount-arithmetic-slip"}:
            expression = f"{_material_number(current)}−{_material_number(base)}"
        elif formula == "amount-current-rate":
            expression = f"{_material_number(current)}×（{signed_rate_text}）"
        else:
            expression = f"{_material_number(current)}×（{signed_rate_text}）÷（1−（{signed_rate_text}））"
        label = f"增长量｜{name}：{expression}＝"
        unit = "亿元"
    elif concept == "growth-rate":
        if formula in {"rate-base", "rate-arithmetic-slip"}:
            denominator = base
        elif formula == "rate-current":
            denominator = current
        else:
            label = f"增长率｜{name}：（{_material_number(base)}−{_material_number(current)}）÷{_material_number(base)}×100%＝"
            value, precision = _material_formula_value(concept, row, formula)
            return f"{label}{_material_number(value, precision)}%", value, precision
        label = f"增长率｜{name}：（{_material_number(current)}−{_material_number(base)}）÷{_material_number(denominator)}×100%＝"
        unit = "%"
    elif concept == "base":
        if formula in {"base-divide", "base-arithmetic-slip"}:
            expression = f"{_material_number(current)}÷（{signed_factor}）"
        elif formula == "base-multiply-complement":
            expression = f"{_material_number(current)}×（1−（{signed_rate_text}））"
        elif formula == "base-divide-complement":
            expression = f"{_material_number(current)}÷（1−（{signed_rate_text}））"
        else:
            expression = f"{_material_number(current)}÷（1{'+' if rate >= 0 else '−'}2×{rate_text}）"
        label = f"基期量｜{name}：{expression}≈"
        unit = "亿元"
    else:
        if formula in {"current-multiply", "current-arithmetic-slip"}:
            expression = f"{_material_number(base)}×（{signed_factor}）"
        elif formula == "current-multiply-complement":
            expression = f"{_material_number(base)}×（1−（{signed_rate_text}））"
        elif formula == "current-divide":
            expression = f"{_material_number(base)}÷（{signed_factor}）"
        else:
            expression = f"{_material_number(base)}×（1{'+' if rate >= 0 else '−'}2×{rate_text}）"
        label = f"现期量｜{name}：{expression}≈"
        unit = "亿元"
    value, precision = _material_formula_value(concept, row, formula)
    suffix = f"{unit}" if unit != "%" else "%"
    return f"{label}{_material_number(value, precision)}{suffix}", value, precision


def _material_audit_question(form: str, rng: random.Random) -> dict:
    """用同一来源、同一单位的真实两期数据，组合四类计算项形成长材料辨析题。"""
    eligible = []
    for fact in GROWTH_RATE_FACTS:
        exact_rate = (fact["current"] - fact["base"]) / fact["base"] * 100
        rounded_rate = round(exact_rate, 2)
        # 只使用按题面保留两位增速后，基期和现期都能准确还原的材料。
        if (round(fact["current"] / (1 + rounded_rate / 100)) == fact["base"]
                and round(fact["base"] * (1 + rounded_rate / 100)) == fact["current"]):
            eligible.append({**fact, "rateDisplayed": rounded_rate})
    if len(eligible) < 4:
        raise ValueError("真实统计材料不足，无法组成综合计算题")
    positive = [fact for fact in eligible if fact["current"] >= fact["base"]]
    negative = [fact for fact in eligible if fact["current"] < fact["base"]]
    if positive and negative:
        rows = [rng.choice(positive), rng.choice(negative)]
        remainder = [fact for fact in eligible if fact not in rows]
        rows.extend(rng.sample(remainder, 2))
        rng.shuffle(rows)
    else:
        rows = rng.sample(eligible, 4)
    concepts = list(MATERIAL_CONCEPTS)
    rng.shuffle(concepts)
    form_is_correct = form == "material-correct"
    target_index = rng.randrange(4)
    items = []
    for index, (concept, row) in enumerate(zip(concepts, rows)):
        correct_formula = MATERIAL_CORRECT_FORMULAS[concept]
        use_correct = index == target_index if form_is_correct else index != target_index
        if use_correct:
            formula = correct_formula
        else:
            candidates = {
                "growth-amount": ("amount-current-rate", "amount-current-rate-wrong-denominator", "amount-arithmetic-slip"),
                "growth-rate": ("rate-current", "rate-reversed", "rate-arithmetic-slip"),
                "base": ("base-multiply-complement", "base-divide-complement", "base-divide-double-rate", "base-arithmetic-slip"),
                "current": ("current-multiply-complement", "current-divide", "current-multiply-double-rate", "current-arithmetic-slip"),
            }[concept]
            correct_value, precision = _material_formula_value(concept, row, correct_formula)
            formula = next((candidate for candidate in candidates
                            if _material_formula_value(concept, row, candidate)[0] != correct_value), None)
            if formula is None:
                raise ValueError("综合材料题干扰项舍入后无法区分")
        label, value, precision = _material_option(concept, row, formula)
        correct_value, _ = _material_formula_value(concept, row, correct_formula)
        truth = formula == correct_formula and value == correct_value
        items.append({"concept": concept, "rowIndex": index, "formula": formula,
                      "correctFormula": correct_formula, "value": value, "precision": precision,
                      "truth": truth, "label": label})

    # Keep each option paired with its source row, then shuffle the options without losing that link.
    rng.shuffle(items)
    expected_true_count = 1 if form_is_correct else 3
    if sum(bool(item["truth"]) for item in items) != expected_true_count:
        raise ValueError("综合材料题正确/错误项数量不唯一")
    answer = next(i for i, item in enumerate(items) if bool(item["truth"]) == form_is_correct)
    steps = []
    for item in items:
        row = rows[item["rowIndex"]]
        label, _, _ = _material_option(item["concept"], row, item["correctFormula"])
        strategy = ""
        if item["concept"] == "growth-amount":
            exact_rate = (row["current"] - row["base"]) / row["base"] * 100
            strategy, advice = _growth_amount_advice(exact_rate)
            strategy = f"建议方法：{strategy}。{advice} "
        steps.append({"text": f"正确计算：{label}。{strategy}"})

    source_rows = [{"context": row["context"], "base": row["base"], "current": row["current"],
                    "rateDisplayed": row["rateDisplayed"]} for row in rows]
    return {
        "method": "mixed", "questionForm": form,
        "stem": "根据材料，以下四项计算中哪一项" + ("正确？" if form_is_correct else "错误？"),
        "latex": "material-audit:" + ":".join(str(row["context"]) for row in rows),
        "plain": "", "material": {
            "title": "公开统计数据改编｜2023—2024年国家统计局国民经济和社会发展统计公报（单位：亿元）",
            "headers": ["指标", "2023年", "2024年"],
            "rows": [[row["context"], _material_number(row["base"]), _material_number(row["current"])] for row in rows],
        },
        "options": [item["label"] for item in items], "answer": answer,
        "steps": steps,
        "pitfall": "先核对指标名称、时期和单位，再辨认各选项对应的计算概念；增长率的分母是基期量，基期量与现期量的还原要注意增减方向。",
        "check": "material-audit", "claims": [bool(item["truth"]) for item in items],
        "claimValues": [item["value"] for item in items],
        "source": {"sourceType": "official-statistics-adaptation",
                    "sourceLabel": TRADE_CONCEPT_SOURCE, "sourceUrls": TRADE_CONCEPT_SOURCE_URLS,
                    "rows": source_rows, "items": [{key: item[key] for key in
                    ("concept", "rowIndex", "formula", "correctFormula", "value", "precision", "truth")}
                    for item in items]},
    }


def _growth_rate_fact_batch(config: dict, rng: random.Random, count: int) -> list[dict]:
    """按增速方向和幅度分层抽取真实数据，避免一组题集中在同一类场景。"""
    level = max(1, min(5, int(config.get("difficulty", 2))))
    max_rate = 5 if level == 1 else 15 if level == 2 else float("inf")
    # Below 0.5%, several common wrong-denominator formulas collapse to the same
    # one-decimal answer. Retain genuine low-growth examples from 0.5% upward;
    # lower changes remain available to concepts where this rounding ambiguity
    # does not affect whether an answer is uniquely judgeable.
    eligible = [
        fact for fact in [*_official_trade_growth_facts(), *_official_grain_growth_facts()]
        if 0.5 <= abs(fact["rate"]) <= max_rate
    ]
    buckets = {
        "positive_near": [], "positive_low": [], "positive_high": [],
        "negative_near": [], "negative_low": [], "negative_high": [],
    }
    for fact in eligible:
        rate = (fact["current"] - fact["base"]) / fact["base"] * 100
        if abs(rate) <= 1:
            bucket = "positive_near" if rate >= 0 else "negative_near"
        elif rate > 0:
            bucket = "positive_low" if rate <= 5 else "positive_high"
        else:
            bucket = "negative_low" if rate >= -5 else "negative_high"
        buckets[bucket].append(fact)
    for pool in buckets.values():
        rng.shuffle(pool)

    # 在正负增长方向内按幅度分层轮换，避免每次都优先抽空“接近零”样本。
    # 难度较低时缺少高幅度场景，空桶会自然跳过。
    sign_order = ["positive", "negative"]
    band_order = ["near", "low", "high"]
    facts: list[dict] = []
    while len(facts) < count and any(buckets.values()):
        progressed = False
        # 奇数题量时正增长多一道，确保预览整体读感不被负增长压过。
        quotas = {"positive": (count + 1) // 2, "negative": count // 2}
        used_by_sign = {
            sign: sum(1 for fact in facts
                      if (fact["current"] >= fact["base"]) == (sign == "positive"))
            for sign in sign_order
        }
        for band in band_order:
            for sign in sign_order:
                key = f"{sign}_{band}"
                if (buckets[key] and used_by_sign[sign] < quotas[sign]
                        and len(facts) < count):
                    facts.append(buckets[key].pop())
                    used_by_sign[sign] += 1
                    progressed = True
        # 某一方向库存不足时，从另一方向尚有库存的场景补齐。
        if len(facts) < count and not progressed:
            for sign in sign_order:
                for band in band_order:
                    key = f"{sign}_{band}"
                    if buckets[key]:
                        facts.append(buckets[key].pop())
                        progressed = True
                        break
                if progressed:
                    break
        if not progressed:
            break
    return facts


def _base_period_fact_batch(config: dict, rng: random.Random, count: int) -> list[dict]:
    """Choose real two-period observations for base-period questions."""
    return _growth_rate_fact_batch(config, rng, count)


def _growth_amount_advice(rate: float) -> tuple[str, str]:
    reciprocal = min(range(2, 21), key=lambda n: abs(abs(rate) - 100 / n))
    reciprocal_gap = abs(abs(rate) - 100 / reciprocal)
    if rate < 0:
        if reciprocal_gap <= 0.15:
            return "除乘转化法", f"下降率接近常见分数 1/{reciprocal}，下降量系数可转为 1/{reciprocal - 1} 估算，结果方向为负。"
        if abs(rate) <= 5:
            return "除乘转化法", "先用现期量×下降率÷（1－下降率）估算下降量绝对值，注意结果方向为负。"
        if abs(rate) <= 8:
            return "乘数拆分法", "把下降量绝对值的系数看作下降率÷（1－下降率），拆成便于心算的乘数估算，结果方向为负。"
        if abs(rate) <= 12:
            return "假设估算法", "可从选项假设一个好算的下降量绝对值，反推基期量和下降率，比较后确定选项。"
        return "错位加减法", "先将下降量绝对值化为现期量×下降率÷（1－下降率），按有效数字配位估算，最后标明下降方向。"
    if reciprocal_gap <= 0.15:
        return "除乘转化法", f"增速接近常见分数 1/{reciprocal}，可把增长量系数转成乘法系数，再结合选项估算。"
    if abs(rate) <= 5:
        return "除乘转化法", "增速较小，可把现期量×r÷（1＋r）转成乘法近似；结果略受增速方向影响。"
    if abs(rate) <= 8:
        return "乘数拆分法", "先把 r÷（1＋r）看成乘数，再拆成便于心算的部分估算。"
    if abs(rate) <= 12:
        return "假设估算法", "可从选项假设一个好算的增长量，反推基期和增速，比较后确定选项。"
    return "错位加减法", "把增长量列式化为乘除后，按有效数字配位，并同步调整分子分母进行估算。"


def _growth_amount_fact_batch(config: dict, rng: random.Random, count: int) -> list[dict]:
    """从真实两期统计数据中按可用速算策略分层抽题。"""
    level = max(1, min(5, int(config.get("difficulty", 2))))
    max_rate = 5 if level == 1 else 15 if level == 2 else float("inf")
    # For growth-amount drills, rates below 2.5% produce very small amounts in
    # several official grain series; at displayed precision, ordinary formula
    # mistakes can collapse to the same answer. Choose source samples with a
    # distinguishable result rather than inventing arithmetic-slip choices.
    eligible = [fact for fact in [*_official_trade_growth_facts(), *_official_grain_growth_facts()]
                if 2.5 <= abs(fact["rate"]) <= max_rate]
    eligible = [
        *eligible,
        *[fact for fact in GROWTH_AMOUNT_REFERENCE_FACTS if 2.5 <= abs(fact["rate"]) <= max_rate],
    ]
    strategies: dict[str, list[dict]] = {
        name: [] for name in ("除乘转化法", "乘数拆分法", "假设估算法", "错位加减法")
    }
    for fact in eligible:
        rate = round(fact.get("rate", (fact["current"] - fact["base"]) / fact["base"] * 100), 1)
        strategy, _ = _growth_amount_advice(rate)
        strategies[strategy].append(fact)
    for pool in strategies.values():
        rng.shuffle(pool)

    facts: list[dict] = []
    order = ["除乘转化法", "乘数拆分法", "假设估算法", "错位加减法"]
    while len(facts) < count and any(strategies.values()):
        progressed = False
        for strategy in order:
            if strategies[strategy] and len(facts) < count:
                facts.append(strategies[strategy].pop())
                progressed = True
        if not progressed:
            break
    used = {(fact["context"], fact.get("period", "")) for fact in facts}
    remaining = [fact for fact in eligible if (fact["context"], fact.get("period", "")) not in used]
    rng.shuffle(remaining)
    facts.extend(remaining[:max(0, count - len(facts))])
    return facts


def _generate(code: str, config: dict, rng: random.Random, growth_rate_fact: dict | None = None) -> dict:
    low = max(100, int(config.get("min", 1000)))
    high = max(low + 100, min(100000, int(config.get("max", 9000))))
    level = max(1, min(5, int(config.get("difficulty", 2))))
    if code in EXTENDED_CODES:
        return _data_concept_question(code, config, rng)
    if code == "fraction-compare":
        form = config.get("_questionForm", "pair")
        if form in {"multi-extrema", "multi-sort"}:
            return _fraction_multi_question(form, config, rng)
        strategy = config.get("_compareStrategy") or rng.choice(tuple(COMPARE_STRATEGIES))
        question = _generate(strategy, config, rng)
        strategy_name, advice = COMPARE_STRATEGIES[strategy]
        question["method"] = code
        question["questionForm"] = "pair"
        question["strategy"] = strategy
        question["steps"].insert(0, {"text": f"最快建议：{strategy_name}。{advice}"})
        question["source"] = {**question.get("source", {}), "concept": code, "strategy": strategy}
        return question
    if code in LEGACY_COMPARE_CODES:
        if code == "direct":
            c, d = rng.randint(low, high), rng.randint(low, high)
            a, b = c + rng.randint(20, 200) * level, max(1, d - rng.randint(20, 200) * level)
            step = f"左边分子 {a} 大于 {c}，分母 {b} 小于 {d}，所以左边分数更大。"
            pitfall = "分子、分母都更大时，不能直接说分数更大。"
        elif code == "difference":
            d_min = max(500, low // 5); d_max = max(d_min + 1, min(2400, high // 3))
            d = rng.randint(d_min, d_max); k = rng.randint(3, 9); c = k * d + rng.randint(100, 400)
            delta = rng.randint(12, 40) * level; high_side = rng.choice([True, False]); da = (k + 2 if high_side else k - 1) * delta
            a, b = c + da, d + delta
            cmp = "更大" if high_side else "更小"
            step = f"差分数为 {da}/{delta}={da // delta}，右边原分数位于 {k} 与 {k + 1} 之间，左边原分数{cmp}。"
            pitfall = "差分法要求分子、分母同向作差且差分母为正。"
        elif code == "position":
            k = rng.randint(2, 4); c_min = max(500, low // 2); c_max = max(c_min + 1, min(4000, high))
            c = rng.randint(c_min, c_max); d = rng.randint(200, max(201, min(600, high // 10)))
            a, b = k * c + rng.randint(20, 100) * level, k * d - rng.randint(10, 60) * level
            step = f"分子超过 {k} 倍、分母不足 {k} 倍，因此左边大于同时放大后的右边。"
            pitfall = "分子、分母跨越倍数界线的方向相反时才能直接判定。"
        else:
            c_min = max(1500, low); c_max = max(c_min + 1, min(9000, high))
            c = rng.randint(c_min, c_max); a = c + rng.randint(400, 800)
            left_rest = rng.randint(150, 350) * level; right_rest = left_rest + rng.randint(30, 180) * level
            b, d = a + left_rest, c + right_rest
            step = f"两个分数均小于 1，改比部分/剩余：{a}/{left_rest} 与 {c}/{right_rest}，左边更大。"
            pitfall = "要求 0＜分子＜分母且剩余量为正。"
        if rng.random() < .5:
            a, b, c, d = c, d, a, b
            step = step.replace("左边", "临时侧").replace("右边", "左边").replace("临时侧", "右边")
        delta = a * d - c * b
        answer_text = ">" if delta > 0 else "<" if delta < 0 else "="
        options, answer = _options(answer_text, ["无法判断"], rng)
        latex = f"\\frac{{{a}}}{{{b}}}\\quad\\text{{与}}\\quad\\frac{{{c}}}{{{d}}}"
        strategy_name = COMPARE_STRATEGIES[code][0]
        product_relation = ">" if a * d > c * b else "<" if a * d < c * b else "="
        return {"method": code, "stem": "比较下面两个分数的大小，选择正确关系。", "latex": latex,
                "plain": f"{a}/{b} 与 {c}/{d}", "options": options, "answer": answer,
                "steps": [{"text": f"解题方法：{strategy_name}。{step} 最后用交叉相乘复核大小关系。",
                           "latex": f"{a}\\times{d} {product_relation} {c}\\times{b}"}], "pitfall": pitfall,
                "check": "compare", "values": [a, b, c, d], "source": {"method": code}}

    if code == "growth-amount":
        fact = growth_rate_fact or _growth_amount_fact_batch(config, rng, 1)[0]
        current = fact["current"]
        base = fact["base"]
        rate = round(fact.get("rate", (current - base) / base * 100), 1)
        rate_ratio = rate / 100
        target = current * rate_ratio / (1 + rate_ratio)
        direction = "增长" if rate >= 0 else "下降"
        unit_label = fact.get("unit", "亿元")
        if fact.get("sourceLabel") and fact.get("sourceUrls"):
            source_intro = f"根据{fact['sourceLabel']}，{fact.get('period', '2023—2024年')}{fact['context']}"
        elif fact.get("sourceLabel"):
            source_intro = f"真题数据改编（{fact['sourceLabel']}）：{fact['period']}{fact['context']}"
        else:
            source_intro = f"根据 2023—2024 年国家统计公报，2024 年{fact['context']}"
        stem = (
            f"{source_intro}为 {current:g} {unit_label}，同比{direction} {abs(rate):g}%，"
            "该指标同比变化量约为多少？"
        )
        rate_latex = f"{rate:g}\\%"
        denominator_latex = f"1{'+' if rate >= 0 else ''}{rate_latex}"
        latex = f"\\frac{{{current:g}\\times {rate_latex}}}{{{denominator_latex}}}"
        strategy, advice = _growth_amount_advice(rate)
        steps = [{
            "text": f"建议方法：{strategy}。{advice} 按增长量公式计算，约为 {target:g} {unit_label}。",
            "latex": f"X=\\frac{{{current:g}\\times {rate_latex}}}{{{denominator_latex}}}\\approx {target:g}\\text{{{unit_label}}}",
        }]
        pitfall = "增长量＝现期量×增长率÷（1＋增长率）；核对结果方向与题干中的增减方向一致。"
        naive = current * rate_ratio
        wrong_denominator = current * rate_ratio / (1 - rate_ratio) if rate_ratio != 1 else current * rate_ratio * 2
        candidates = [target, naive, wrong_denominator, target * 100, target / (1 + rate_ratio)]
        source = {"current": current, "base": base, "rate": rate, "context": fact["context"],
                  "period": fact.get("period", ""), "unit": unit_label,
                  "sourceLabel": fact.get("sourceLabel", ""), "sourceUrls": fact.get("sourceUrls", []),
                  "sourceType": "official-statistics-adaptation" if fact.get("sourceUrls") else "exam-data-adaptation"}
        unit = unit_label
    elif code == "growth-rate":
        fact = growth_rate_fact or _growth_rate_fact_batch(config, rng, 1)[0]
        current = fact["current"]
        base = fact["base"]
        growth_amount = round(current - base, 2)
        target = round(growth_amount / base * 100, 1)
        unit = "%"
        base_year, current_year = fact.get("baseYear", 2023), fact.get("currentYear", 2024)
        value_unit = fact.get("unit", "亿元")
        source_label = fact.get("sourceLabel", "国家统计局2023、2024年统计公报")
        stem = (
            f"根据{source_label}，{base_year}年{fact['context']}为 {base:g} {value_unit}，"
            f"{current_year}年为 {current:g} {value_unit}，同比增速约为多少？（保留一位小数）"
        )
        latex = f"\\frac{{{current:g}-{base:g}}}{{{base:g}}}\\times100\\%"
        change_text = (
            f"增长量为 {growth_amount:g} {value_unit}"
            if growth_amount >= 0
            else f"现期量比基期量减少 {abs(growth_amount):g} {value_unit}"
        )
        steps = [{
            "text": f"{change_text}，再除以基期量 {base:g} {value_unit}，得到 {target:.1f}%。数据来源：{source_label}。",
            "latex": f"R=\\frac{{{current:g}-{base:g}}}{{{base:g}}}\\times100\\%={target:.1f}\\%",
        }]
        pitfall = "增长率的分母是基期量；用现期量作分母会算小。"
        wrong_denominator = growth_amount / current * 100
        rounded_whole = round(target)
        forgot_percent_scale = growth_amount / base
        ratio_without_minus_one = current / base * 100
        candidates = [target, wrong_denominator, -target, rounded_whole,
                      forgot_percent_scale, ratio_without_minus_one,
                      growth_amount / (base + current) * 100]
        source = {"current": current, "base": base, "context": fact["context"],
                  "period": fact.get("period", ""), "unit": value_unit,
                  "baseYear": base_year, "currentYear": current_year,
                  "sourceLabel": source_label, "sourceUrls": fact.get("sourceUrls", []),
                  "sourceType": "official-statistics-adaptation"}
    elif code == "base":
        fact = growth_rate_fact or _base_period_fact_batch(config, rng, 1)[0]
        rate = round(fact.get("rate", (fact["current"] - fact["base"]) / fact["base"] * 100), 1)
        current = fact["current"]
        direction = "增长" if rate >= 0 else "下降"
        rate_text = f"{abs(rate):g}%"
        latex_denominator = f"1{'+' if rate >= 0 else '-'}{abs(rate):g}\\%"
        target = current / (1 + rate / 100); unit = fact.get("unit", "亿元")
        base_precision = 1 if unit in {"万吨", "公斤/公顷"} else 0
        source_label = fact.get("sourceLabel", "国家统计局与海关总署公开统计数据")
        source_intro = f"根据{source_label}，{fact.get('currentYear', '')}年{fact['context']}"
        stem = f"{source_intro}现期量为 {current:g} {unit}，同比{direction} {rate_text}，基期量最接近多少？"
        latex = f"\\frac{{{current:g}}}{{{latex_denominator}}}"
        steps = [{
            "text": f"基期量＝现期量÷（1{'＋' if rate >= 0 else '－'}{rate_text}）。题中增速按一位小数展示，按题面数据还原后最接近 {target:.{base_precision}f} {unit}。数据来源：{source_label}。",
            "latex": f"A=\\frac{{{current:g}}}{{{latex_denominator}}}\\approx{target:.{base_precision}f}\\text{{{unit}}}",
        }]
        pitfall = "基期量＝现期量÷（1＋增长率）；核对分母是否按题干给出的增减方向取值。"
        # 三类常见误算：把增长率直接从现期量扣除、分母符号用反、直接把现期量当基期量。
        candidates = [
            target,
            current * (1 - rate / 100),
            current / (1 - rate / 100) if rate != 100 else -1,
            current,
            current * (1 + rate / 100),
            current / (1 + abs(rate) / 100),
            current / (1 + rate),
            current / (1 - rate) if rate != 1 else -1,
        ]
        source = {"current": current, "base": fact["base"], "rate": rate,
                  "context": fact["context"], "period": fact.get("period", ""), "unit": unit,
                  "baseYear": fact.get("baseYear"), "currentYear": fact.get("currentYear"),
                  "sourceLabel": source_label, "sourceUrls": fact.get("sourceUrls", []),
                  "sourceType": "official-statistics-adaptation"}
    else:
        raise ValueError("不支持的速算生成方法")
    precision = 1 if unit in {"%", "万吨", "公斤/公顷"} else (base_precision if code == "base" else 0)
    round_to = lambda n: round(float(n) + 1e-10, precision)
    target = round_to(target); values = []
    for value in candidates:
        value = round_to(value)
        if (value >= 0 or code in {"growth-rate", "growth-amount"}) and value not in values:
            values.append(value)
    values = values[:4]
    if len(values) != 4:
        raise UnusableQuickCalcSample(f"{code} 的样本无法形成四个不同且有依据的选项")
    rng.shuffle(values)
    options = [f"{v:g}{unit}" for v in values]
    result = {"method": code, "questionForm": "calculation", "stem": stem, "latex": latex, "plain": stem, "options": options,
              "answer": values.index(target), "steps": steps, "pitfall": pitfall,
              "check": "number", "target": target, "values": values, "unit": unit,
              "precision": precision, "source": source}
    requested_form = config.get("_questionForm", "calculation")
    if requested_form in CALCULATION_FORMS:
        return _calculation_audit_question(result, requested_form, rng)
    return result


def _safe_question(question: dict) -> dict:
    return {k: v for k, v in question.items() if k not in {"answer", "check", "values", "target", "unit", "source", "steps", "pitfall", "strategy", "claims", "claimValues"}}


def preview(db: Session, code: str, count: int = 5) -> dict:
    method = next((m for m in list_methods(db) if m["code"] == code), None)
    if not method:
        raise ValueError("训练方法不存在")
    rng = random.Random(20261016)
    count = max(1, min(20, count))
    if code == "growth-rate":
        growth_facts = _growth_rate_fact_batch(method["config"], rng, count)
    elif code == "growth-amount":
        growth_facts = _growth_amount_fact_batch(method["config"], rng, count)
    elif code == "base":
        growth_facts = _base_period_fact_batch(method["config"], rng, count)
    else:
        growth_facts = []
    questions = []
    strategy_codes = list(COMPARE_STRATEGIES)
    pair_strategy_index = 0
    for i in range(count):
        config = dict(method["config"])
        if code == "fraction-compare":
            form = FRACTION_FORMS[i % len(FRACTION_FORMS)]
            if form == "pair":
                config["_compareStrategy"] = strategy_codes[pair_strategy_index % len(strategy_codes)]
                pair_strategy_index += 1
            config["_questionForm"] = form
        elif code in {"growth-amount", "growth-rate", "base"}:
            config["_questionForm"] = CALCULATION_FORM_SEQUENCE[i % len(CALCULATION_FORM_SEQUENCE)]
        elif code in EXTENDED_CODES:
            config["_questionForm"] = EXTENDED_FORMS[code][i % len(EXTENDED_FORMS[code])]
            config["_sourceIndex"] = i
        if code in EXTENDED_CODES:
            for attempt in range(250):
                config["_sourceIndex"] = i + attempt
                try:
                    candidate = _generate(code, config, rng)
                except UnusableQuickCalcSample:
                    continue
                identity = (candidate["method"], candidate.get("questionForm", ""), candidate["stem"], candidate["latex"])
                if any((q["method"], q.get("questionForm", ""), q["stem"], q["latex"]) == identity for q in questions):
                    continue
                questions.append(candidate)
                break
            else:
                raise ValueError(f"{method['name']} 当前没有足够的真实样本生成有效预览")
        else:
            questions.append(_generate(code, config, rng, growth_facts[i] if growth_facts else None))
    _validate_questions(questions)
    knowledge_state = _knowledge_path_state(db, method["knowledgePath"])
    knowledge_resolved = knowledge_state["knowledgeResolved"]
    return {"valid": knowledge_resolved, "mathValid": True, **knowledge_state,
            "validationMessage": knowledge_state["knowledgeMessage"],
            "method": method, "questions": questions}


def _path_matches_tree(tree: dict, parts: list[str]) -> bool:
    if not parts or str(tree.get("title", "")).strip() != parts[0]:
        return False
    siblings = tree.get("children") or []
    for title in parts[1:]:
        node = next((item for item in siblings if str(item.get("title", "")).strip() == title), None)
        if node is None:
            return False
        siblings = node.get("children") or []
    return True


def _knowledge_path_state(db: Session, path: str) -> dict:
    """Separate draft-node existence from student-facing publish readiness."""
    parts = [part.strip() for part in path.split("/") if part.strip()]
    if len(parts) < 2:
        return {"knowledgeResolved": False, "knowledgeDraftResolved": False,
                "knowledgeStatus": "missing", "knowledgeMessage": "知识关联路径格式无效，请选择知识框架节点。"}

    from app.models import KnowledgeNode, KnowledgeTree
    from app.services.knowledge_structured import get_draft

    tree_row = db.query(KnowledgeTree).filter(KnowledgeTree.tree_key == parts[0]).first()
    if not tree_row:
        return {"knowledgeResolved": False, "knowledgeDraftResolved": False,
                "knowledgeStatus": "tree_missing", "knowledgeMessage": f"知识树「{parts[0]}」尚未导入。"}

    draft_tree = get_draft(db, tree_row)
    draft_resolved = _path_matches_tree(draft_tree, parts)
    relative_path = "/".join(parts[1:])
    live_resolved = db.query(KnowledgeNode.id).filter(
        KnowledgeNode.tree_key == tree_row.tree_key,
        KnowledgeNode.path == relative_path,
        KnowledgeNode.archived_at.is_(None),
    ).first() is not None
    is_live = int(tree_row.live_version or 0) > 0
    is_visible = bool(tree_row.is_visible)
    ready = live_resolved and is_live and is_visible

    if ready:
        status, message = "ready", "关联节点已发布且学员可见。"
    elif live_resolved and not is_visible:
        status, message = "tree_hidden", "已找到已发布的知识节点，但知识树尚未设为学员可见。请先开启可见，再发布训练方法。"
    elif draft_resolved and not is_live:
        status, message = "tree_unpublished", "草稿中已找到该节点；请先发布知识框架，再发布训练方法。"
    elif draft_resolved:
        status, message = "node_unpublished", "草稿中已找到该节点，但当前已发布版本尚不包含它。请先发布知识框架草稿。"
    else:
        status, message = "node_missing", f"知识框架中未找到路径「{' / '.join(parts)}」。请修正关联路径或补充节点。"

    return {"knowledgeResolved": ready, "knowledgeDraftResolved": draft_resolved,
            "knowledgeStatus": status, "knowledgeMessage": message}


def _validate_questions(questions: list[dict]) -> None:
    for question in questions:
        if len(question["options"]) != 4 or len(set(question["options"])) != 4:
            raise ValueError("选项必须为四个互不重复的内容")
        if question["check"] == "data-concept":
            code, form, source = question["method"], question.get("questionForm", ""), question.get("source", {})
            if code not in EXTENDED_CODES or form not in EXTENDED_FORMS[code]:
                raise ValueError("资料分析概念题型或题目形式无效")
            precision = int(question.get("precision", 1))
            if precision not in {1, 2}:
                raise ValueError("资料分析概念题显示精度无效")
            expected = round(_expected_data_concept_value(code, form, source) + 1e-10, precision)
            if question.get("target") != expected or question["values"][question["answer"]] != expected:
                raise ValueError("资料分析概念题与独立公式复核结果不一致")
            if len(question["values"]) != 4 or len(set(question["values"])) != 4:
                raise ValueError("资料分析概念题数值选项必须唯一")
            if not source.get("sourceLabel") or not source.get("sourceUrls"):
                raise ValueError("资料分析概念题缺少可追溯的数据来源")
            if code == "mixed-growth" and source.get("priceBasis") not in {"现价", "同口径粮食产量"}:
                raise ValueError("混合增长题必须明确数据口径")
        elif question["check"] == "fraction-multi":
            source = question["source"]
            fractions = source["fractions"]
            if len(fractions) != 4 or any(a <= 0 or b <= 0 for a, b in fractions):
                raise ValueError("多分数题必须含四个正分数")
            order = sorted(range(4), key=cmp_to_key(lambda i, j: fractions[i][0] * fractions[j][1] - fractions[j][0] * fractions[i][1]))
            if len({(fractions[i][0], fractions[i][1]) for i in range(4)}) != 4:
                raise ValueError("多分数题存在重复数值")
            if question["questionForm"] == "multi-extrema":
                expected_label = "ABCD"[order[-1] if source["pickLargest"] else order[0]]
                if question["options"][question["answer"]] != expected_label:
                    raise ValueError("多分数最大/最小题答案不一致")
            elif question["questionForm"] == "multi-sort":
                expected_order = list(reversed(order)) if source["descending"] else order
                expected = " ".join("ABCD"[i] for i in expected_order)
                if question["options"][question["answer"]] != expected:
                    raise ValueError("多分数排序题答案不一致")
        elif question["check"] == "calculation-audit":
            claims = question["claims"]
            claim_values = question["claimValues"]
            should_be_true = question["questionForm"] == "calculation-correct"
            expected_true_count = 1 if should_be_true else 3
            if len(claims) != 4 or len(claim_values) != 4 or sum(claims) != expected_true_count:
                raise ValueError("计算辨析题正确/错误项数量不符合题干要求")
            precision = 1 if question.get("unit") in {"%", "万吨", "公斤/公顷"} else 0
            if claims != [value == round(float(question["target"]) + 1e-10, precision) for value in claim_values]:
                raise ValueError("计算辨析题选项真值与独立结果校验不一致")
            if claims[question["answer"]] is not should_be_true:
                raise ValueError("计算辨析题正确/错误选项索引不一致")
            source = question["source"]
            if question["method"] == "growth-amount":
                exact_precision = 1 if question.get("unit") in {"万吨", "公斤/公顷"} else 0
                exact = round(source["current"] * (source["rate"] / 100) / (1 + source["rate"] / 100) + 1e-10, exact_precision)
            elif question["method"] == "growth-rate":
                exact = round((source["current"] - source["base"]) / source["base"] * 100 + 1e-10, 1)
            else:
                exact_precision = 1 if question.get("unit") in {"万吨", "公斤/公顷"} else 0
                exact = round(source["current"] / (1 + source["rate"] / 100) + 1e-10, exact_precision)
            if exact != question["target"]:
                raise ValueError("计算辨析题源数据与标准答案不一致")
        elif question["check"] == "material-audit":
            form = question["questionForm"]
            if form not in {"material-correct", "material-incorrect"}:
                raise ValueError("综合材料题题目形式无效")
            source = question["source"]
            rows, items = source.get("rows", []), source.get("items", [])
            if len(rows) != 4 or len(items) != 4:
                raise ValueError("综合材料题必须包含四个数据项和四个计算项")
            if {item.get("concept") for item in items} != set(MATERIAL_CONCEPTS):
                raise ValueError("综合材料题的四个选项必须覆盖四种计算概念")
            expected_true_count = 1 if form == "material-correct" else 3
            expected_claims = []
            for index, item in enumerate(items):
                concept, row_index = item.get("concept"), item.get("rowIndex")
                if not isinstance(row_index, int) or not 0 <= row_index < len(rows):
                    raise ValueError("综合材料题计算项与材料行不匹配")
                row = rows[row_index]
                if item.get("correctFormula") != MATERIAL_CORRECT_FORMULAS[concept]:
                    raise ValueError("综合材料题标准公式定义不一致")
                calculated_value, precision = _material_formula_value(concept, row, item.get("formula", ""))
                exact_value, _ = _material_formula_value(concept, row, item["correctFormula"])
                truth = item["formula"] == item["correctFormula"] and calculated_value == exact_value
                label, _, _ = _material_option(concept, row, item["formula"])
                if (calculated_value != item.get("value") or precision != item.get("precision")
                        or truth is not item.get("truth") or question["options"][index] != label):
                    raise ValueError("综合材料题选项与独立公式核验结果不一致")
                expected_claims.append(truth)
            if expected_claims != question.get("claims") or sum(expected_claims) != expected_true_count:
                raise ValueError("综合材料题正确/错误项数量不符合题干要求")
            if question.get("claimValues") != [item["value"] for item in items]:
                raise ValueError("综合材料题计算结果与选项不一致")
            answer_truth = form == "material-correct"
            if expected_claims[question["answer"]] is not answer_truth:
                raise ValueError("综合材料题答案索引与题干要求不一致")
            for row in rows:
                rate = row["rateDisplayed"] / 100
                if (round(row["current"] / (1 + rate)) != row["base"]
                        or round(row["base"] * (1 + rate)) != row["current"]):
                    raise ValueError("综合材料题所用数据无法按展示增速还原")
        elif question["check"] == "compare":
            a, b, c, d = question["values"]
            strategy = question.get("strategy", question["method"])
            if min(a, b, c, d) <= 0:
                raise ValueError("分数分子、分母必须为正数")
            delta = a * d - c * b
            expected = ">" if delta > 0 else "<" if delta < 0 else "="
            if question["options"][question["answer"]] != expected:
                raise ValueError("分数比较答案与交叉乘积校验不一致")
            if strategy == "split" and not (a < b and c < d):
                raise ValueError("分母拆分题未满足正分数适用条件")
            if strategy == "direct" and not ((a > c and b < d) or (a < c and b > d)):
                raise ValueError("分数性质题未满足分子、分母方向相反的条件")
            if strategy == "difference":
                if a > c:
                    high_n, high_d, low_n, low_d = a, b, c, d
                else:
                    high_n, high_d, low_n, low_d = c, d, a, b
                if high_n <= low_n or high_d <= low_d:
                    raise ValueError("差分题的分子分母没有同向增加")
                delta_sign = (high_n - low_n) * low_d - low_n * (high_d - low_d)
                fraction_sign = high_n * low_d - low_n * high_d
                if (delta_sign > 0) != (fraction_sign > 0):
                    raise ValueError("差分题中差分数与原分数的关系不一致")
            if strategy == "position":
                if a > c:
                    high_n, high_d, low_n, low_d = a, b, c, d
                else:
                    high_n, high_d, low_n, low_d = c, d, a, b
                if not any(high_n > k * low_n and high_d < k * low_d for k in (2, 3, 4)):
                    raise ValueError("同位比较题未满足同一倍数界线条件")
            if strategy == "split":
                split_sign = a * (d - c) - c * (b - a)
                if (split_sign > 0) != (delta > 0):
                    raise ValueError("分母拆分前后大小关系不一致")
        elif question["values"][question["answer"]] != question["target"]:
            raise ValueError("数值题正确选项与精确结果不一致")
        else:
            source = question["source"]
            if question["method"] == "growth-amount":
                rate = source["rate"] / 100
                exact_precision = 1 if question.get("unit") in {"万吨", "公斤/公顷"} else 0
                exact = round(source["current"] * rate / (1 + rate) + 1e-10, exact_precision)
            elif question["method"] == "growth-rate":
                exact = round((source["current"] - source["base"]) / source["base"] * 100 + 1e-10, 1)
            else:
                exact_precision = 1 if question.get("unit") in {"万吨", "公斤/公顷"} else 0
                exact = round(source["current"] / (1 + source["rate"] / 100) + 1e-10, exact_precision)
                if question["method"] == "base":
                    source_rate = (source["current"] - source["base"]) / source["base"] * 100
                    if round(source_rate + 1e-10, 1) != source["rate"]:
                        raise ValueError("基期量题展示增速与公开两期数据不一致")
                    if not source.get("sourceLabel") or not source.get("sourceUrls"):
                        raise ValueError("基期量题缺少可追溯的数据来源")
            if exact != question["target"]:
                raise ValueError("题干数据独立计算与正确答案不一致")


def validate_method(code: str, config: dict) -> None:
    rng = random.Random(731)
    if code == "fraction-compare":
        questions = [
            _generate(code, {**config, "_compareStrategy": tuple(COMPARE_STRATEGIES)[i % 4],
                            "_questionForm": FRACTION_FORMS[i % len(FRACTION_FORMS)]}, rng)
            for i in range(20)
        ]
    elif code in {"growth-amount", "growth-rate", "base"}:
        questions = [
            _generate(code, {**config, "_questionForm": CALCULATION_FORM_SEQUENCE[i % len(CALCULATION_FORM_SEQUENCE)]}, rng)
            for i in range(20)
        ]
    elif code in EXTENDED_CODES:
        forms = EXTENDED_FORMS[code]
        questions = [_generate(code, {**config, "_questionForm": forms[i % len(forms)]}, rng) for i in range(24)]
    else:
        questions = [_generate(code, config, rng) for _ in range(20)]
    _validate_questions(questions)


def create_session(db: Session, user_id: str, mode: str, count: int) -> dict:
    mode = LEGACY_TO_CONCEPT.get(mode, mode)
    methods = list_methods(db, published_only=True)
    selected = [m for m in methods if mode == "mixed" or m["code"] == mode]
    if not selected:
        raise ValueError("没有可用的已发布训练方法")
    rng = random.SystemRandom()
    if mode == "mixed":
        rng.shuffle(selected)
    questions = []
    seen: set[tuple[str, str, str, str]] = set()
    versions = {method["code"]: method["version"] for method in selected}
    selected_codes = {method["code"] for method in selected}
    material_indexes = (
        set(range(9, count, 10))
        if mode == "mixed" and count >= 10
        and {"growth-amount", "growth-rate", "base"}.issubset(selected_codes)
        else set()
    )
    if material_indexes:
        versions["material-audit"] = 1
    if mode == "growth-rate":
        growth_facts = _growth_rate_fact_batch(selected[0]["config"], rng, count)
    elif mode == "growth-amount":
        growth_facts = _growth_amount_fact_batch(selected[0]["config"], rng, count)
    elif mode == "base":
        growth_facts = _base_period_fact_batch(selected[0]["config"], rng, count)
    else:
        growth_facts = []
    mixed_fact_batches: dict[str, list[dict]] = {}
    mixed_fact_offsets: dict[str, int] = {}
    if mode == "mixed":
        for method in selected:
            code = method["code"]
            if code not in {"growth-amount", "growth-rate", "base"}:
                continue
            needed = sum(
                1 for index in range(count)
                if index not in material_indexes and selected[index % len(selected)]["code"] == code
            )
            if code == "growth-amount":
                mixed_fact_batches[code] = _growth_amount_fact_batch(method["config"], rng, needed)
            elif code == "base":
                mixed_fact_batches[code] = _base_period_fact_batch(method["config"], rng, needed)
            else:
                mixed_fact_batches[code] = _growth_rate_fact_batch(method["config"], rng, needed)
            mixed_fact_offsets[code] = 0
    compare_index = 0
    compare_order = list(COMPARE_STRATEGIES)
    rng.shuffle(compare_order)
    fraction_form_order = list(FRACTION_FORMS)
    form_phase = rng.randrange(len(fraction_form_order))
    concept_question_index: dict[str, int] = {}
    for i in range(count):
        if i in material_indexes:
            form = "material-correct" if (i // 10) % 2 == 0 else "material-incorrect"
            question = _material_audit_question(form, rng)
            questions.append({**question, "id": gen_id("qci")})
            continue
        method = selected[i % len(selected)] if mode == "mixed" else selected[0]
        config = dict(method["config"])
        if method["code"] == "fraction-compare":
            form = fraction_form_order[(compare_index + form_phase) % len(fraction_form_order)]
            config["_questionForm"] = form
            if form == "pair":
                config["_compareStrategy"] = compare_order[sum(1 for q in questions if q["method"] == "fraction-compare" and q["questionForm"] == "pair") % len(compare_order)]
            compare_index += 1
        elif method["code"] in {"growth-amount", "growth-rate", "base"}:
            concept_index = concept_question_index.get(method["code"], 0)
            config["_questionForm"] = CALCULATION_FORM_SEQUENCE[concept_index % len(CALCULATION_FORM_SEQUENCE)]
            concept_question_index[method["code"]] = concept_index + 1
        elif method["code"] in EXTENDED_CODES:
            concept_index = concept_question_index.get(method["code"], 0)
            forms = EXTENDED_FORMS[method["code"]]
            config["_questionForm"] = forms[concept_index % len(forms)]
            config["_sourceIndex"] = concept_index
            concept_question_index[method["code"]] = concept_index + 1
        question = None
        if mode == "mixed" and method["code"] in mixed_fact_batches:
            offset = mixed_fact_offsets[method["code"]]
            facts = mixed_fact_batches[method["code"]]
            fact = facts[offset] if offset < len(facts) else None
            mixed_fact_offsets[method["code"]] = offset + 1
        else:
            fact = growth_facts[i] if i < len(growth_facts) else None
        for _ in range(100):
            candidate_config = config
            if method["code"] in EXTENDED_CODES and _:
                candidate_config = {**config, "_sourceIndex": config.get("_sourceIndex", 0) + _}
            try:
                candidate = _generate(method["code"], candidate_config, rng, fact)
            except UnusableQuickCalcSample:
                continue
            identity = (candidate["method"], candidate.get("questionForm", ""), candidate["stem"], candidate["latex"])
            if identity not in seen:
                question = candidate
                seen.add(identity)
                break
        if question is None:
            raise ValueError("本组题目无法去重，请调整方法或题量")
        questions.append({**question, "id": gen_id("qci")})
    if mode == "mixed":
        rng.shuffle(questions)
    _validate_questions(questions)
    row = ZiliaoQuickSession(id=gen_id("zqs"), user_id=user_id, mode=mode,
        method_versions_json=json.dumps(versions), questions_json=json.dumps(questions, ensure_ascii=False),
        answers_json="[]", status="active")
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "mode": mode, "questions": [_safe_question(q) for q in questions]}


def answer_question(db: Session, user_id: str, session_id: str, question_id: str, selected: int, seconds: int) -> dict | None:
    row = db.get(ZiliaoQuickSession, session_id)
    if not row or row.user_id != user_id or row.status != "active":
        return None
    questions = _json(row.questions_json, []); answers = _json(row.answers_json, [])
    question = next((q for q in questions if q["id"] == question_id), None)
    if not question:
        raise ValueError("题目不属于当前练习")
    existing = next((a for a in answers if a["questionId"] == question_id), None)
    if existing:
        if existing["selected"] != selected:
            raise ValueError("本题已经提交，不能修改答案")
        return {"correct": existing["correct"], "correctOption": question["options"][question["answer"]], "steps": question["steps"], "pitfall": question["pitfall"],
                "optionFeedback": ["该计算成立" if value else "该计算不成立" for value in question.get("claims", [])]}
    correct = selected == question["answer"]
    answers.append({"questionId": question_id, "selected": selected, "selectedText": question["options"][selected],
                    "correct": correct, "seconds": seconds, "method": question["method"],
                    "questionForm": question.get("questionForm", "calculation"),
                    "strategy": question.get("strategy", ""),
                    "correctOption": question["answer"]})
    row.answers_json = json.dumps(answers, ensure_ascii=False)
    db.commit()
    return {"correct": correct, "correctOption": question["options"][question["answer"]], "steps": question["steps"], "pitfall": question["pitfall"],
            "optionFeedback": ["该计算成立" if value else "该计算不成立" for value in question.get("claims", [])]}


def complete_session(db: Session, user_id: str, session_id: str, total_seconds: int) -> dict | None:
    row = db.get(ZiliaoQuickSession, session_id)
    if not row or row.user_id != user_id:
        return None
    if row.status != "completed":
        answers = _json(row.answers_json, [])
        if not answers:
            raise ValueError("本组尚无已作答题目")
        row.status = "completed"; row.total_seconds = total_seconds; row.completed_at = now()
        db.commit()
        record_event(db, user_id, "quick_calc_done", {"sessionId": row.id, "mode": row.mode,
            "total": len(answers), "correct": sum(1 for a in answers if a["correct"])}, commit=True)
    answers = _json(row.answers_json, [])
    return {"sessionId": row.id, "total": len(answers), "correct": sum(1 for a in answers if a["correct"]),
            "seconds": row.total_seconds, "completed": row.status == "completed"}


def analytics(db: Session, days: int = 30) -> dict:
    since = now() - timedelta(days=max(1, min(365, days)))
    sessions = db.query(ZiliaoQuickSession).filter(ZiliaoQuickSession.created_at >= since,
        ZiliaoQuickSession.status == "completed").all()
    by_method: dict[str, dict] = {}
    for session in sessions:
        for answer in _json(session.answers_json, []):
            concept = LEGACY_TO_CONCEPT.get(answer["method"], answer["method"])
            item = by_method.setdefault(concept, {"method": concept, "attempts": 0, "correct": 0,
                "seconds": 0, "wrongOptions": {}, "strategyCounts": {}, "formCounts": {}, "formStats": {}})
            item["attempts"] += 1; item["correct"] += int(answer["correct"]); item["seconds"] += answer["seconds"]
            strategy = answer.get("strategy") or (answer["method"] if answer["method"] in LEGACY_COMPARE_CODES else "")
            if strategy:
                label = COMPARE_STRATEGIES.get(strategy, (strategy, ""))[0]
                item["strategyCounts"][label] = item["strategyCounts"].get(label, 0) + 1
            form = answer.get("questionForm") or "calculation"
            form_label = FORM_LABELS.get(form, form)
            item["formCounts"][form_label] = item["formCounts"].get(form_label, 0) + 1
            form_stat = item["formStats"].setdefault(form_label, {"attempts": 0, "correct": 0, "seconds": 0})
            form_stat["attempts"] += 1
            form_stat["correct"] += int(answer["correct"])
            form_stat["seconds"] += answer["seconds"]
            if not answer["correct"]:
                wrong_key = str(answer.get("selectedText", answer["selected"]))
                item["wrongOptions"][wrong_key] = item["wrongOptions"].get(wrong_key, 0) + 1
    methods = {m["code"]: m["name"] for m in list_methods(db)}
    methods["mixed"] = "综合材料辨析"
    rows = []
    for code, item in by_method.items():
        item["name"] = methods.get(code, code)
        item["accuracy"] = round(item["correct"] * 100 / item["attempts"], 1) if item["attempts"] else 0
        item["averageSeconds"] = round(item["seconds"] / item["attempts"], 1) if item["attempts"] else 0
        item["formPerformance"] = {
            form: {
                "attempts": stats["attempts"],
                "accuracy": round(stats["correct"] * 100 / stats["attempts"], 1) if stats["attempts"] else 0,
                "averageSeconds": round(stats["seconds"] / stats["attempts"], 1) if stats["attempts"] else 0,
            }
            for form, stats in item["formStats"].items()
        }
        del item["formStats"]
        rows.append(item)
    return {"days": days, "sessions": len(sessions), "attempts": sum(x["attempts"] for x in rows),
            "methods": sorted(rows, key=lambda x: x["method"])}


def user_history(db: Session, user_id: str, limit: int = 10) -> dict:
    rows = (db.query(ZiliaoQuickSession).filter_by(user_id=user_id, status="completed")
            .order_by(ZiliaoQuickSession.completed_at.desc()).limit(max(1, min(30, limit))).all())
    result = []; by_method: dict[str, dict[str, int]] = {}
    for row in rows:
        answers = _json(row.answers_json, [])
        result.append({"id": row.id, "mode": LEGACY_TO_CONCEPT.get(row.mode, row.mode), "date": row.completed_at.isoformat() if row.completed_at else "",
                       "correct": sum(1 for a in answers if a["correct"]), "total": len(answers),
                       "seconds": row.total_seconds})
        for answer in answers:
            concept = LEGACY_TO_CONCEPT.get(answer["method"], answer["method"])
            item = by_method.setdefault(concept, {"attempts": 0, "correct": 0})
            item["attempts"] += 1; item["correct"] += int(answer["correct"])
    method_names = {m["code"]: m["name"] for m in list_methods(db, published_only=True)}
    recommendations = []
    for code, item in by_method.items():
        if item["attempts"] >= 5:
            accuracy = round(item["correct"] * 100 / item["attempts"], 1)
            if accuracy < 75 and code in method_names:
                recommendations.append({"code": code, "name": method_names[code], "accuracy": accuracy, "attempts": item["attempts"]})
    recommendations.sort(key=lambda x: (x["accuracy"], -x["attempts"]))
    return {"sessions": result, "recommendations": recommendations[:3]}


def retry_wrong(db: Session, user_id: str, session_id: str, question_ids: list[str]) -> dict | None:
    source = db.get(ZiliaoQuickSession, session_id)
    if not source or source.user_id != user_id or source.status != "completed":
        return None
    questions = _json(source.questions_json, [])
    answers = _json(source.answers_json, [])
    wrong_ids = {a["questionId"] for a in answers if not a["correct"]}
    requested = set(question_ids) & wrong_ids
    selected = [q for q in questions if q["id"] in requested]
    if not selected:
        raise ValueError("未找到可重练的错题")
    row = ZiliaoQuickSession(id=gen_id("zqs"), user_id=user_id, mode="retry",
        method_versions_json=source.method_versions_json, questions_json=json.dumps(selected, ensure_ascii=False),
        answers_json="[]", status="active")
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "mode": "retry", "questions": [_safe_question(q) for q in selected]}
