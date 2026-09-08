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


@dataclass
class _ImportNode:
    """level: 1=章 2=节 3=段（与移动端 ArticleSection 一致）"""
    level: int
    title: str
    content_parts: list[str] = field(default_factory=list)
    children: list[_ImportNode] = field(default_factory=list)
    raw_heading: str = ""


def _strip_quotes(text: str) -> str:
    return text.strip().strip("「」\"'“”")


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
    if content:
        section["content"] = content
        highlight = _extract_highlight(content)
        if highlight:
            section["highlight"] = highlight
        elif node.level == 2 and len(content) <= 160:
            section["highlight"] = _first_sentence(content, 120)
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


def _parse_legacy_part_format(lines: list[str], warnings: list[str]) -> tuple[str, list[_ImportNode]]:
    """旧版三编结构：映射为 章(1) / 节(2)，编名写入章标题前缀"""
    doc_title = ""
    roots: list[_ImportNode] = []
    current_part_title = ""
    current_chapter: _ImportNode | None = None
    current_section: _ImportNode | None = None
    content_target: _ImportNode | None = None

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if not line.strip():
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
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
                content_target = None
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
                content_target = current_chapter
                continue

            if depth == 4:
                if not current_chapter:
                    warnings.append(f"第 {line_no} 行：节标题前缺少章，已跳过")
                    continue
                if current_section:
                    _finalize_section_node(current_section)
                current_section = _ImportNode(level=2, title=heading_text, raw_heading=heading_text)
                current_chapter.children.append(current_section)
                content_target = current_section
                continue

            continue

        quote_match = _BLOCKQUOTE_RE.match(line)
        if quote_match and content_target:
            text = quote_match.group(1).strip()
            if text:
                content_target.content_parts.append(text)
            continue

    if current_section:
        _finalize_section_node(current_section)

    for chapter in roots:
        intro = _join_content(chapter.content_parts)
        chapter.title = _chapter_title(chapter.raw_heading, intro or None)
        for section in chapter.children:
            content = _join_content(section.content_parts)
            section.title = _section_title(section.raw_heading, content)

    return doc_title, roots


def _parse_chapter_section_format(lines: list[str], warnings: list[str]) -> tuple[str, list[_ImportNode]]:
    doc_title = ""
    roots: list[_ImportNode] = []
    current_chapter: _ImportNode | None = None
    current_section: _ImportNode | None = None
    content_target: _ImportNode | None = None

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if not line.strip():
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            marks, heading_text = heading_match.groups()
            depth = len(marks)
            heading_text = heading_text.strip()

            if depth == 1:
                if not doc_title:
                    doc_title = _strip_quotes(heading_text)
                else:
                    warnings.append(f"第 {line_no} 行：忽略重复的文档标题")
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
                content_target = current_chapter
                continue

            if depth == 3:
                if not current_chapter:
                    warnings.append(f"第 {line_no} 行：节前缺少章标题，已自动创建默认章")
                    current_chapter = _ImportNode(level=1, title="正文", raw_heading="正文")
                    roots.append(current_chapter)
                if current_section:
                    _finalize_section_node(current_section)
                current_section = _ImportNode(level=2, title=heading_text, raw_heading=heading_text)
                current_chapter.children.append(current_section)
                content_target = current_section
                continue

            if depth == 4:
                warnings.append(f"第 {line_no} 行：请使用 ### 节 + 引用块分段，#### 标题已忽略")
                continue

            warnings.append(f"第 {line_no} 行：不支持的标题层级 {depth}")
            continue

        quote_match = _BLOCKQUOTE_RE.match(line)
        if quote_match:
            if content_target is None:
                warnings.append(f"第 {line_no} 行：正文出现在标题之前，已忽略")
                continue
            text = quote_match.group(1).strip()
            if text:
                content_target.content_parts.append(text)
            continue

        warnings.append(f"第 {line_no} 行：无法识别的内容，已忽略")

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
    lines = text.replace("\r\n", "\n").split("\n")

    if _detect_legacy_part_format(lines):
        warnings.append("检测到旧版「编-章-节」格式，已自动映射为移动端章-节结构")
        doc_title, roots = _parse_legacy_part_format(lines, warnings)
    else:
        doc_title, roots = _parse_chapter_section_format(lines, warnings)

    if not roots:
        raise ValueError(
            "未解析到章-节结构。请使用：# 标题、## 章、### 节，正文用 > 引用块（多段自动拆为「段」）"
        )

    sections = [_node_to_section(chapter, f"ch{index + 1}") for index, chapter in enumerate(roots)]
    stats = _count_nodes(roots)
    content = sections_to_content(sections)
    summary = _first_sentence(content or doc_title, 120)

    if not doc_title:
        doc_title = roots[0].title if roots else "未命名文章"
        warnings.append("未找到 # 文档标题，已使用默认标题")

    return {
        "title": doc_title,
        "summary": summary,
        "sections": sections,
        "content": content,
        "stats": stats,
    }, warnings
