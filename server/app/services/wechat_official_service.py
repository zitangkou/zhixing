"""杜衡阁公众号基础回调：验签、明文消息解析和确定性回复。"""
from __future__ import annotations

import hashlib
import hmac
import re
import threading
import time
import xml.etree.ElementTree as ET
from copy import deepcopy
from collections import OrderedDict
from dataclasses import dataclass
from urllib.parse import urlsplit


MAX_XML_BYTES = 64 * 1024
DEDUP_TTL_SECONDS = 300
DEDUP_MAX_ITEMS = 2048

FIFTEEN_FIVE_SHARE_REPLY = (
    "杜衡阁《十五五规划纲要全篇重点题汇总（360题）》资料\n\n"
    "我用夸克网盘给你分享了「杜衡阁_十五五规划纲要全篇重点题汇总_360题.pdf」，"
    "点击链接或复制整段内容，打开「夸克网盘APP」即可获取。\n\n"
    "提取口令：/~46b63bJJFJ~:/\n"
    "链接：https://pan.quark.cn/s/06e4e47206f9\n\n"
    "资料为依据《十五五规划纲要》整理的模拟练习，不是官方真题。"
)

DEFAULT_REPLY_CONFIG = {
    "welcomeReply": (
        "欢迎来到「杜衡阁」\n\n"
        "把重要文章读懂，把关键题目练会。\n\n"
        "1  今日学习\n"
        "2  时政练习\n"
        "3  时评精拆\n\n"
        "回复数字即可进入，回复 0 查看导航。\n"
        "回复「十五五」获取规划纲要360题资料。"
    ),
    "fallbackReply": (
        "暂时没有识别这个问题。\n\n"
        "回复 1 开始今日学习，回复 0 查看学习导航，回复「十五五」获取规划纲要360题资料。"
    ),
    "unsupportedMessageReply": "暂时只能识别文字消息。\n\n回复 0 查看学习导航。",
    "unsupportedEventReply": "已收到。\n\n回复 0 查看学习导航。",
    "keywordRules": [
        {
            "id": "today",
            "name": "今日学习",
            "keywords": ["1", "今日", "今天", "今日学习", "今日一练"],
            "matchType": "exact",
            "responseText": (
                "杜衡阁｜今日学习\n\n今日文章：时评与时政按日期排列，点开即读。\n\n"
                "进入学习\n{{today_url}}\n\n回复 0 返回学习导航。"
            ),
            "enabled": True,
            "priority": 100,
        },
        {
            "id": "theory",
            "name": "时政练习",
            "keywords": ["2", "时政", "日知", "时政学习", "时政阅读", "时政练习", "练习", "考点练习"],
            "matchType": "exact",
            "responseText": (
                "杜衡阁｜时政练习\n\n学习路径\n阅读全文 → 考点练习\n\n"
                "进入学习\n{{theory_url}}\n\n回复 0 返回学习导航。"
            ),
            "enabled": True,
            "priority": 100,
        },
        {
            "id": "rmrb",
            "name": "时评精拆",
            "keywords": ["3", "时评", "申论", "策论", "申论学习", "三刀", "时评精拆", "评论"],
            "matchType": "exact",
            "responseText": (
                "杜衡阁｜时评精拆\n\n学习路径\n读原文 → 时评解析 → 去开采\n\n"
                "进入学习\n{{rmrb_url}}\n\n回复 0 返回学习导航。"
            ),
            "enabled": True,
            "priority": 100,
        },
        {
            "id": "fifteen_five",
            "name": "十五五规划资料",
            "keywords": ["十五五", "十五五规划", "十五五规划纲要", "十五五资料", "十五五规划资料", "规划纲要资料"],
            "matchType": "exact",
            "responseText": FIFTEEN_FIVE_SHARE_REPLY,
            "enabled": True,
            "priority": 100,
        },
        {
            "id": "menu",
            "name": "学习导航",
            "keywords": ["0", "菜单", "帮助", "导航", "开始"],
            "matchType": "exact",
            "responseText": (
                "杜衡阁｜学习导航\n\n"
                "1  今日学习\n"
                "2  时政练习\n"
                "3  时评精拆\n\n"
                "回复数字即可进入。\n"
                "回复「十五五」获取规划纲要360题资料。\n"
                "每次只选一个任务，完成后再继续。"
            ),
            "enabled": True,
            "priority": 100,
        },
    ],
}


def default_reply_config() -> dict:
    return deepcopy(DEFAULT_REPLY_CONFIG)


@dataclass(frozen=True)
class InboundMessage:
    to_user: str
    from_user: str
    create_time: str
    msg_type: str
    content: str = ""
    event: str = ""
    event_key: str = ""
    msg_id: str = ""


@dataclass(frozen=True)
class ReplyDecision:
    intent: str
    text: str | None
    matched_rule_id: str = ""


_dedup_lock = threading.Lock()
_dedup_cache: OrderedDict[str, tuple[float, ReplyDecision]] = OrderedDict()


def verify_signature(token: str, signature: str, timestamp: str, nonce: str) -> bool:
    if not token or not signature or not timestamp or not nonce:
        return False
    digest = hashlib.sha1("".join(sorted((token, timestamp, nonce))).encode("utf-8")).hexdigest()
    return hmac.compare_digest(digest, signature)


