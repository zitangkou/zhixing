#!/usr/bin/env python3
"""解析人民日报「十五五规划建议」正文，生成前端 mock 数据与后端 JSON。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(
    "/Users/dnn/.cursor/projects/Users-dnn-Projects-zhengkao-tong/uploads/content_30111880-0.html"
)
OUT_TS = ROOT / "src/mock/shiwuwu-plan.ts"
OUT_JSON = ROOT / "server/data/shiwuwu-plan.json"

HIGHLIGHT_KEYWORDS = [
    "两个确立",
    "两个维护",
    "新质生产力",
    "中国式现代化",
    "根本保证",
    "主要目标",
    "必须遵循",
    "高质量发展",
    "科技自立自强",
    "共同富裕",
    "总体国家安全观",
    "人类命运共同体",
]


def extract_body(text: str) -> str:
    start = text.find("中国共产党第二十届中央委员会第四次全体会议")
    if start == -1:
        raise ValueError("未找到正文起始位置")
    end = text.find("（新华社北京10月28日电）", start)
    if end == -1:
        end = len(text)
    body = text[start:end].strip()
    # 去掉重复的第二份正文（页面底部再次渲染）
    second = body.find("\n\n**一、")
    if second != -1:
        dup = body.find("\n\n**一、", second + 4)
        if dup != -1:
            body = body[:dup].strip()
    return body


def extract_highlight(text: str) -> str | None:
    for kw in HIGHLIGHT_KEYWORDS:
        if kw in text:
            idx = text.find(kw)
            start = max(0, text.rfind("。", 0, idx) + 1)
            end = text.find("。", idx)
            if end == -1:
                end = min(len(text), idx + 48)
            snippet = text[start : end + 1].strip()
            if len(snippet) >= 8:
                return snippet
    return None


def parse_bullets(block: str) -> tuple[str, list[dict]]:
    """将 —— 条目拆为 level 3 小节。"""
    parts = re.split(r"\n\s*——", block)
    intro = parts[0].strip()
    children: list[dict] = []
    for i, part in enumerate(parts[1:], 1):
        part = part.strip()
        if not part:
            continue
        title_end = part.find("。")
        title = part[: title_end + 1] if title_end != -1 else part[:24]
        children.append(
            {
                "id": f"bullet-{i}",
                "title": title[:30],
                "level": 3,
                "content": part,
            }
        )
    return intro, children


def parse_chapters(body: str) -> list[dict]:
    chapter_pattern = re.compile(r"\*\*([一二三四五六七八九十]+)、(.+?)\*\*")
    matches = list(chapter_pattern.finditer(body))
    if not matches:
        raise ValueError("未解析到章节标题")

    chapters: list[dict] = []
    for ci, match in enumerate(matches):
        ch_num = match.group(1)
        ch_title = match.group(2).strip()
        start = match.end()
        end = matches[ci + 1].start() if ci + 1 < len(matches) else len(body)
        chunk = body[start:end].strip()

        children: list[dict] = []
        item_pattern = re.compile(r"(?:^|\n)\s*（(\d+)）\s*")
        item_matches = list(item_pattern.finditer(chunk))

        if item_matches and item_matches[0].start() > 0:
            intro = chunk[: item_matches[0].start()].strip()
            if len(intro) > 10:
                children.append(
                    {
                        "id": f"c{ci + 1}-intro",
                        "title": "章节导言",
                        "level": 2,
                        "content": intro,
                        "highlight": extract_highlight(intro),
                    }
                )

        for ii, im in enumerate(item_matches):
            num = im.group(1)
            seg_start = im.end()
            seg_end = item_matches[ii + 1].start() if ii + 1 < len(item_matches) else len(chunk)
            seg = chunk[seg_start:seg_end].strip()
            node_id = f"c{ci + 1}-p{num}"

            if "——" in seg and seg.count("——") >= 2:
                intro, bullets = parse_bullets(seg)
                node: dict = {
                    "id": node_id,
                    "title": f"（{num}）",
                    "level": 2,
                    "content": intro if intro else seg.split("——")[0].strip(),
                    "highlight": extract_highlight(intro or seg),
                }
                for bi, b in enumerate(bullets):
                    b["id"] = f"{node_id}-{bi + 1}"
                if bullets:
                    node["children"] = bullets
                children.append(node)
            else:
                children.append(
                    {
                        "id": node_id,
                        "title": f"（{num}）",
                        "level": 2,
                        "content": seg,
                        "highlight": extract_highlight(seg),
                    }
                )

        if not children and chunk:
            children.append(
                {
                    "id": f"c{ci + 1}-1",
                    "title": "（一）",
                    "level": 2,
                    "content": chunk,
                    "highlight": extract_highlight(chunk),
                }
            )

        chapters.append(
            {
                "id": f"ch{ci + 1}",
                "title": f"{ch_num}、{ch_title}",
                "level": 1,
                "children": children,
            }
        )

    return chapters


def derive_section_title(title: str, content: str | None, highlight: str | None) -> str:
    generic = re.compile(r"^（[\d一二三四五六七八九十]+）$|^章节导言$|^第[\d一二三四]+段$")
    raw = title.strip()
    if not generic.match(raw) and len(raw) > 6:
        return raw
    text = (content or highlight or "").strip()
    if not text:
        return raw
    num_prefix = re.match(r"^（[\d]+）", raw)
    prefix = num_prefix.group(0) if num_prefix else ""
    first = re.split(r"[。；\n]", text)[0].strip()
    first = re.sub(r"^（\d+）\s*", "", first)
    first = re.sub(r"^——\s*", "", first)
    if len(first) > 40:
        first = first[:40] + "…"
    return f"{prefix}{first}" if prefix else first or raw


def enrich_titles(sections: list[dict]) -> list[dict]:
    result = []
    for sec in sections:
        node = {**sec}
        node["title"] = derive_section_title(
            sec.get("title", ""),
            sec.get("content"),
            sec.get("highlight"),
        )
        if sec.get("children"):
            node["children"] = enrich_titles(sec["children"])
        result.append(node)
    return result


def build_mind_map(title: str, sections: list[dict]) -> dict:
    children = []
    for sec in sections[:8]:
        child = {"id": sec["id"], "title": sec["title"][:20]}
        highlights = []
        for c in sec.get("children", [])[:2]:
            if c.get("highlight"):
                highlights.append(c["highlight"][:30])
            elif c.get("content"):
                highlights.append(c["content"][:30])
        if highlights:
            child["content"] = highlights[0]
        children.append(child)
    if len(sections) > 8:
        children.append(
            {
                "id": "more",
                "title": f"等共{len(sections)}大部分",
                "content": "涵盖产业、科技、民生、安全等",
            }
        )
    return {"id": "root", "title": title[:24], "children": children}


def sections_to_content(sections: list[dict]) -> str:
    parts: list[str] = []

    def walk(nodes: list[dict]):
        for node in nodes:
            if node.get("content"):
                parts.append(str(node["content"]).strip())
            if node.get("children"):
                walk(node["children"])

    walk(sections)
    return "\n\n".join(parts)


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    body = extract_body(text)
    sections = enrich_titles(parse_chapters(body))
    title = "中共中央关于制定国民经济和社会发展第十五个五年规划的建议"
    content = sections_to_content(sections)
    summary = (
        "党的二十届四中全会通过的「十五五」规划建议，明确「十五五」时期"
        "在基本实现社会主义现代化进程中的战略地位、指导方针与主要目标，"
        "是备考政治理论的重中之重。"
    )

    article = {
        "id": "art-shiwuwu",
        "title": title,
        "source": "人民日报",
        "sourceUrl": "https://paper.people.com.cn/rmrb/pc/content/202510/29/content_30111880.html",
        "publishDate": "2025-10-29",
        "summary": summary,
        "tags": ["十五五规划", "重点必读", "中国式现代化"],
        "isFeatured": True,
        "sections": sections,
        "content": content,
        "mindMap": build_mind_map("十五五规划建议", sections),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")

    ts = f"""import type {{ Article, ArticleSection, MindMapNode }} from '@/types'

/** 人民日报重点文章：十五五规划建议（自动生成，勿手改） */
export const shiwuwuPlanSections: ArticleSection[] = {json.dumps(sections, ensure_ascii=False, indent=2)}

export const shiwuwuPlanMindMap: MindMapNode = {json.dumps(article['mindMap'], ensure_ascii=False, indent=2)}

export const shiwuwuPlanArticleBase: Omit<Article, 'content'> = {{
  id: 'art-shiwuwu',
  title: {json.dumps(title, ensure_ascii=False)},
  source: '人民日报',
  publishDate: '2025-10-29',
  summary: {json.dumps(summary, ensure_ascii=False)},
  tags: {json.dumps(article['tags'], ensure_ascii=False)},
  isFeatured: true,
  sections: shiwuwuPlanSections,
  mindMap: shiwuwuPlanMindMap,
}}
"""
    OUT_TS.write_text(ts, encoding="utf-8")
    print(f"章节数: {len(sections)}")
    print(f"正文字数: {len(content)}")
    print(f"已写入: {OUT_TS}")
    print(f"已写入: {OUT_JSON}")


if __name__ == "__main__":
    main()
