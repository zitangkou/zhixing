"""从文章 sections 提取指定章节文本"""

from __future__ import annotations

from typing import Any


def _collect_section(node: dict[str, Any], parts: list[str]) -> None:
    title = (node.get("title") or "").strip()
    content = (node.get("content") or "").strip()
    highlight = (node.get("highlight") or "").strip()
    if title:
        parts.append(f"【{title}】")
    if content:
        parts.append(content)
    if highlight and highlight != content:
        parts.append(f"要点：{highlight}")
    for child in node.get("children") or []:
        _collect_section(child, parts)


def extract_sections_text(sections: list[dict[str, Any]], section_ids: list[str]) -> str:
    id_set = set(section_ids)
    parts: list[str] = []
    for sec in sections:
        if sec.get("id") in id_set:
            _collect_section(sec, parts)
    return "\n\n".join(parts).strip()


def flatten_source_corpus(sections: list[dict[str, Any]], section_ids: list[str]) -> str:
    """用于校验 source_sentence 的完整语料（含正文与 highlight）"""
    return extract_sections_text(sections, section_ids)


def list_chapter_section_ids(sections: list[dict[str, Any]]) -> list[str]:
    """列出顶层章节 id（如 ch1, ch2 …）"""
    ids: list[str] = []
    for sec in sections:
        sid = sec.get("id") or ""
        if isinstance(sid, str) and sid.startswith("ch") and sid[2:].isdigit():
            ids.append(sid)
    return ids
