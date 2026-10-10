"""人民日报客户端网页首屏列表解析。失败时由上层降级，不阻断电子报采集。"""
from datetime import date, datetime, timedelta
import re
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

BEIJING = ZoneInfo("Asia/Shanghai")
USER_AGENT = "Mozilla/5.0 (compatible; ZhixingRmrbArchive/1.0)"
PEOPLEAPP_CHANNELS = {
    "peopleapp_home": "https://www.peopleapp.com/home",
    "peopleapp_opinion": "https://www.peopleapp.com/opinion?param1=2003&param2=2",
}


def _decode_nuxt_payload(payload):
    cache = {}

    def resolve(value, stack=()):
        if isinstance(value, bool) or not isinstance(value, int):
            return value
        if value < 0 or value >= len(payload) or value in stack:
            return None
        if value in cache:
            return cache[value]
        node = payload[value]
        if isinstance(node, dict):
            result = {key: resolve(child, stack + (value,)) for key, child in node.items()}
            cache[value] = result
            return result
        if isinstance(node, list):
            if node and isinstance(node[0], str) and node[0] in {"Reactive", "ShallowReactive", "Ref", "ShallowRef"}:
                return resolve(node[1], stack + (value,))
            result = [resolve(child, stack + (value,)) for child in node]
            cache[value] = result
            return result
        return node

    return resolve(0)


def _parse_publish_datetime(raw_time) -> datetime | None:
    """Parse PeopleApp publishTime as Beijing time; do not substitute createTime."""
    if raw_time in (None, ""):
        return None
    try:
        timestamp = float(raw_time)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, BEIJING)
    except (TypeError, ValueError, OSError, OverflowError):
        pass
    try:
        value = datetime.fromisoformat(str(raw_time).strip().replace("Z", "+00:00"))
        return value.replace(tzinfo=BEIJING) if value.tzinfo is None else value.astimezone(BEIJING)
    except ValueError:
        return None


def fetch_channel_items(channel: str, window_start: datetime, window_end: datetime) -> list[dict]:
    """Fetch homepage/opinion articles published in the rolling 24-hour window.

    Bounds are explicit so both channels use the same collection window. Naive bounds
    are interpreted as Beijing local time for compatibility with callers.
    """
    url = PEOPLEAPP_CHANNELS[channel]
    if window_start.tzinfo is None:
        window_start = window_start.replace(tzinfo=BEIJING)
    else:
        window_start = window_start.astimezone(BEIJING)
    if window_end.tzinfo is None:
        window_end = window_end.replace(tzinfo=BEIJING)
    else:
        window_end = window_end.astimezone(BEIJING)
    if window_end <= window_start or window_end - window_start > timedelta(hours=24):
        raise ValueError("采集时间范围必须大于 0 且不超过 24 小时")
    response = httpx.get(url, timeout=25, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    state_tag = soup.find("script", id="__NUXT_DATA__")
    if state_tag is None or not state_tag.string:
        raise RuntimeError("页面未找到 Nuxt 服务端文章数据")
    import json

    state = _decode_nuxt_payload(json.loads(state_tag.string))
    candidates = []

    def walk(value):
        if isinstance(value, dict):
            if value.get("objectId") and value.get("newsTitle"):
                candidates.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(state)
    items = {}
    for item in candidates:
        object_id = str(item.get("objectId", "")).strip()
        relation_id = str(item.get("relId", "")).strip()
        title = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(item.get("newsTitle", ""))).strip()
        if not object_id or not relation_id or not title:
            continue
        source_url = f"https://www.peopleapp.com/column/{object_id}-{relation_id}"
        raw_time = item.get("publishTime")
        published_at = _parse_publish_datetime(raw_time)
        if published_at is None:
            # 只按明确的发布日期入库；createTime 不能替代发布日期。
            continue
        if not (window_start <= published_at <= window_end):
            continue
        authors = item.get("authorList") or []
        author_line = "、".join(str(author.get("authorName", "")).strip() for author in authors if isinstance(author, dict) and author.get("authorName"))
        key = source_url
        items.setdefault(key, {
            "title": title,
            "url": source_url,
            "issue_date": published_at.date(),
            "publication_time": str(item.get("publishTime") or ""),
            "author_line": author_line,
            "channel": channel,
        })
    return list(items.values())
