"""知识框架 Markdown 解析 / 校验 / 序列化（纯函数，无 DB 依赖）。

规则对齐实施文档 §3.3 + §3.4：
- `#` 文档标题（不进树）
- `##` depth0、`###` depth1；`####`～`######` 仍可解析但发出 DEEP_HEADING 警告
- depth≥2 推荐 `- ` 列表（2 空格缩进/级）
- `> ` 行写入上一节点 content
- 同级标题不可重复（error）
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LIST_RE = re.compile(r"^([-*+]|\d+\.)\s+")
_FRONTMATTER_RE = re.compile(r"^---\s*$")


@dataclass
class Issue:
    level: str  # error | warning
    code: str
    line: int
    message: str
    path: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class FlatNode:
    title: str
    depth: int
    parent_index: int
    sort_order: int
    line: int
    content: str = ""
    path: str = ""
    id: str = ""  # filled by publish / preview callers

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MapNode:
    id: str
    title: str
    depth: int
    line: int
    path: str
    content: str = ""
    children: list["MapNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "depth": self.depth,
            "line": self.line,
            "path": self.path,
            "children": [c.to_dict() for c in self.children] if self.children else None,
        }


@dataclass
class ParseResult:
    title: str
    nodes: list[FlatNode]
    tree: MapNode | None
    issues: list[Issue]
    stats: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "nodes": [n.to_dict() for n in self.nodes],
            "tree": self.tree.to_dict() if self.tree else None,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats,
        }

    @property
    def has_errors(self) -> bool:
        return any(i.level == "error" for i in self.issues)


def strip_md(text: str) -> str:
    s = text.strip()
    if s.startswith("\\"):
        s = s[1:]
    s = re.sub(r"^[-*+]\s+", "", s)
    s = re.sub(r"^\d+\.\s+", "", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"\[\[(.+?)(?:\|(.+?))?\]\]", lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s.strip()


def _append_content(node: FlatNode, text: str) -> None:
    t = text.strip()
    if t.startswith(">"):
        t = t[1:].lstrip()
    if not t and not text.strip().startswith(">"):
        return
    prev = node.content.rstrip()
    node.content = f"{prev}\n{t}".strip() if prev else t


def _build_path(parent_path: str, title: str) -> str:
    return f"{parent_path}/{title}" if parent_path else title


def parse_md(md: str, *, temp_id_prefix: str = "tmp") -> ParseResult:
    issues: list[Issue] = []
    nodes: list[FlatNode] = []
    stack: list[tuple[int, int]] = []  # (depth, index)
    last_heading_depth = -1
    last_list_indent: int | None = None
    doc_title = ""
    lines = md.splitlines()

    if lines and _FRONTMATTER_RE.match(lines[0].strip()):
        # classic frontmatter block
        if len(lines) > 1:
            issues.append(
                Issue("error", "FRONTMATTER", 1, "禁止使用 frontmatter；导图样式由系统统一配置")
            )

    def add_node(title: str, depth: int, line_no: int) -> int:
        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent_index = stack[-1][1] if stack else -1
        parent_path = nodes[parent_index].path if parent_index >= 0 else ""
        path = _build_path(parent_path, title)
        # duplicate sibling check
        for i, n in enumerate(nodes):
            if n.parent_index == parent_index and n.title == title:
                issues.append(
                    Issue(
                        "error",
                        "DUPLICATE_SIBLING",
                        line_no,
                        f"同级重复标题「{title}」",
                        path=path,
                    )
                )
                break
        node = FlatNode(
            title=title,
            depth=depth,
            parent_index=parent_index,
            sort_order=len(nodes),
            line=line_no,
            path=path,
            id=f"{temp_id_prefix}-{len(nodes)}",
        )
        idx = len(nodes)
        nodes.append(node)
        stack.append((depth, idx))
        return idx

    for line_no, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        # only spaces for indent (tabs → warning + treat as 2 spaces each)
        if "\t" in raw[: len(raw) - len(raw.lstrip(" \t"))]:
            issues.append(
                Issue("warning", "BAD_INDENT", line_no, "请使用空格缩进（勿用 Tab）")
            )
        indent_part = raw[: len(raw) - len(raw.lstrip(" "))]
        indent = len(indent_part)
        stripped = raw.lstrip(" ")

        if stripped.startswith("---"):
            # horizontal rule or closing frontmatter — skip content
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            title = strip_md(heading.group(2))
            if not title:
                issues.append(Issue("error", "EMPTY_TITLE", line_no, "空标题"))
                continue
            if len(title) > 200:
                issues.append(
                    Issue("error", "TITLE_TOO_LONG", line_no, "标题超过 200 字", path=title)
                )
            elif len(title) > 60:
                issues.append(
                    Issue("warning", "LONG_TITLE", line_no, "标题超过 60 字，导图将换行", path=title)
                )
            if level == 1:
                if not doc_title:
                    doc_title = title
                last_heading_depth = -1
                last_list_indent = None
                continue
            if level >= 4:
                issues.append(
                    Issue(
                        "warning",
                        "DEEP_HEADING",
                        line_no,
                        "depth≥2 建议改用 `- ` 列表（2 空格缩进）",
                        path=title,
                    )
                )
            depth = level - 2
            # heading level jump warning (## then ####)
            if stack and depth > stack[-1][0] + 1 and last_heading_depth >= 0:
                issues.append(
                    Issue(
                        "warning",
                        "HEADING_JUMP",
                        line_no,
                        f"标题跳级（上一层 depth={last_heading_depth} → {depth}）",
                        path=title,
                    )
                )
            add_node(title, depth, line_no)
            last_heading_depth = depth
            last_list_indent = None
            continue

        if indent % 2 != 0 and _LIST_RE.match(stripped):
            issues.append(
                Issue("error", "BAD_INDENT", line_no, "列表缩进必须是 2 空格的倍数")
            )

        if _LIST_RE.match(stripped):
            title = strip_md(stripped)
            if not title:
                issues.append(Issue("error", "EMPTY_TITLE", line_no, "空列表项标题"))
                continue
            if len(title) > 200:
                issues.append(
                    Issue("error", "TITLE_TOO_LONG", line_no, "标题超过 200 字", path=title)
                )
            elif len(title) > 60:
                issues.append(
                    Issue("warning", "LONG_TITLE", line_no, "标题超过 60 字，导图将换行", path=title)
                )
            if last_list_indent is not None and indent - last_list_indent > 2:
                issues.append(
                    Issue(
                        "error",
                        "LEVEL_JUMP",
                        line_no,
                        "列表一次缩进超过 1 级（>2 空格）",
                        path=title,
                    )
                )
            if last_heading_depth >= 0:
                depth = last_heading_depth + 1 + (indent // 2)
            else:
                depth = indent // 2
            add_node(title, depth, line_no)
            last_list_indent = indent
            continue

        # blockquote content
        if stripped.startswith(">"):
            if nodes:
                _append_content(nodes[-1], stripped)
            continue

        if nodes and not stripped.startswith("<!--"):
            _append_content(nodes[-1], stripped)

    if not doc_title:
        issues.append(Issue("error", "MISSING_H1", 1, "缺少一级标题 `# 科目名`"))

    # empty depth0 branches
    for n in nodes:
        if n.depth == 0:
            has_child = any(c.parent_index == n.sort_order for c in nodes)
            # parent_index points to index, sort_order == index at creation
            has_child = any(c.parent_index == nodes.index(n) for c in nodes)
            if not has_child:
                issues.append(
                    Issue(
                        "warning",
                        "EMPTY_BRANCH",
                        n.line,
                        f"题型「{n.title}」下没有子节点",
                        path=n.path,
                    )
                )

    if len(nodes) > 2000:
        issues.append(
            Issue("error", "TOO_MANY_NODES", 1, f"节点数 {len(nodes)} 超过上限 2000")
        )
    max_d = max((n.depth for n in nodes), default=-1)
    if max_d > 10:
        issues.append(Issue("error", "TOO_DEEP", 1, f"最大深度 {max_d} 超过上限 10"))

    tree = build_map_tree(doc_title or "未命名", nodes)
    leaf_count = sum(1 for n in nodes if not any(c.parent_index == nodes.index(n) for c in nodes))
    stats = {
        "nodeCount": len(nodes),
        "leafCount": leaf_count,
        "maxDepth": max_d,
    }
    return ParseResult(title=doc_title, nodes=nodes, tree=tree, issues=issues, stats=stats)


def build_map_tree(root_title: str, nodes: list[FlatNode]) -> MapNode:
    root = MapNode(id="root", title=root_title, depth=-1, line=1, path="")
    if not nodes:
        return root
    map_nodes = [
        MapNode(
            id=n.id or f"n-{i}",
            title=n.title,
            depth=n.depth,
            line=n.line,
            path=n.path,
            content=n.content,
        )
        for i, n in enumerate(nodes)
    ]
    for i, n in enumerate(nodes):
        if n.parent_index < 0:
            root.children.append(map_nodes[i])
        else:
            map_nodes[n.parent_index].children.append(map_nodes[i])
    return root


def serialize_md(tree: MapNode) -> str:
    """按 §3.4 规范输出。tree 为含科目根的 MapNode（depth=-1）。"""
    lines: list[str] = [f"# {tree.title}", ""]

    def esc(title: str) -> str:
        t = " ".join((title or "").strip().split())
        if t.startswith("#") or _LIST_RE.match(t) or t.startswith(">"):
            return "\\" + t
        return t

    def emit(n: MapNode) -> None:
        title = esc(n.title)
        if n.depth == 0:
            lines.append(f"## {title}")
            lines.append("")
        elif n.depth == 1:
            lines.append(f"### {title}")
            lines.append("")
        else:
            indent = "  " * max(n.depth - 2, 0)
            lines.append(f"{indent}- {title}")
        if n.content:
            for para in n.content.splitlines():
                lines.append(f"> {para}" if para.strip() else ">")
            lines.append("")
        for c in n.children or []:
            emit(c)
        if n.depth <= 1 and lines and lines[-1] != "":
            lines.append("")

    for child in tree.children or []:
        emit(child)
    while lines and lines[-1] == "":
        lines.pop()
    lines.append("")
    return "\n".join(lines)


def parse_md_to_legacy_flat(md: str, tree_key: str = "", source_file: str = "") -> list[dict]:
    """兼容旧 `_parse_md_to_tree` 返回结构。"""
    result = parse_md(md)
    out: list[dict] = []
    for n in result.nodes:
        out.append(
            {
                "title": n.title,
                "depth": n.depth,
                "parent_index": n.parent_index,
                "sort_order": n.sort_order,
                "line": n.line,
                "content": n.content,
                "path": n.path,
            }
        )
    return out
