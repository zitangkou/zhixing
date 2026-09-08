"""将纯文本自动拆分为多层级 sections（章/节/段）"""

from __future__ import annotations

import re
from typing import Any

_CN_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
_CN_SUB = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


def _split_paragraphs(content: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", content.strip())
    return [p.strip() for p in parts if len(p.strip()) > 8]


def _extract_highlight(paragraph: str) -> str | None:
    for kw in ["根本保证", "本质", "核心", "本质要求", "重大原则", "根本遵循"]:
        if kw in paragraph:
            idx = paragraph.find(kw)
            start = max(0, paragraph.rfind("。", 0, idx) + 1)
            end = paragraph.find("。", idx)
            if end == -1:
                end = min(len(paragraph), idx + 40)
            return paragraph[start : end + 1].strip()
    return None


def build_sections_from_content(title: str, content: str) -> list[dict[str, Any]]:
    paragraphs = _split_paragraphs(content)
    if not paragraphs:
        return [
            {
                "id": "s1",
                "title": "正文",
                "level": 1,
                "children": [
                    {
                        "id": "s1-1",
                        "title": "（一）全文",
                        "level": 2,
                        "content": content.strip(),
                    }
                ],
            }
        ]

    if len(paragraphs) <= 2:
        return [
            {
                "id": "s1",
                "title": "核心内容",
                "level": 1,
                "children": [
                    {
                        "id": f"s1-{i + 1}",
                        "title": f"（{_CN_SUB[i] if i < len(_CN_SUB) else i + 1}）要点{i + 1}",
                        "level": 2,
                        "content": para,
                        "highlight": _extract_highlight(para),
                    }
                    for i, para in enumerate(paragraphs)
                ],
            }
        ]

    chapter_size = max(2, (len(paragraphs) + 2) // 3)
    chapters: list[dict[str, Any]] = []

    for ci, start in enumerate(range(0, len(paragraphs), chapter_size)):
        chunk = paragraphs[start : start + chapter_size]
        ch_label = _CN_NUM[ci] if ci < len(_CN_NUM) else str(ci + 1)
        children: list[dict[str, Any]] = []

        for pi, para in enumerate(chunk):
            sub_label = _CN_SUB[pi] if pi < len(_CN_SUB) else str(pi + 1)
            node: dict[str, Any] = {
                "id": f"s{ci + 1}-{pi + 1}",
                "title": f"（{sub_label}）第{pi + 1}段",
                "level": 2,
                "content": para,
            }
            highlight = _extract_highlight(para)
            if highlight:
                node["highlight"] = highlight

            if len(para) > 180:
                sentences = [s.strip() + "。" for s in re.split(r"[。！？]", para) if len(s.strip()) > 12]
                if len(sentences) >= 2:
                    node["children"] = [
                        {
                            "id": f"s{ci + 1}-{pi + 1}-{si + 1}",
                            "title": f"{si + 1}. 分句",
                            "level": 3,
                            "content": sent,
                        }
                        for si, sent in enumerate(sentences[:4])
                    ]
                    node.pop("content", None)

            children.append(node)

        chapters.append(
            {
                "id": f"s{ci + 1}",
                "title": f"第{ch_label}部分",
                "level": 1,
                "children": children,
            }
        )

    return chapters


def sections_to_content(sections: list[dict[str, Any]]) -> str:
    parts: list[str] = []

    def walk(nodes: list[dict[str, Any]]):
        for node in nodes:
            if node.get("content"):
                parts.append(str(node["content"]).strip())
            if node.get("children"):
                walk(node["children"])

    walk(sections)
    return "\n\n".join(parts)
