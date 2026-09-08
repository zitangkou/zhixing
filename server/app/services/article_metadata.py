"""从粘贴的正文推断文章元数据（标题、来源、标签、分类等）"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import Category

_URL_RE = re.compile(r"https?://[^\s<>\"'\)]+")
_DATE_PATTERNS = [
    re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})"),
]

_SOURCE_HINTS = [
    (("people.com.cn", "people.cn"), "人民日报"),
    (("xinhuanet.com", "news.cn"), "新华网"),
    (("qstheory.cn",), "求是网"),
    (("gov.cn",), "中国政府网"),
]

_TAG_RULES: list[tuple[list[str], str]] = [
    (["十五五", "十四五", "规划建议", "规划纲要"], "十五五规划"),
    (["新质生产力", "高质量发展", "现代化产业体系"], "新质生产力"),
    (["中国式现代化", "强国建设", "民族复兴"], "中国式现代化"),
    (["两个确立", "两个维护", "四个意识"], "政治术语"),
    (["法治", "宪法", "立法", "司法"], "法治"),
    (["党史", "革命", "建党", "长征"], "党史学习"),
    (["文化", "文明", "传统", "非遗"], "文化思想"),
    (["经济", "消费", "投资", "市场"], "时政要闻"),
]

_CATEGORY_RULES: list[tuple[list[str], list[str]]] = [
    (["党史", "革命", "建党", "长征", "红色"], ["党史", "党史事件", "党史学习"]),
    (["法治", "法律", "宪法", "立法", "司法", "检察"], ["法治", "政策法规"]),
    (["文化", "文明", "传统", "非遗", "文艺"], ["文化", "中华文明", "传统文化", "文化思想"]),
    (["十五五", "十四五", "规划", "现代化", "新质生产力", "高质量", "改革"], ["思想理论", "时政"]),
    (["外交", "国际", "全球", "一带一路"], ["时政", "时政要闻"]),
]

_HIGH_IMPORTANCE_KEYWORDS = [
    "十五五",
    "十四五",
    "根本保证",
    "两个确立",
    "中国式现代化",
    "新质生产力",
    "强国建设",
    "民族复兴",
]


def _today() -> str:
    from app.timezone import today as today_str

    return today_str()


def _normalize_text(text: str) -> str:
    return re.sub(r"\r\n?", "\n", text.strip())


def _split_paragraphs(content: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", content.strip())
    return [p.strip() for p in parts if len(p.strip()) > 8]


def split_title_and_content(text: str) -> tuple[str, str]:
    """首行像标题时拆出标题与正文"""
    text = _normalize_text(text)
    if not text:
        return "", ""

    lines = text.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return "", text

    first = re.sub(r"^【[^】]+】\s*", "", lines[0].strip())
    rest = "\n".join(lines[1:]).strip()

    looks_like_title = (
        4 <= len(first) <= 100
        and not first.endswith("。")
        and not first.endswith("！")
        and not first.endswith("？")
        and (rest or len(first) <= 60)
    )
    if looks_like_title and rest:
        return first, rest
    return "", text


def extract_source_url(text: str) -> str:
    urls = _URL_RE.findall(text)
    if not urls:
        return ""
    for url in urls:
        if "people.com.cn" in url or "people.cn" in url:
            return url.rstrip(".,;，。")
    return urls[0].rstrip(".,;，。")


def infer_source(text: str, source_url: str = "") -> str:
    haystack = f"{text}\n{source_url}".lower()
    for domains, name in _SOURCE_HINTS:
        if any(d in haystack for d in domains):
            return name
    if "人民日报" in text:
        return "人民日报"
    if "新华社" in text:
        return "新华网"
    return "手动录入"


def extract_publish_date(text: str) -> str:
    head = text[:800]
    for pattern in _DATE_PATTERNS:
        match = pattern.search(head)
        if match:
            y, m, d = match.groups()
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    return _today()


def extract_summary(content: str, title: str = "", max_len: int = 120) -> str:
    paragraphs = _split_paragraphs(content)
    for para in paragraphs:
        line = re.sub(r"\s+", "", para)
        if len(line) < 20:
            continue
        if title and line.startswith(title):
            line = line[len(title) :].lstrip("，。：: ")
        if len(line) >= 20:
            return line[:max_len] + ("…" if len(line) > max_len else "")
    plain = re.sub(r"\s+", "", content)
    return plain[:max_len] + ("…" if len(plain) > max_len else "")


def infer_tags(title: str, content: str, source: str) -> list[str]:
    text = f"{title}\n{content}"
    tags: list[str] = []
    if source and source != "手动录入":
        tags.append(source)
    tags.append("政治理论")

    for keywords, tag in _TAG_RULES:
        if any(kw in text for kw in keywords) and tag not in tags:
            tags.append(tag)

    return tags[:8]


def _flatten_categories(db: Session) -> list[tuple[str, str, str]]:
    rows = db.query(Category).filter(Category.is_active.is_(True)).all()
    by_id = {row.id: row for row in rows}
    flat: list[tuple[str, str, str]] = []

    def walk(cat: Category) -> None:
        path_parts: list[str] = []
        current: Category | None = cat
        while current:
            path_parts.insert(0, current.name)
            current = by_id.get(current.parent_id) if current.parent_id else None
        flat.append((cat.id, cat.name, "/".join(path_parts)))

    for row in rows:
        walk(row)
    return flat


def infer_category_id(db: Session, title: str, content: str) -> tuple[str | None, str | None]:
    text = f"{title}\n{content}"
    categories = _flatten_categories(db)
    if not categories:
        return None, None

    best_id: str | None = None
    best_name: str | None = None
    best_score = 0

    for cat_id, cat_name, path in categories:
        score = 0
        for keywords, name_hints in _CATEGORY_RULES:
            if not any(kw in text for kw in keywords):
                continue
            if any(hint in cat_name or hint in path for hint in name_hints):
                score += 3
        if cat_name in text or any(part in text for part in path.split("/") if len(part) >= 2):
            score += 1
        if score > best_score:
            best_score = score
            best_id = cat_id
            best_name = cat_name

    if best_score <= 0:
        for cat_id, cat_name, _path in categories:
            if cat_name == "时政要闻":
                return cat_id, cat_name
        for cat_id, cat_name, _path in categories:
            if cat_name == "思想理论":
                return cat_id, cat_name
    return best_id, best_name


def infer_importance(title: str, content: str) -> int:
    text = f"{title}\n{content}"
    hits = sum(1 for kw in _HIGH_IMPORTANCE_KEYWORDS if kw in text)
    if hits >= 2 or any(k in title for k in ("全文", "重磅", "解读")):
        return 5
    if hits == 1:
        return 4
    return 3


def infer_article_metadata(
    db: Session,
    *,
    content: str,
    title: str = "",
) -> dict[str, Any]:
    """根据正文推断可自动填充的字段"""
    raw = _normalize_text(content)
    if not raw:
        return {
            "title": title.strip(),
            "content": "",
            "source": "手动录入",
            "source_url": "",
            "publish_date": _today(),
            "summary": "",
            "tags": ["政治理论"],
            "category_id": None,
            "category_name": None,
            "importance": 3,
        }

    parsed_title, body = split_title_and_content(raw)
    final_title = title.strip() or parsed_title or raw.split("\n", 1)[0].strip()[:100]
    final_content = body or raw
    source_url = extract_source_url(raw)
    source = infer_source(raw, source_url)
    category_id, category_name = infer_category_id(db, final_title, final_content)

    return {
        "title": final_title,
        "content": final_content,
        "source": source,
        "source_url": source_url,
        "publish_date": extract_publish_date(raw),
        "summary": extract_summary(final_content, final_title),
        "tags": infer_tags(final_title, final_content, source),
        "category_id": category_id,
        "category_name": category_name,
        "importance": infer_importance(final_title, final_content),
    }


def merge_article_fields(
    db: Session,
    *,
    title: str,
    source: str,
    source_url: str,
    publish_date: str,
    summary: str,
    content: str,
    tags: list[str],
    category_id: str | None,
    importance: int,
) -> dict[str, Any]:
    """用推断结果补全空缺字段（创建/保存时使用）"""
    inferred = infer_article_metadata(db, content=content, title=title)
    merged_content = content.strip() or inferred["content"]

    def pick(current: str, key: str, *, ignore: set[str] | None = None) -> str:
        value = (current or "").strip()
        if value and (not ignore or value not in ignore):
            return value
        return str(inferred.get(key) or "").strip()

    merged_title = pick(title, "title")
    merged_source = pick(source, "source", ignore={"手动录入"})
    merged_source_url = pick(source_url, "source_url")
    merged_publish_date = pick(publish_date, "publish_date")
    merged_summary = pick(summary, "summary")
    merged_tags = tags if tags else inferred["tags"]
    merged_category_id = category_id or inferred.get("category_id")
    merged_importance = inferred["importance"] if importance == 3 else importance

    if not merged_title and merged_content:
        merged_title = merged_content.split("\n", 1)[0].strip()[:100]

    if not merged_summary and merged_content:
        merged_summary = extract_summary(merged_content, merged_title)

    return {
        "title": merged_title,
        "source": merged_source or "手动录入",
        "source_url": merged_source_url,
        "publish_date": merged_publish_date or _today(),
        "summary": merged_summary or merged_title[:120],
        "content": merged_content,
        "tags": merged_tags,
        "category_id": merged_category_id,
        "importance": merged_importance,
    }
