"""knowledge_md 解析 / 校验 / 序列化单测。"""
from __future__ import annotations

from pathlib import Path

from app.services.knowledge_md import parse_md, serialize_md

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "docs" / "content" / "knowledge-framework"

SAMPLE = """# 申论

## 归纳概括题

### 类型

- 隐性要素
  - 概括变化
    - 提示变化的词语
      - 过去
      - 现在
- 显性要素

## 空题型
"""


def test_parse_heading_and_list_depths():
    r = parse_md(SAMPLE)
    assert r.title == "申论"
    assert not r.has_errors
    by_path = {n.path: n for n in r.nodes}
    assert by_path["归纳概括题"].depth == 0
    assert by_path["归纳概括题/类型"].depth == 1
    assert by_path["归纳概括题/类型/隐性要素"].depth == 2
    assert by_path["归纳概括题/类型/隐性要素/概括变化"].depth == 3
    assert by_path["归纳概括题/类型/隐性要素/概括变化/提示变化的词语/过去"].depth == 5
    assert any(i.code == "EMPTY_BRANCH" for i in r.issues)


def test_blockquote_content():
    md = "# 科\n\n## A\n\n> 第一行说明\n> 第二行\n"
    r = parse_md(md)
    assert r.nodes[0].content == "第一行说明\n第二行"


def test_duplicate_sibling_error():
    md = "# 科\n\n## A\n\n## A\n"
    r = parse_md(md)
    assert r.has_errors
    assert any(i.code == "DUPLICATE_SIBLING" for i in r.issues)


def test_bad_indent_error():
    md = "# 科\n\n## A\n\n### B\n\n - bad\n"  # 1-space indent before list marker position... 
    # use 1 space before dash after ### context: " ###" no - list with indent 1
    md = "# 科\n\n## A\n\n### B\n\n - x\n"
    r = parse_md(md)
    assert any(i.code == "BAD_INDENT" and i.level == "error" for i in r.issues)


def test_level_jump_error():
    md = "# 科\n\n## A\n\n### B\n\n- c\n    - too deep jump\n"
    r = parse_md(md)
    assert any(i.code == "LEVEL_JUMP" for i in r.issues)


def test_missing_h1_error():
    r = parse_md("## Only H2\n")
    assert any(i.code == "MISSING_H1" for i in r.issues)


def test_deep_heading_warning():
    md = "# 科\n\n## A\n\n### B\n\n#### C\n"
    r = parse_md(md)
    assert any(i.code == "DEEP_HEADING" for i in r.issues)


def test_serialize_roundtrip_stable():
    r = parse_md(SAMPLE)
    assert r.tree is not None
    md2 = serialize_md(r.tree)
    r2 = parse_md(md2)
    assert [n.path for n in r.nodes if n.path != "空题型"] == [
        n.path for n in r2.nodes if n.path != "空题型"
    ]
    # serialize drops empty branch still present - both have 空题型
    assert [n.path for n in r.nodes] == [n.path for n in r2.nodes]
    md3 = serialize_md(r2.tree)
    assert md2 == md3


def test_archive_files_parse_clean():
    """存档 md 应能解析；允许 warning，不应有 error（除已知空题型已删）。"""
    assert ARCHIVE.is_dir(), ARCHIVE
    for path in sorted(ARCHIVE.glob("*.md")):
        if path.name == "README.md":
            continue
        r = parse_md(path.read_text(encoding="utf-8"))
        errors = [i for i in r.issues if i.level == "error"]
        assert not errors, f"{path.name}: {errors}"
        assert r.stats["nodeCount"] > 0


def test_heading_jump_is_error_and_depth_normalized():
    md = "# 科\n\n## A\n\n#### B\n\n- c\n"
    r = parse_md(md)
    assert any(i.code == "HEADING_JUMP" and i.level == "error" for i in r.issues)
    by_path = {n.path: n for n in r.nodes}
    # 深度始终为 parent.depth + 1，与标题级别无关
    assert by_path["A/B"].depth == 1
    assert by_path["A/B/c"].depth == 2


def test_first_list_item_indented_is_error():
    md = "# 科\n\n## A\n\n### B\n\n    - c\n"
    r = parse_md(md)
    assert any(i.code == "LEVEL_JUMP" and i.level == "error" for i in r.issues)
    assert {n.path: n for n in r.nodes}["A/B/c"].depth == 2


def test_roundtrip_preserves_depths():
    r = parse_md(SAMPLE)
    r2 = parse_md(serialize_md(r.tree))
    assert [(n.path, n.depth, n.parent_index) for n in r.nodes] == [
        (n.path, n.depth, n.parent_index) for n in r2.nodes
    ]


def test_archive_roundtrip_preserves_structure():
    for path in sorted(ARCHIVE.glob("*.md")):
        if path.name == "README.md":
            continue
        r = parse_md(path.read_text(encoding="utf-8"))
        r2 = parse_md(serialize_md(r.tree))
        assert [(n.path, n.depth) for n in r.nodes] == [(n.path, n.depth) for n in r2.nodes], path.name


def test_md_too_large_rejected():
    from app.services.knowledge_md import MAX_MD_CHARS

    r = parse_md("# 科\n" + "x" * (MAX_MD_CHARS + 1))
    assert any(i.code == "MD_TOO_LARGE" for i in r.issues)
    assert r.nodes == []


def test_parse_is_linear_time():
    """2000 节点应在远低于 1 秒内完成（旧实现为 O(n³)，630 节点需十余秒）。"""
    import time

    lines = ["# 科", ""]
    for a in range(20):
        lines += [f"## 分支{a}", ""]
        for b in range(10):
            lines.append(f"- 子{b}")
            for c in range(9):
                lines.append(f"  - 叶{c}")
    md = "\n".join(lines) + "\n"
    t0 = time.perf_counter()
    r = parse_md(md)
    elapsed = time.perf_counter() - t0
    assert r.stats["nodeCount"] == 20 + 20 * 10 * 10
    assert r.stats["leafCount"] == 20 * 10 * 9
    assert elapsed < 1.0, elapsed
