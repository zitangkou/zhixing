"""三刀解剖法 Markdown 导入解析服务

将用户按模板书写的三刀解剖 Markdown 解析为 ShenlunMineLogUpsert 结构化数据。
模板结构：
  一、原文关键信息提取（表格）
  二、第一刀：剜出"万能规范词"（分类表格 + 金句 + 动词）
  三、第二刀：剔出"论证骨架"（总骨架 + 分论点）
  四、第三刀：割下"万能句式"（句型 A/B/C/D）
  五、申论核心启示总结
"""

from __future__ import annotations

import re
from datetime import date

from app.schemas import (
    ShenlunArgumentPoint,
    ShenlunArgumentSkeleton,
    ShenlunMineLogUpsert,
    ShenlunMineTermItem,
    ShenlunQuoteItem,
    ShenlunTemplateItem,
    ShenlunVerbItem,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_bold(text: str) -> str:
    """Remove markdown bold markers."""
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text).strip()


def _extract_table_rows(block: str) -> list[list[str]]:
    """Extract data rows from a markdown table (skip header + separator)."""
    rows: list[list[str]] = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        # skip separator row (---|---)
        if all(re.match(r"^[-:]+$", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def _split_sections(md: str) -> dict[str, str]:
    """Split markdown by ## headings, return {heading_text: content}."""
    sections: dict[str, str] = {}
    current_key = ""
    current_lines: list[str] = []
    for line in md.splitlines():
        m = re.match(r"^##\s+(.+)", line)
        if m:
            if current_key:
                sections[current_key] = "\n".join(current_lines)
            current_key = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_key:
        sections[current_key] = "\n".join(current_lines)
    return sections


def _split_subsections(block: str) -> dict[str, str]:
    """Split by ### headings within a section."""
    subs: dict[str, str] = {}
    current_key = ""
    current_lines: list[str] = []
    for line in block.splitlines():
        m = re.match(r"^###\s+(.+)", line)
        if m:
            if current_key:
                subs[current_key] = "\n".join(current_lines)
            current_key = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_key:
        subs[current_key] = "\n".join(current_lines)
    return subs


def _split_subsubsections(block: str) -> dict[str, str]:
    """Split by #### headings."""
    subs: dict[str, str] = {}
    current_key = ""
    current_lines: list[str] = []
    for line in block.splitlines():
        m = re.match(r"^####\s+(.+)", line)
        if m:
            if current_key:
                subs[current_key] = "\n".join(current_lines)
            current_key = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_key:
        subs[current_key] = "\n".join(current_lines)
    return subs


# ---------------------------------------------------------------------------
# Parsers per section
# ---------------------------------------------------------------------------

def _parse_title(md: str) -> str:
    """Extract article title from header metadata."""
    # Pattern: **文章标题：《xxx》（yyy）** or **文章标题：《xxx》**
    m = re.search(r"文章标题[：:]\s*《(.+?)》", md)
    if m:
        return m.group(1).strip()
    # Fallback: first # heading
    m = re.search(r"^#\s+(.+)", md, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _parse_date(md: str) -> str:
    """Extract practice date."""
    m = re.search(r"练习日期[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", md)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"练习日期[：:]\s*(\d{4}-\d{2}-\d{2})", md)
    if m:
        return m.group(1)
    return date.today().isoformat()


def _parse_source_excerpt(section: str) -> str:
    """Parse 原文关键信息提取 table into a summary string."""
    rows = _extract_table_rows(section)
    parts: list[str] = []
    for row in rows:
        if len(row) >= 2:
            key = _strip_bold(row[0])
            val = _strip_bold(row[1])
            if key in ("维度", "内容"):
                continue
            parts.append(f"【{key}】{val}")
    return "\n".join(parts)


def _parse_terms(section: str) -> list[ShenlunMineTermItem]:
    """Parse 第一刀 section: category tables → terms."""
    terms: list[ShenlunMineTermItem] = []
    subsections = _split_subsubsections(section)
    for heading, block in subsections.items():
        # Determine category from heading like "1. 问题与积弊"
        cat_match = re.match(r"\d+\.\s*(.+)", heading)
        category = cat_match.group(1).strip() if cat_match else heading.strip()
        # Skip 金句 and 动词 sections (parsed separately)
        if "金句" in category or "动词" in category:
            continue
        rows = _extract_table_rows(block)
        for row in rows:
            if len(row) >= 2:
                term = _strip_bold(row[0])
                plain = _strip_bold(row[1])
                if term in ("规范词", "可替换的普通词/语境"):
                    continue
                terms.append(ShenlunMineTermItem(term=term, category=category, plainWord=plain))
    return terms


def _parse_quotes(section: str) -> list[ShenlunQuoteItem]:
    """Parse 经典金句 table."""
    quotes: list[ShenlunQuoteItem] = []
    subsections = _split_subsubsections(section)
    for heading, block in subsections.items():
        if "金句" not in heading:
            continue
        rows = _extract_table_rows(block)
        for row in rows:
            if len(row) >= 2:
                text = _strip_bold(row[0])
                source = _strip_bold(row[1])
                if text in ("金句", "出处/解释"):
                    continue
                # Try to split "清代万斯大：有利于百姓的事..." into source + meaning
                meaning = ""
                if "：" in source:
                    src_part, meaning = source.split("：", 1)
                    source = src_part.strip()
                elif ":" in source:
                    src_part, meaning = source.split(":", 1)
                    source = src_part.strip()
                quotes.append(ShenlunQuoteItem(text=text, source=source, meaning=meaning.strip()))
    return quotes


def _parse_verbs(section: str) -> list[ShenlunVerbItem]:
    """Parse 高频动词 table."""
    verbs: list[ShenlunVerbItem] = []
    subsections = _split_subsubsections(section)
    for heading, block in subsections.items():
        if "动词" not in heading:
            continue
        rows = _extract_table_rows(block)
        for row in rows:
            if len(row) >= 2:
                verb = _strip_bold(row[0])
                usage = _strip_bold(row[1])
                if verb in ("动词", "适用语境"):
                    continue
                verbs.append(ShenlunVerbItem(verb=verb, usage=usage, category="高频动词"))
    return verbs


def _parse_argument(section: str) -> ShenlunArgumentSkeleton:
    """Parse 第二刀 section: 总骨架 + 分论点."""
    subsections = _split_subsections(section)
    overview = ""
    conclusion = ""
    points: list[ShenlunArgumentPoint] = []

    for heading, block in subsections.items():
        if "总骨架" in heading or "全文" in heading:
            # Extract overview text (first meaningful paragraph)
            lines = [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith("#")]
            overview = "\n".join(lines[:10])  # keep first 10 lines as overview
        elif "分论点" in heading:
            point = _parse_single_point(heading, block)
            points.append(point)

    # Try to extract conclusion from 总结升华
    if "总结升华" in section:
        m = re.search(r"总结升华[：:]\s*(.+?)(?:\n|$)", section)
        if m:
            conclusion = m.group(1).strip()

    return ShenlunArgumentSkeleton(
        mode="points",
        overview=overview,
        conclusion=conclusion,
        points=points,
    )


def _parse_single_point(heading: str, block: str) -> ShenlunArgumentPoint:
    """Parse a single 分论点 subsection."""
    # Extract title from heading like "2. 分论点1的论证小骨架（经典模板）"
    title_match = re.match(r"\d+\.\s*(.+)", heading)
    title = title_match.group(1).strip() if title_match else heading

    # Extract method name
    method = ""
    method_note = ""
    m = re.search(r"方法命名[：:]\s*(.+)", block)
    if m:
        method = m.group(1).strip()
        # Method explanation: lines after 方法命名 until a keyword line
        start = m.end()
        note_lines: list[str] = []
        for line in block[start:].splitlines():
            ls = line.strip()
            if not ls:
                continue
            if re.match(r"^(Step|套用|方法|点例|排比|类比|问题|典型)", ls):
                break
            note_lines.append(ls)
        method_note = "\n".join(note_lines[:10])

    # Extract template
    template = ""
    m = re.search(r"套用模板[：:]\s*(.*)", block)
    if m:
        # Collect from match to end of block or next ### heading
        start = m.end()
        tpl_lines: list[str] = []
        first = m.group(1).strip()
        if first:
            tpl_lines.append(first)
        for line in block[start:].splitlines():
            if line.strip().startswith("###") or line.strip().startswith("##"):
                break
            tpl_lines.append(line.strip())
        template = "\n".join(l for l in tpl_lines if l).strip()

    # Evidence: collect Step lines
    evidence_lines: list[str] = []
    for line in block.splitlines():
        if re.match(r"^Step\s*\d+", line) or re.match(r"^├|^└", line):
            evidence_lines.append(line.strip())
    evidence = "\n".join(evidence_lines[:20])

    return ShenlunArgumentPoint(
        title=title,
        evidence=evidence,
        method=method,
        methodNote=method_note,
        template=template,
    )


def _parse_templates(section: str) -> list[ShenlunTemplateItem]:
    """Parse 第三刀 section: 句型 A/B/C/D."""
    templates: list[ShenlunTemplateItem] = []
    subsections = _split_subsections(section)

    for heading, block in subsections.items():
        # heading like "句型A：对比转折型（引出问题、强调改变）"
        type_match = re.match(r"句型\s*([A-Z])[：:]\s*(.+)", heading)
        if not type_match:
            continue
        type_code = type_match.group(1).lower()
        type_name = type_match.group(2).strip()
        # Remove parenthetical
        type_name = re.sub(r"（.*?）", "", type_name).strip()

        original = ""
        template = ""
        imitate = ""

        for line in block.splitlines():
            line_s = line.strip()
            if line_s.startswith("- **原文：**") or line_s.startswith("- **原文:**"):
                original = re.sub(r"^-\s*\*\*原文[：:]\*\*\s*", "", line_s).strip()
            elif line_s.startswith("- **套用模板：**") or line_s.startswith("- **套用模板:**"):
                template = re.sub(r"^-\s*\*\*套用模板[：:]\*\*\s*", "", line_s).strip()
            elif line_s.startswith("- **仿写示例：**") or line_s.startswith("- **仿写示例:**"):
                imitate = re.sub(r"^-\s*\*\*仿写示例[：:]\*\*\s*", "", line_s).strip()

        # Also check for multi-line imitate examples (indented bullets)
        if not imitate:
            imitate_lines: list[str] = []
            in_imitate = False
            for line in block.splitlines():
                if "仿写示例" in line:
                    in_imitate = True
                    # Check if content is on same line
                    after = re.sub(r".*仿写示例[：:]\*{0,2}\s*", "", line.strip())
                    if after:
                        imitate_lines.append(after)
                    continue
                if in_imitate:
                    if line.strip().startswith("- ") and "原文" in line:
                        break
                    if line.strip().startswith("- "):
                        imitate_lines.append(line.strip().lstrip("- ").strip())
                    elif line.strip() and not line.strip().startswith("#"):
                        imitate_lines.append(line.strip())
            imitate = "\n".join(imitate_lines[:5])

        templates.append(ShenlunTemplateItem(
            type=type_code,
            typeName=type_name,
            original=original,
            template=template,
            imitate=imitate,
        ))

    return templates


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def parse_three_knife_markdown(md: str) -> ShenlunMineLogUpsert:
    """Parse a full three-knife dissection markdown into structured data."""
    title = _parse_title(md)
    mine_date = _parse_date(md)
    sections = _split_sections(md)

    # Find sections by keyword matching (headings may have numbering)
    excerpt_section = ""
    terms_section = ""
    argument_section = ""
    templates_section = ""

    for key, content in sections.items():
        if "原文" in key and "提取" in key:
            excerpt_section = content
        elif "第一刀" in key or "规范词" in key:
            terms_section = content
        elif "第二刀" in key or "骨架" in key:
            argument_section = content
        elif "第三刀" in key or "句式" in key:
            templates_section = content

    source_excerpt = _parse_source_excerpt(excerpt_section) if excerpt_section else ""
    terms: list[ShenlunMineTermItem | str] = list(_parse_terms(terms_section)) if terms_section else []
    quotes = _parse_quotes(terms_section) if terms_section else []
    verbs = _parse_verbs(terms_section) if terms_section else []
    argument = _parse_argument(argument_section) if argument_section else ShenlunArgumentSkeleton()
    templates = _parse_templates(templates_section) if templates_section else []

    return ShenlunMineLogUpsert(
        mineDate=mine_date,
        articleTitle=title,
        sourceExcerpt=source_excerpt,
        terms=terms,
        quotes=quotes,
        verbs=verbs,
        argument=argument,
        templates=templates,
    )
