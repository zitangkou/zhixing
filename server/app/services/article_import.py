"""从结构化 Markdown 导入长文（章 → 节 → 段，与移动端 level 1/2/3 一致）"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.section_parser import _extract_highlight, sections_to_content

_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
_CHAPTER_PREFIX_RE = re.compile(r"^(第[一二三四五六七八九十百零\d]+章)\s*(.*)$")
_SECTION_PREFIX_RE = re.compile(r"^(第[一二三四五六七八九十百零\d]+节)\s*(.*)$")
_BOLD_ITEM_RE = re.compile(r"^\*\*(.+?)\*\*[。．]?\s*(.*)$", re.S)
_PART_PREFIX_RE = re.compile(r"^第[一二三四五六七八九十百零\d]+编")
_KEYWORD_HEADING_RE = re.compile(r"^\*{0,2}【关键词】\*{0,2}\s*(.*)$")
_META_RE = re.compile(
    r"^\*{0,2}\s*(来源|日期|原文链接|链接)\*{0,2}\s*[：:]\s*(.+)$"
)
_TITLE_DECORATION_RE = re.compile(
    r"[（(](?:三章结构(?:[·•．.]?关键词)?版|关键词版)[）)]"
)


@dataclass
class _ImportNode:
    """level: 1=章 2=节 3=段（与移动端 ArticleSection 一致）"""
    level: int
    title: str
    content_parts: list[str] = field(default_factory=list)
    children: list[_ImportNode] = field(default_factory=list)
    raw_heading: str = ""
    highlight: str = ""


def _strip_quotes(text: str) -> str:
    return text.strip().strip("「」\"'“”")


def _clean_doc_title(title: str) -> str:
    cleaned = _TITLE_DECORATION_RE.sub("", title).strip()
    return cleaned or title.strip()


def _first_sentence(text: str, max_len: int = 80) -> str:
    plain = re.sub(r"\s+", "", text.strip())
    if not plain:
        return ""
    for sep in "。！？":
        idx = plain.find(sep)
        if 8 <= idx <= max_len:
            return plain[: idx + 1]
    return plain[:max_len] + ("…" if len(plain) > max_len else "")


def _positioning_sentence(text: str) -> str:
    sentence = _first_sentence(text, max_len=100)
    return sentence.rstrip("。！？") if sentence else ""


def _chapter_title(raw_heading: str, chapter_intro: str | None = None) -> str:
    heading = raw_heading.strip()
    match = _CHAPTER_PREFIX_RE.match(heading)
    if not match:
        return heading

    prefix, rest = match.groups()
    rest = rest.strip()
    if rest and len(rest) >= 4:
        return f"{prefix} {rest}".strip()

    if chapter_intro:
        pos = _positioning_sentence(chapter_intro)
        if pos:
            return f"{prefix} {pos}"
    return heading


def _section_title(raw_heading: str, content: str = "") -> str:
    heading = raw_heading.strip()
    match = _SECTION_PREFIX_RE.match(heading)
    if match:
        prefix, rest = match.groups()
        if rest.strip():
            return f"{prefix} {rest.strip()}".strip()
        if content:
            pos = _positioning_sentence(content)
            if pos:
                return f"{prefix} {pos}"
    if heading:
        return heading
    if content:
        return _positioning_sentence(content) or _first_sentence(content, 40)
    return "未命名节"


def _parse_paragraph_block(text: str) -> tuple[str, str]:
    text = text.strip()
    match = _BOLD_ITEM_RE.match(text)
    if match:
        title = match.group(1).strip().rstrip("。．")
        body = match.group(2).strip()
        full = f"{title}。{body}" if body else text
        return title, full

    title = _positioning_sentence(text) or _first_sentence(text, 36).rstrip("。！？")
    return title, text


def _join_content(parts: list[str]) -> str:
    return "\n\n".join(p.strip() for p in parts if p.strip()).strip()


def _join_quote_lines(lines: list[str]) -> str:
    return "".join(line.strip() for line in lines if line.strip())


def _normalize_keywords(text: str) -> str:
    parts = [p.strip() for p in re.split(r"[／/]", text) if p.strip()]
    return " / ".join(parts)


def _apply_meta(meta: dict[str, str], raw: str) -> bool:
    match = _META_RE.match(raw.strip())
    if not match:
        return False
    key, value = match.group(1), match.group(2).strip().strip("《》<>")
    if key == "来源":
        meta["source"] = value
    elif key == "日期":
        meta["publish_date"] = value
    else:
        meta["source_url"] = value
    return True


def _finalize_section_node(section: _ImportNode) -> None:
    """将节内多个引用块拆为 level-3 段，或合并为节正文"""
    parts = [p for p in section.content_parts if p.strip()]
    section.content_parts = []

    if not parts:
        return

    if len(parts) == 1:
        section.content_parts = parts
        return

    bold_parts = [p for p in parts if _BOLD_ITEM_RE.match(p.strip())]
    first_is_intro = bool(bold_parts) and len(bold_parts) < len(parts) and not _BOLD_ITEM_RE.match(parts[0].strip())

    start_idx = 1 if first_is_intro else 0
    if first_is_intro:
        section.content_parts = [parts[0]]

    for part in parts[start_idx:]:
        title, content = _parse_paragraph_block(part)
        section.children.append(
            _ImportNode(level=3, title=title, content_parts=[content], raw_heading=title)
        )

    if not section.children and len(parts) > 1:
        section.content_parts = parts


def _node_to_section(node: _ImportNode, node_id: str) -> dict[str, Any]:
    section: dict[str, Any] = {
        "id": node_id,
        "title": node.title,
        "level": node.level,
    }
    content = _join_content(node.content_parts)
    highlight = (node.highlight or "").strip()
    if content:
        section["content"] = content
        if not highlight:
            highlight = _extract_highlight(content) or ""
        if not highlight and node.level == 2 and len(content) <= 160:
            highlight = _first_sentence(content, 120)
    if highlight:
        section["highlight"] = highlight
    if node.children:
        section["children"] = [
            _node_to_section(child, f"{node_id}-{index + 1}")
            for index, child in enumerate(node.children)
        ]
    return section


def _count_nodes(nodes: list[_ImportNode]) -> dict[str, int]:
    stats = {"chapters": 0, "sections": 0, "paragraphs": 0}

    def walk(node: _ImportNode) -> None:
        if node.level == 1:
            stats["chapters"] += 1
        elif node.level == 2:
            stats["sections"] += 1
        elif node.level == 3:
            stats["paragraphs"] += 1
        for child in node.children:
            walk(child)

    for root in nodes:
        walk(root)
    return stats


def _detect_legacy_part_format(lines: list[str]) -> bool:
    has_part = False
    has_h4 = False
    for line in lines:
        match = _HEADING_RE.match(line.strip())
        if not match:
            continue
        depth = len(match.group(1))
        title = match.group(2).strip()
        if depth == 2 and _PART_PREFIX_RE.match(title):
            has_part = True
        if depth == 4:
            has_h4 = True
    return has_part and has_h4


class _LineParser:
    def __init__(self, lines: list[str], warnings: list[str], meta: dict[str, str]):
        self.lines = lines
        self.warnings = warnings
        self.meta = meta
        self.quote_buf: list[str] = []
        self.content_target: _ImportNode | None = None

    def flush_quote(self) -> None:
        if not self.quote_buf:
            return
        text = _join_quote_lines(self.quote_buf)
        self.quote_buf = []
        if not text:
            return
        if self.content_target is None:
            if not _apply_meta(self.meta, text):
                self.warnings.append("文首引用无法识别为来源/日期/链接，已忽略")
            return
        self.content_target.content_parts.append(text)

    def apply_keywords(self, raw: str) -> None:
        keywords = _normalize_keywords(raw)
        if not keywords:
            return
        target = self.content_target
        if target is None:
            self.warnings.append("关键词出现在标题之前，已忽略")
            return
        target.highlight = keywords

    def consume_keyword_followup(self, start_index: int) -> tuple[str, int]:
        collected: list[str] = []
        index = start_index
        while index < len(self.lines):
            peek = self.lines[index].rstrip()
            if not peek.strip():
                if collected:
                    break
                index += 1
                continue
            if _HEADING_RE.match(peek.strip()) or _BLOCKQUOTE_RE.match(peek):
                break
            kw_match = _KEYWORD_HEADING_RE.match(peek.strip())
            if kw_match:
                break
            collected.append(peek.strip())
            index += 1
            break
        return " ".join(collected), index


def _parse_legacy_part_format(
    lines: list[str], warnings: list[str], meta: dict[str, str]
) -> tuple[str, list[_ImportNode]]:
    """旧版三编结构：映射为 章(1) / 节(2)，编名写入章标题前缀"""
    doc_title = ""
    roots: list[_ImportNode] = []
    current_part_title = ""
    current_chapter: _ImportNode | None = None
    current_section: _ImportNode | None = None
    state = _LineParser(lines, warnings, meta)
    index = 0

    while index < len(lines):
        line = lines[index].rstrip()
        index += 1
        if not line.strip():
            state.flush_quote()
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            state.flush_quote()
            marks, heading_text = heading_match.groups()
            depth = len(marks)
            heading_text = heading_text.strip()

            if depth == 1:
                if not doc_title:
                    doc_title = _strip_quotes(heading_text)
                continue

            if depth == 2:
                if current_section:
                    _finalize_section_node(current_section)
                    current_section = None
                current_part_title = heading_text
                current_chapter = None
                state.content_target = None
                continue

            if depth == 3:
                if current_section:
                    _finalize_section_node(current_section)
                    current_section = None
                part_prefix = f"[{current_part_title}] " if current_part_title else ""
                current_chapter = _ImportNode(
                    level=1,
                    title=f"{part_prefix}{heading_text}",
                    raw_heading=heading_text,
                )
                roots.append(current_chapter)
                state.content_target = current_chapter
                continue

            if depth == 4:
                if not current_chapter:
                    warnings.append(f"第 {index} 行：节标题前缺少章，已跳过")
                    continue
                if current_section:
                    _finalize_section_node(current_section)
                current_section = _ImportNode(level=2, title=heading_text, raw_heading=heading_text)
                current_chapter.children.append(current_section)
                state.content_target = current_section
                continue
            continue

        quote_match = _BLOCKQUOTE_RE.match(line)
        if quote_match:
            text = quote_match.group(1).strip()
            if not text:
                state.flush_quote()
            else:
                if state.content_target is None and _apply_meta(meta, text):
                    continue
                state.quote_buf.append(text)
            continue

        kw_match = _KEYWORD_HEADING_RE.match(line.strip())
        if kw_match:
            state.flush_quote()
            rest = kw_match.group(1).strip()
            if not rest:
                follow, index = state.consume_keyword_followup(index)
                rest = follow
            state.apply_keywords(rest)
            continue

        state.flush_quote()
        warnings.append(f"第 {index} 行：无法识别的内容，已忽略")

    state.flush_quote()
    if current_section:
        _finalize_section_node(current_section)

    for chapter in roots:
        intro = _join_content(chapter.content_parts)
        chapter.title = _chapter_title(chapter.raw_heading, intro or None)
        for section in chapter.children:
            content = _join_content(section.content_parts)
            section.title = _section_title(section.raw_heading, content)

    return doc_title, roots


def _parse_chapter_section_format(
    lines: list[str], warnings: list[str], meta: dict[str, str]
) -> tuple[str, list[_ImportNode]]:
    doc_title = ""
    roots: list[_ImportNode] = []
    current_chapter: _ImportNode | None = None
    current_section: _ImportNode | None = None
    state = _LineParser(lines, warnings, meta)
    index = 0

    while index < len(lines):
        line = lines[index].rstrip()
        index += 1
        if not line.strip():
            state.flush_quote()
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            state.flush_quote()
            marks, heading_text = heading_match.groups()
            depth = len(marks)
            heading_text = heading_text.strip()

            if depth == 1:
                if not doc_title:
                    doc_title = _strip_quotes(heading_text)
                else:
                    warnings.append(f"第 {index} 行：忽略重复的文档标题")
                continue

            if depth == 2:
                if current_section:
                    _finalize_section_node(current_section)
                    current_section = None
                if current_chapter:
                    intro = _join_content(current_chapter.content_parts)
                    current_chapter.title = _chapter_title(current_chapter.raw_heading, intro or None)
                current_chapter = _ImportNode(level=1, title=heading_text, raw_heading=heading_text)
                roots.append(current_chapter)
                state.content_target = current_chapter
                continue

            if depth == 3:
                if not current_chapter:
                    warnings.append(f"第 {index} 行：节前缺少章标题，已自动创建默认章")
                    current_chapter = _ImportNode(level=1, title="正文", raw_heading="正文")
                    roots.append(current_chapter)
                if current_section:
                    _finalize_section_node(current_section)
                current_section = _ImportNode(level=2, title=heading_text, raw_heading=heading_text)
                current_chapter.children.append(current_section)
                state.content_target = current_section
                continue

            if depth == 4:
                warnings.append(f"第 {index} 行：请使用 ### 节 + 引用块分段，#### 标题已忽略")
                continue

            warnings.append(f"第 {index} 行：不支持的标题层级 {depth}")
            continue

        quote_match = _BLOCKQUOTE_RE.match(line)
        if quote_match:
            text = quote_match.group(1).strip()
            if not text:
                state.flush_quote()
                continue
            if state.content_target is None:
                if _apply_meta(meta, text):
                    continue
                state.quote_buf.append(text)
                continue
            state.quote_buf.append(text)
            continue

        kw_match = _KEYWORD_HEADING_RE.match(line.strip())
        if kw_match:
            state.flush_quote()
            rest = kw_match.group(1).strip()
            if not rest:
                follow, index = state.consume_keyword_followup(index)
                rest = follow
            state.apply_keywords(rest)
            continue

        state.flush_quote()
        warnings.append(f"第 {index} 行：无法识别的内容，已忽略")

    state.flush_quote()
    if current_section:
        _finalize_section_node(current_section)
    if current_chapter:
        intro = _join_content(current_chapter.content_parts)
        if intro and current_chapter.children:
            current_chapter.content_parts = []
        current_chapter.title = _chapter_title(current_chapter.raw_heading, intro or None)

    for chapter in roots:
        if chapter.raw_heading:
            chapter.title = _chapter_title(chapter.raw_heading, _join_content(chapter.content_parts) or None)
        for section in chapter.children:
            content = _join_content(section.content_parts)
            section.title = _section_title(section.raw_heading, content)

    return doc_title, roots


def parse_article_markdown(text: str) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    meta = {"source": "", "publish_date": "", "source_url": ""}
    lines = text.replace("\r\n", "\n").split("\n")

    if _detect_legacy_part_format(lines):
        warnings.append("检测到旧版「编-章-节」格式，已自动映射为移动端章-节结构")
        doc_title, roots = _parse_legacy_part_format(lines, warnings, meta)
    else:
        doc_title, roots = _parse_chapter_section_format(lines, warnings, meta)

    if not roots:
        raise ValueError(
            "未解析到章-节结构。请粘贴结构化 MD（# 标题、## 章、### 节，正文用 > 引用块），不要粘贴「原文素材」摘要稿。"
        )

    sections = [_node_to_section(chapter, f"ch{index + 1}") for index, chapter in enumerate(roots)]
    stats = _count_nodes(roots)
    content = sections_to_content(sections)
    summary = _first_sentence(content or doc_title, 120)

    if not doc_title:
        doc_title = roots[0].title if roots else "未命名文章"
        warnings.append("未找到 # 文档标题，已使用默认标题")
    doc_title = _clean_doc_title(doc_title)

    return {
        "title": doc_title,
        "summary": summary,
        "sections": sections,
        "content": content,
        "stats": stats,
        "source": meta["source"],
        "publish_date": meta["publish_date"],
        "source_url": meta["source_url"],
        "content_html": "",
    }, warnings


def _html_to_text(html: str) -> str:
    from html import unescape

    text = re.sub(r"(?is)<script.*?</script>", " ", html or "")
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|blockquote)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def parse_article_html(text: str) -> tuple[dict[str, Any], list[str]]:
    """清洗运营产出的理论文章 HTML，保存版式；明文仅作摘要、出题与检索。"""
    from app.services.html_sanitize import sanitize_display_html

    warnings: list[str] = []
    raw = (text or "").strip()
    if len(raw) < 20:
        raise ValueError("HTML 内容过短")
    html = sanitize_display_html(raw)
    if not html:
        raise ValueError("未解析到可用 HTML，请粘贴含标题与正文的完整页面或片段")

    title = ""
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    if h1:
        title = _html_to_text(h1.group(1))
    if not title:
        title_tag = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
        if title_tag:
            title = _html_to_text(title_tag.group(1))
    title = _clean_doc_title(title)
    if not title:
        title = "未命名文章"
        warnings.append("未找到 h1/title，已使用默认标题")

    plain = _html_to_text(html)
    meta = {"source": "", "publish_date": "", "source_url": ""}
    for line in plain.splitlines()[:40]:
        _apply_meta(meta, line)

    summary = _first_sentence(plain or title, 120)
    return {
        "title": title,
        "summary": summary,
        "sections": [],
        "content": plain,
        "content_html": html,
        "stats": {"chapters": 0, "sections": 0, "paragraphs": 0, "chars": len(plain)},
        "source": meta["source"],
        "publish_date": meta["publish_date"],
        "source_url": meta["source_url"],
    }, warnings
