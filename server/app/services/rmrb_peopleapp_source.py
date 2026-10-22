"""人民日报客户端评论频道分页解析。失败时由上层降级，不阻断电子报采集。"""
from datetime import date, datetime, timedelta
import re
from zoneinfo import ZoneInfo
from urllib.parse import parse_qs, urlparse

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
    """Fetch homepage/opinion articles published in the rolling 48-hour window.

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
    if window_end <= window_start or window_end - window_start > timedelta(hours=48):
        raise ValueError("采集时间范围必须大于 0 且不超过 48 小时")
    response = httpx.get(url, timeout=25, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    state_tag = soup.find("script", id="__NUXT_DATA__")
    if state_tag is None or not state_tag.string:
        raise RuntimeError("页面未找到 Nuxt 服务端文章数据")
    import json

    state = _decode_nuxt_payload(json.loads(state_tag.string))

    # 评论页 SSR 只带首屏10条。客户端使用同一 compInfo 接口分页，需逐页
    # 读到发布时间早于窗口起点，否则“最近24/48小时”实际上只是首屏采集。
    # AppCode 是页面公开运行配置，动态读取以兼容版本轮换，不写入仓库。
    if channel == "peopleapp_opinion":
        app_code_match = re.search(r'VITE_APP_CODE:"([^"\\]+)', response.text)
        stage_match = re.search(r'VITE_X_CA_STAGE:"([^"\\]+)', response.text)
        query = parse_qs(urlparse(url).query)
        channel_id = (query.get("param1") or [None])[0]
        channel_strategy = (query.get("param2") or [None])[0]
        if not (app_code_match and stage_match and channel_id and channel_strategy):
            raise RuntimeError("评论页分页配置未识别")
        api_url = "https://www.peopleapp.com/api/rmrb-bff-display-zh/display/zh/c/pc/compInfo"
        api_headers = {
            "User-Agent": USER_AGENT,
            "Authorization": f"AppCode {app_code_match.group(1)}",
            "X-Ca-Stage": stage_match.group(1),
            "plat": "web",
            "system": "PC",
            "versionCode": "7422",
            "Referer": url,
        }
        # 该频道接口 pageSize 上限为20，超过上限会返回业务码0000400。
        page_size = 20
        page_num = 1
        total_count = None
        refresh_time = None
        paged_candidates = []
        max_pages = 100  # 仅扫描截至窗口边界的近期页，异常排序时设硬上限。
        while page_num <= max_pages:
            params = {"channelId": channel_id, "channelStrategy": channel_strategy,
                      "pageNum": page_num, "pageSize": page_size}
            if refresh_time is not None:
                params["refreshTime"] = refresh_time
            page_response = httpx.get(api_url, params=params, timeout=25,
                                      headers=api_headers, follow_redirects=True)
            page_response.raise_for_status()
            try:
                payload = page_response.json()
            except ValueError as exc:
                raise RuntimeError("评论页分页接口返回格式异常") from exc
            if str(payload.get("code")) != "0" or not isinstance(payload.get("data"), dict):
                raise RuntimeError("评论页分页接口未返回文章目录")
            data = payload["data"]
            page_items = data.get("list") if isinstance(data.get("list"), list) else []
            if total_count is None:
                total_count = int(data.get("totalCount") or 0)
                refresh_time = data.get("refreshTime")
            if not page_items:
                break
            # 与评论页前端一致，排除仅用于版式展示的 appStyle=27 条目。
            paged_candidates.extend(item for item in page_items
                                    if isinstance(item, dict) and str(item.get("appStyle")) != "27")
            times = [_parse_publish_datetime(item.get("publishTime")) for item in page_items]
            valid_times = [value for value in times if value]
            # 频道按发布时间倒序。整页已早于窗口且至少已取到第一页后即可结束。
            if valid_times and max(valid_times) < window_start:
                break
            if page_num * page_size >= total_count:
                break
            page_num += 1
        if page_num > max_pages:
            raise RuntimeError("评论页分页超过安全扫描上限")
        state = {"pagedArticles": paged_candidates}
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
