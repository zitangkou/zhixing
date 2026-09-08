"""爬虫入库前过滤（政考向）"""

from __future__ import annotations

TITLE_INCLUDE = (
    "规划", "纲要", "意见", "决定", "条例", "讲话", "论述", "解读", "要点",
    "精神", "部署", "改革", "现代化", "理论", "思想", "政策",
)

TITLE_EXCLUDE = (
    "图集", "图片", "视频", "图解", "快讯", "人事", "任免", "通报",
    "一图读懂", "短视频",
)

MIN_CONTENT_LENGTH = 400


def should_keep_article(title: str, content: str) -> tuple[bool, str]:
    title = (title or "").strip()
    content = (content or "").strip()

    if not title:
        return False, "标题为空"

    for kw in TITLE_EXCLUDE:
        if kw in title:
            return False, f"标题含排除词「{kw}」"

    if len(content) < MIN_CONTENT_LENGTH:
        return False, f"正文过短（{len(content)}<{MIN_CONTENT_LENGTH}）"

    if any(kw in title for kw in TITLE_INCLUDE):
        return True, "标题命中白名单"

    # 正文含多个政治理论关键词也可保留
    body_hits = sum(1 for kw in TITLE_INCLUDE if kw in content)
    if body_hits >= 2:
        return True, "正文命中关键词"

    return False, "未命中标题/正文过滤规则"
