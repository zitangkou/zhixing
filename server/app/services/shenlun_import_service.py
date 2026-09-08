"""解析运营 v2.18 三刀解剖 Markdown。"""

from __future__ import annotations

import re
from datetime import date

from app.schemas.rmrb import (
    ShenlunArgumentPoint,
    ShenlunArgumentSkeleton,
    ShenlunExamAnchor,
    ShenlunMineLogUpsert,
    ShenlunMineTermItem,
    ShenlunQuoteItem,
    ShenlunTemplateItem,
    ShenlunTransferGuide,
    ShenlunVerbItem,
)


def _strip(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text or "").strip()


def _front_matter(md: str) -> tuple[dict[str, str], str]:
    if not md.startswith("---"):
        return {}, md
    end = md.find("\n---", 3)
    if end < 0:
        return {}, md
    meta: dict[str, str] = {}
    for line in md[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip()] = val.strip()
    return meta, md[end + 4 :]


def _split_h2(md: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = ""
    lines: list[str] = []
    for line in md.splitlines():
        m = re.match(r"^##\s+(.+)", line)
        if m:
            if current:
                sections[current] = "\n".join(lines)
            current = m.group(1).strip()
            lines = []
        else:
            lines.append(line)
    if current:
        sections[current] = "\n".join(lines)
    return sections


def _split_h3(block: str) -> dict[str, str]:
    subs: dict[str, str] = {}
    current = ""
    lines: list[str] = []
    for line in block.splitlines():
        m = re.match(r"^###\s+(.+)", line)
        if m:
            if current:
                subs[current] = "\n".join(lines)
            current = m.group(1).strip()
            lines = []
        else:
            lines.append(line)
    if current:
        subs[current] = "\n".join(lines)
    return subs


def _section(sections: dict[str, str], *keys: str) -> str:
    for name, body in sections.items():
        if any(k in name for k in keys):
            return body
    return ""


def _field(block: str, *labels: str) -> str:
    """解析 `- 标签：值` / `标签：值`，兼容加粗与中英文冒号。"""
    if not block:
        return ""
    for label in labels:
        escaped = re.escape(label)
        patterns = (
            rf"^[\-\*\u2022·]\s*(?:\*\*)?{escaped}(?:\*\*)?\s*[：:]\s*(.+)$",
            rf"^(?:\*\*)?{escaped}(?:\*\*)?\s*[：:]\s*(.+)$",
        )
        for pat in patterns:
            m = re.search(pat, block, re.M)
            if m:
                return _strip(m.group(1))
    return ""


def _bullet(block: str, label: str) -> str:
    return _field(block, label)


def theme_tags_from_anchor(theme: str) -> list[str]:
    parts = re.split(r"[｜|/、，,]+", theme or "")
    tags: list[str] = []
    seen: set[str] = set()
    for raw in ["时评精拆", *parts]:
        item = raw.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        tags.append(item)
    return tags[:8]


def _table_rows(block: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [_strip(c) for c in line.split("|")[1:-1]]
        if all(re.match(r"^[-:]+$", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def _parse_terms(section: str) -> list[ShenlunMineTermItem]:
    items: list[ShenlunMineTermItem] = []
    for row in _table_rows(section):
        if len(row) < 2:
            continue
        term, category = row[0], row[1] if len(row) > 1 else "其他"
        plain = row[2] if len(row) > 2 else ""
        if term in ("词语", "规范词") or term.startswith("待补充"):
            continue
        items.append(ShenlunMineTermItem(term=term, category=category or "其他", plainWord=plain))
    return items


def _parse_quotes(section: str) -> list[ShenlunQuoteItem]:
    quotes: list[ShenlunQuoteItem] = []
    for heading, block in _split_h3(section).items():
        if "语录" not in heading:
            continue
        quotes.append(
            ShenlunQuoteItem(
                text=_bullet(block, "原文"),
                source=_bullet(block, "出处"),
                meaning=_bullet(block, "释义"),
            )
        )
    return [q for q in quotes if q.text]


def _parse_verbs(section: str) -> list[ShenlunVerbItem]:
    verbs: list[ShenlunVerbItem] = []
    for row in _table_rows(section):
        if len(row) < 2:
            continue
        verb, usage = row[0], row[1]
        category = row[2] if len(row) > 2 else "其他"
        if verb in ("动词",) or verb.startswith("待补充"):
            continue
        verbs.append(ShenlunVerbItem(verb=verb, usage=usage, category=category or "其他"))
    return verbs


def _parse_templates(section: str) -> list[ShenlunTemplateItem]:
    templates: list[ShenlunTemplateItem] = []
    for _heading, block in _split_h3(section).items():
        type_code = _bullet(block, "类型") or "dialectic"
        templates.append(
            ShenlunTemplateItem(
                type=type_code.split()[0],
                typeName=_bullet(block, "类型名"),
                original=_bullet(block, "原文"),
                template=_bullet(block, "模板"),
                imitate=_bullet(block, "仿写"),
            )
        )
    return [t for t in templates if t.original or t.template]


def _parse_points(section: str) -> list[ShenlunArgumentPoint]:
    points: list[ShenlunArgumentPoint] = []
    for heading, block in _split_h3(section).items():
        if "分论点" not in heading:
            continue
        points.append(
            ShenlunArgumentPoint(
                title=_bullet(block, "标题"),
                evidence=_bullet(block, "论据"),
                summary=_bullet(block, "小结"),
                method=_bullet(block, "论证方法"),
                methodNote=_bullet(block, "方法说明"),
                template=_bullet(block, "套用模板"),
            )
        )
    return points


def _overview_line(section: str) -> str:
    m = re.search(r"^总论点[：:]\s*(.+)", section, re.M)
    return _strip(m.group(1)) if m else ""


def parse_three_knife_markdown(md: str) -> ShenlunMineLogUpsert:
    meta, body = _front_matter(md.strip())
    sections = _split_h2(body)
    exam_sec = _section(sections, "考题定位")
    excerpt_sec = _section(sections, "原文摘录")
    skeleton_sec = _section(sections, "总骨架")
    summary_sec = _section(sections, "总结")
    terms_sec = _section(sections, "规范词")
    quotes_sec = _section(sections, "语录")
    verbs_sec = _section(sections, "高频动词")
    tpl_sec = _section(sections, "句式")
    transfer_sec = _section(sections, "迁移指南")

    excerpt = _strip(excerpt_sec)
    excerpt = re.sub(r"^>\s*", "", excerpt, flags=re.M).strip()

    title = meta.get("article_title") or ""
    if not title:
        m = re.search(r"文章标题[：:]\s*《(.+?)》", md)
        title = m.group(1).strip() if m else ""
    mine_date = meta.get("mine_date") or date.today().isoformat()

    argument = ShenlunArgumentSkeleton(
        mode="points",
        openingPattern=_bullet(skeleton_sec, "开头范式"),
        transition=_bullet(skeleton_sec, "过渡技巧"),
        overview=_overview_line(skeleton_sec),
        conclusion=_strip(summary_sec),
        points=_parse_points(skeleton_sec),
    )
    return ShenlunMineLogUpsert(
        mineDate=mine_date,
        articleId=meta.get("article_id") or None,
        articleTitle=title,
        sourceExcerpt=excerpt,
        terms=_parse_terms(terms_sec),
        quotes=_parse_quotes(quotes_sec),
        verbs=_parse_verbs(verbs_sec),
        argument=argument,
        templates=_parse_templates(tpl_sec),
        examAnchor=ShenlunExamAnchor(
            theme=_field(exam_sec, "主题归类", "主题"),
            titleDevice=_field(exam_sec, "标题机关"),
            stancePath=_field(exam_sec, "立意路径"),
        ),
        transferGuide=ShenlunTransferGuide(
            examFit=_bullet(transfer_sec, "适用考题"),
            caution=_bullet(transfer_sec, "套用警示"),
            imitateDemo=_bullet(transfer_sec, "今日仿写示范"),
        ),
    )


def v218_incomplete_reasons(parsed: ShenlunMineLogUpsert) -> list[str]:
    reasons: list[str] = []
    a = parsed.argument or ShenlunArgumentSkeleton()
    if not parsed.articleTitle:
        reasons.append("文章标题")
    if not parsed.sourceExcerpt:
        reasons.append("原文摘录")
    if not parsed.examAnchor.theme or not parsed.examAnchor.titleDevice or not parsed.examAnchor.stancePath:
        reasons.append("考题定位")
    if not a.openingPattern or not a.transition or not a.overview or not a.conclusion or not a.points:
        reasons.append("总骨架")
    if not parsed.terms:
        reasons.append("规范词")
    if not parsed.quotes:
        reasons.append("语录")
    if not parsed.verbs:
        reasons.append("高频动词")
    if not parsed.templates:
        reasons.append("句式模板")
    if not parsed.transferGuide.examFit or not parsed.transferGuide.caution or not parsed.transferGuide.imitateDemo:
        reasons.append("迁移指南")
    return reasons
