"""杜衡阁推广配置：文本回复与受控小程序页面说明，不调用微信菜单或客服接口。"""
from copy import deepcopy

ENTRY_PATHS = {
    "home": "pages/index/index",
    "practice": "pages/question/article-pick",
    "quotes": "pages/quotes/index",
    "shenlun": "pages/rmrb/exercise-list",
    "quick_calc": "pages/ziliao/quick-calc",
    "knowledge": "pages/knowledge/index",
    "feedback": "pages/user/feedback",
}


def promotion_entries() -> list[dict]:
    names = {"home": "首页", "practice": "每日练习", "quotes": "金句素材", "shenlun": "申论练习", "quick_calc": "速算训练", "knowledge": "知识框架", "feedback": "问题反馈"}
    return [dict(id=key, name=name, pagePath=ENTRY_PATHS[key], enabled=True,
                 instruction=f"在微信搜索小程序「杜衡阁」，进入「{name}」。" if key != "home" else "在微信搜索小程序「杜衡阁」，打开即可开始学习。",
                 fallbackText="在微信搜索小程序「杜衡阁」，从首页选择可用功能。")
            for key, name in names.items()]


def promotion_config(current: dict) -> dict:
    """显式导入草稿；保留专项资料、未知自定义规则和已有入口配置。"""
    from app.services.wechat_official_service import normalise_text

    result = deepcopy(current)
    entries = {entry["id"]: entry for entry in promotion_entries()}
    entries.update({entry["id"]: entry for entry in current.get("promotionEntries", [])})
    result["promotionEntries"] = list(entries.values())
    specs = [
        ("miniapp", "打开小程序", ["小程序", "杜衡阁", "进入小程序", "打开小程序"], "杜衡阁小程序已上线。\n\n练题、积累金句、练申论、练速算、梳理知识，从一次学习开始。", "home"),
        ("today", "每日练习", ["练题", "每日练习", "今日", "今天", "今日学习", "今日一练", "1"], "今天先完成一组练习。\n\n选择一组题，作答后查看解析。", "practice"),
        ("theory", "专题练习", ["时政", "时政练习", "时政学习", "时政阅读", "日知", "考点练习", "专题", "专题练习", "练习", "2"], "把读过的要点，变成一次练习。\n\n选择已发布的练习题，做完再看解析。", "practice"),
        ("quotes", "金句素材", ["金句", "金句素材", "每日金句", "作文金句"], "好句子，记住以后还要会用。\n\n查看已整理的句子，挑一句用于今天的表达练习。", "quotes"),
        ("shenlun", "申论练习", ["申论", "申论练习", "申论学习", "策论"], "申论积累之后，再动笔练一题。\n\n选择已发布题目，先作答，再对照参考要点与解析订正。系统不提供自动评分。", "shenlun"),
        ("rmrb", "旧时评入口", ["时评", "时评精拆", "三刀", "评论", "3"], "你可以在杜衡阁继续进行申论学习，先选一道题动笔，再对照参考要点订正。", "shenlun"),
        ("quick_calc", "速算训练", ["速算", "资料分析", "速算训练", "计算练习"], "资料分析，先把计算练熟。\n\n选择当前开放的训练，做完一组再看解析。", "quick_calc"),
        ("knowledge", "知识框架", ["框架", "知识框架", "知识点"], "知识点零散时，先看看它们的关系。\n\n选择要复习的主题，按结构梳理。", "knowledge"),
        ("materials", "资料导航", ["资料", "领资料", "资料领取"], "目前可领取：\n回复「十五五」获取规划纲要360题资料。\n\n想直接练题，可回复「练题」。", ""),
        ("menu", "学习导航", ["0", "菜单", "帮助", "导航", "开始"], "杜衡阁｜学习导航\n\n「小程序」打开杜衡阁\n「练题」每日练习\n「金句」积累表达\n「申论」动笔练习\n「速算」计算训练\n「框架」梳理知识\n「资料」领取资料\n\n回复对应关键词即可。先选一项，完成一次学习。", ""),
        ("feedback", "使用反馈", ["反馈", "使用问题", "打不开", "小程序打不开"], "请在微信搜索小程序「杜衡阁」。若仍无法使用，可稍后重试；进入后在「我的」中提交问题反馈，并说明具体页面和现象。", ""),
    ]
    replacements = [dict(id=key, name=name, keywords=words, matchType="exact", responseText=text, entryId=entry, enabled=True, priority=100) for key, name, words, text, entry in specs]
    # 保留内置规则上人工添加的别名；规范词重新分流（如申论）以新版归属为准。
    claimed = {normalise_text(word) for rule in replacements for word in rule["keywords"]}
    old_rules = {rule.get("id"): rule for rule in current.get("keywordRules", [])}
    for rule in replacements:
        for word in old_rules.get(rule["id"], {}).get("keywords", []):
            if normalise_text(word) not in claimed:
                rule["keywords"].append(word)
                claimed.add(normalise_text(word))
    replaced = {rule["id"] for rule in replacements}
    result["keywordRules"] = replacements + [rule for rule in result.get("keywordRules", []) if rule.get("id") not in replaced]
    result.update(welcomeReply="欢迎来到「杜衡阁」🌿\n读到好内容，顺手练起来。\n\n杜衡阁小程序已上线：练题、积累金句、练申论、练速算、梳理知识。\n\n在微信搜索小程序「杜衡阁」，先完成一次学习。\n\n回复「练题」「金句」「申论」获取使用说明；回复「资料」领资料，回复「菜单」看完整导航。",
                  fallbackReply="暂时没识别到对应入口。\n回复「小程序」查看杜衡阁打开方法，或回复「菜单」查看学习导航。",
                  unsupportedMessageReply="自动回复目前支持文字关键词。\n请发送「练题」「金句」「申论」或「菜单」。",
                  unsupportedEventReply="回复「菜单」查看学习导航，或在微信搜索小程序「杜衡阁」开始学习。")
    return result


def render_promotion_entry(config: dict, entry_id: str) -> str:
    if not entry_id:
        return ""
    entry = next((item for item in config.get("promotionEntries", []) if item.get("id") == entry_id), None)
    if entry is None:
        return "入口正在维护，请回复「菜单」查看其他学习方式。"
    return str(entry.get("instruction") if entry.get("enabled") else entry.get("fallbackText") or "入口正在维护，请回复「菜单」查看其他学习方式。")