def parse_message(raw: bytes) -> InboundMessage:
    if not raw or len(raw) > MAX_XML_BYTES:
        raise ValueError("消息正文为空或超过限制")
    upper = raw[:1024].upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("消息正文包含不允许的 XML 声明")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("消息 XML 无法解析") from exc

    def value(name: str) -> str:
        node = root.find(name)
        return (node.text or "").strip() if node is not None else ""

    message = InboundMessage(
        to_user=value("ToUserName"),
        from_user=value("FromUserName"),
        create_time=value("CreateTime"),
        msg_type=value("MsgType").lower(),
        content=value("Content"),
        event=value("Event").lower(),
        event_key=value("EventKey"),
        msg_id=value("MsgId"),
    )
    if not message.to_user or not message.from_user or not message.msg_type:
        raise ValueError("消息缺少必要字段")
    return message


def normalise_text(text: str) -> str:
    text = text.strip().lower()
    return re.sub(r"[\s，。！？、,.!?：:；;‘’“”「」『』\"'（）()【】\[\]]+", "", text)


_normalise_text = normalise_text


def _link(base_url: str, path: str) -> str:
    base = base_url.strip().rstrip("/")
    if not base:
        return ""
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{base}{path}"


def _with_link(title: str, description: str, url: str) -> str:
    if not url:
        return f"杜衡阁｜{title}\n\n{description}\n\n入口正在配置中。\n回复 0 返回学习导航。"
    return f"杜衡阁｜{title}\n\n{description}\n\n进入学习\n{url}\n\n回复 0 返回学习导航。"


def _render_reply_template(text: str, public_base_url: str) -> str:
    urls = {
        "{{today_url}}": _link(public_base_url, "/#/pages/index/index"),
        "{{theory_url}}": _link(public_base_url, "/#/pages/question/article-pick"),
        "{{rmrb_url}}": _link(public_base_url, "/#/pages/rmrb/article-list"),
    }
    for token, url in urls.items():
        text = text.replace(token, url or "入口正在配置中")
    return text


def decide_reply(
    message: InboundMessage,
    public_base_url: str,
    config: dict | None = None,
) -> ReplyDecision:
    reply_config = config or DEFAULT_REPLY_CONFIG

    if message.msg_type == "event":
        if message.event == "subscribe":
            return ReplyDecision("subscribe", _render_reply_template(reply_config["welcomeReply"], public_base_url))
        if message.event == "unsubscribe":
            return ReplyDecision("unsubscribe", None)
        return ReplyDecision(
            "unsupported_event",
            _render_reply_template(reply_config["unsupportedEventReply"], public_base_url),
        )

    if message.msg_type != "text":
        return ReplyDecision(
            "unsupported_message",
            _render_reply_template(reply_config["unsupportedMessageReply"], public_base_url),
        )

    text = normalise_text(message.content)
    rules = [rule for rule in reply_config.get("keywordRules", []) if rule.get("enabled", True)]
    matches: list[tuple[int, int, int, dict]] = []
    for rule_index, rule in enumerate(rules):
        match_type = rule.get("matchType", "exact")
        for keyword in rule.get("keywords", []):
            normalized_keyword = normalise_text(str(keyword))
            if not normalized_keyword:
                continue
            matched = text == normalized_keyword if match_type == "exact" else normalized_keyword in text
            if matched:
                # 精确匹配优先；其余按配置优先级和关键词长度稳定排序。
                matches.append((0 if match_type == "exact" else 1, -int(rule.get("priority", 0)), -len(normalized_keyword), rule))
                break
    if matches:
        matches.sort(key=lambda item: (item[0], item[1], item[2], item[3].get("id", "")))
        rule = matches[0][3]
        return ReplyDecision(
            str(rule.get("id", "keyword")),
            _render_reply_template(str(rule.get("responseText", "")), public_base_url),
            str(rule.get("id", "")),
        )
    return ReplyDecision("fallback", _render_reply_template(reply_config["fallbackReply"], public_base_url))


def message_key(message: InboundMessage) -> str:
    if message.msg_id:
        return f"msg:{message.msg_id}"
    material = "|".join(
        (message.from_user, message.create_time, message.msg_type, message.event, message.event_key, message.content)
    )
    return "event:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def decide_reply_once(
    message: InboundMessage,
    public_base_url: str,
    config: dict | None = None,
    cache_namespace: str = "",
) -> ReplyDecision:
    key = f"{cache_namespace}:{message_key(message)}" if cache_namespace else message_key(message)
    now = time.monotonic()
    with _dedup_lock:
        expired = [cached_key for cached_key, (deadline, _) in _dedup_cache.items() if deadline <= now]
        for cached_key in expired:
            _dedup_cache.pop(cached_key, None)
        cached = _dedup_cache.get(key)
        if cached:
            _dedup_cache.move_to_end(key)
            return cached[1]
        decision = decide_reply(message, public_base_url, config)
        _dedup_cache[key] = (now + DEDUP_TTL_SECONDS, decision)
        while len(_dedup_cache) > DEDUP_MAX_ITEMS:
            _dedup_cache.popitem(last=False)
        return decision


def build_text_reply(message: InboundMessage, text: str, timestamp: int | None = None) -> bytes:
    root = ET.Element("xml")
    ET.SubElement(root, "ToUserName").text = message.from_user
    ET.SubElement(root, "FromUserName").text = message.to_user
    ET.SubElement(root, "CreateTime").text = str(timestamp or int(time.time()))
    ET.SubElement(root, "MsgType").text = "text"
    ET.SubElement(root, "Content").text = text
    return ET.tostring(root, encoding="utf-8", xml_declaration=False)


def clear_dedup_cache() -> None:
    """仅用于测试隔离。"""
    with _dedup_lock:
        _dedup_cache.clear()
