#!/usr/bin/env python3
"""只读旧库 knowledge_nodes，按父链重算深度，导出为规范 Markdown（§3.4）。

规范：
- `# 科目`
- depth0 → `##`，depth1 → `###`
- depth≥2 → `- ` 列表，2 空格缩进/级
- 可选正文：`> ` 行
- 同级重复标题：默认保留第一条（按 sort_order），其余跳过并写入警告
- 默认跳过「申论题型」与健康类树；可选把「申论题型」中独有 path 合并进「申论」

用法：
  python3 scripts/knowledge_export_from_legacy.py --verify
  python3 scripts/knowledge_export_from_legacy.py --merge-unique-shenlun-tixing --verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path("/Users/dnn/Projects/zhengkao-tong/server/data/zhengkao.db")
DEFAULT_OUT = ROOT / "docs" / "content" / "knowledge-framework"
RUNTIME_OUT = ROOT / "server" / "data" / "knowledge"

_HEALTH_SKIP = ("心理和身体", "恢复计划", "健康日记", "湿气", "湿疹")
_LIST_PREFIX_RE = re.compile(r"^([-*+]|\d+\.)\s+")


@dataclass
class Node:
    id: str
    parent_id: str | None
    title: str
    content: str
    sort_order: int
    children: list["Node"] = field(default_factory=list)
    depth: int = 0  # parent-chain depth


@dataclass
class Warn:
    code: str
    tree_key: str
    path: str
    message: str


def open_ro(db: Path) -> sqlite3.Connection:
    uri = f"file:{db}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def should_skip_tree(tree_key: str) -> bool:
    return any(k in tree_key for k in _HEALTH_SKIP)


def escape_title(title: str) -> str:
    t = " ".join((title or "").strip().split())
    if not t:
        return t
    if t.startswith("#") or _LIST_PREFIX_RE.match(t) or t.startswith(">"):
        return "\\" + t
    return t


def load_tree(conn: sqlite3.Connection, tree_key: str) -> tuple[list[Node], list[Warn]]:
    rows = conn.execute(
        "SELECT id, parent_id, title, content, sort_order "
        "FROM knowledge_nodes WHERE tree_key=? ORDER BY sort_order, id",
        (tree_key,),
    ).fetchall()
    by_id: dict[str, Node] = {}
    for r in rows:
        by_id[r["id"]] = Node(
            id=r["id"],
            parent_id=r["parent_id"],
            title=(r["title"] or "").strip(),
            content=(r["content"] or "").strip(),
            sort_order=int(r["sort_order"] or 0),
        )
    roots: list[Node] = []
    for n in by_id.values():
        if n.parent_id and n.parent_id in by_id:
            by_id[n.parent_id].children.append(n)
        else:
            roots.append(n)

    def sort_rec(nodes: list[Node]) -> None:
        nodes.sort(key=lambda x: (x.sort_order, x.title, x.id))
        for c in nodes:
            sort_rec(c.children)

    sort_rec(roots)

    warns: list[Warn] = []

    def assign_depth(nodes: list[Node], depth: int, parent_path: str) -> None:
        seen: dict[str, Node] = {}
        kept: list[Node] = []
        for n in nodes:
            n.depth = depth
            path = f"{parent_path}/{n.title}" if parent_path else n.title
            if not n.title or n.title == "-":
                warns.append(
                    Warn(
                        "BAD_TITLE_REMOVED",
                        tree_key,
                        path or "(empty)",
                        "已删除空标题或占位「-」节点",
                    )
                )
                continue
            if n.title in seen:
                warns.append(
                    Warn(
                        "DUPLICATE_SIBLING",
                        tree_key,
                        path,
                        f"同级重复标题，已丢弃后出现的副本（保留 sort_order={seen[n.title].sort_order}）",
                    )
                )
                continue
            seen[n.title] = n
            kept.append(n)
            assign_depth(n.children, depth + 1, path)
        nodes[:] = kept

    assign_depth(roots, 0, "")
    return roots, warns


def drop_empty_branch(roots: list[Node], title: str, tree_key: str, warns: list[Warn]) -> None:
    kept: list[Node] = []
    for n in roots:
        if n.title == title and not n.children and not n.content:
            warns.append(
                Warn(
                    "EMPTY_BRANCH_REMOVED",
                    tree_key,
                    n.title,
                    f"已删除空分支「{title}」",
                )
            )
            continue
        kept.append(n)
    roots[:] = kept


def iter_paths(roots: list[Node], parent: str = "") -> list[str]:
    out: list[str] = []
    for n in roots:
        path = f"{parent}/{n.title}" if parent else n.title
        out.append(path)
        out.extend(iter_paths(n.children, path))
    return out


def max_depth(roots: list[Node]) -> int:
    if not roots:
        return -1
    m = 0
    for n in roots:
        m = max(m, n.depth, max_depth(n.children) if n.children else n.depth)
    return m


def count_nodes(roots: list[Node]) -> int:
    return sum(1 + count_nodes(n.children) for n in roots)


def count_leaves(roots: list[Node]) -> int:
    total = 0
    for n in roots:
        if not n.children:
            total += 1
        else:
            total += count_leaves(n.children)
    return total


def serialize(tree_key: str, roots: list[Node]) -> str:
    lines: list[str] = [f"# {tree_key}", ""]

    def emit(n: Node) -> None:
        title = escape_title(n.title)
        if n.depth == 0:
            lines.append(f"## {title}")
            lines.append("")
        elif n.depth == 1:
            lines.append(f"### {title}")
            lines.append("")
        else:
            indent = "  " * (n.depth - 2)
            lines.append(f"{indent}- {title}")
        if n.content:
            for para in n.content.splitlines():
                lines.append(f"> {para}" if para.strip() else ">")
            lines.append("")
        for c in n.children:
            emit(c)
        if n.depth <= 1:
            # keep blank line after heading blocks when next sibling is heading
            if lines and lines[-1] != "":
                lines.append("")

    for r in roots:
        emit(r)
    while lines and lines[-1] == "":
        lines.pop()
    lines.append("")
    return "\n".join(lines)


def find_by_path(roots: list[Node], path: str) -> Node | None:
    parts = path.split("/")
    cur_list = roots
    cur: Node | None = None
    for part in parts:
        cur = next((n for n in cur_list if n.title == part), None)
        if not cur:
            return None
        cur_list = cur.children
    return cur


def merge_unique_paths(
    target: list[Node],
    source: list[Node],
    tree_key: str,
    warns: list[Warn],
    parent_path: str = "",
) -> int:
    """把 source 中 target 尚不存在的同级节点（含子树）并入 target。返回新增节点数。"""
    added = 0
    target_by_title = {n.title: n for n in target}
    for s in source:
        path = f"{parent_path}/{s.title}" if parent_path else s.title
        if s.title in target_by_title:
            t = target_by_title[s.title]
            added += merge_unique_paths(t.children, s.children, tree_key, warns, path)
        else:
            # clone subtree
            def clone(n: Node, depth: int) -> Node:
                m = Node(
                    id=n.id,
                    parent_id=n.parent_id,
                    title=n.title,
                    content=n.content,
                    sort_order=n.sort_order,
                    depth=depth,
                )
                m.children = [clone(c, depth + 1) for c in n.children]
                return m

            # depth of new node = parent's depth+1; roots have depth 0
            parent_depth = -1
            if parent_path:
                parent = find_by_path(target if False else [], "")  # unused
                # infer from existing siblings
                if target:
                    parent_depth = target[0].depth - 1
            new_depth = parent_depth + 1 if parent_path else 0
            # better: compute from parent_path length
            new_depth = parent_path.count("/") + 1 if parent_path else 0
            cloned = clone(s, new_depth)

            def redepth(n: Node, d: int) -> None:
                n.depth = d
                for c in n.children:
                    redepth(c, d + 1)

            redepth(cloned, new_depth)
            target.append(cloned)
            target.sort(key=lambda x: (x.sort_order, x.title, x.id))
            added += count_nodes([cloned])
            warns.append(
                Warn(
                    "MERGED_FROM_SHENLUN_TIXING",
                    tree_key,
                    path,
                    f"从「申论题型」合并独有子树（+{count_nodes([cloned])} 节点）",
                )
            )
    return added


def write_outputs(
    out_dir: Path,
    tree_key: str,
    md: str,
    roots: list[Node],
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{tree_key}.md"
    path.write_text(md, encoding="utf-8")
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    return {
        "treeKey": tree_key,
        "file": path.name,
        "bytes": path.stat().st_size,
        "nodeCount": count_nodes(roots),
        "leafCount": count_leaves(roots),
        "maxDepth": max_depth(roots),
        "sha256": digest,
    }


def verify_against_db(
    conn: sqlite3.Connection,
    tree_key: str,
    roots: list[Node],
    *,
    expect_node_count: int | None = None,
) -> list[str]:
    errors: list[str] = []
    # rebuild expected paths from DB with parent-chain (ignore stored depth)
    rows = conn.execute(
        "SELECT id, parent_id, title, sort_order FROM knowledge_nodes WHERE tree_key=? ORDER BY sort_order, id",
        (tree_key,),
    ).fetchall()
    by_id = {r["id"]: r for r in rows}
    children: dict[str | None, list] = defaultdict(list)
    for r in rows:
        children[r["parent_id"]].append(r)

    def dedupe_children(pid):
        seen = set()
        out = []
        for r in sorted(children[pid], key=lambda x: (x["sort_order"], x["title"], x["id"])):
            t = (r["title"] or "").strip()
            if t in seen:
                continue
            seen.add(t)
            out.append(r)
        return out

    expected_paths: list[str] = []

    def walk(pid, parent_path: str, depth: int):
        for r in dedupe_children(pid):
            title = (r["title"] or "").strip()
            if not title or title == "-":
                continue
            path = f"{parent_path}/{title}" if parent_path else title
            expected_paths.append(path)
            walk(r["id"], path, depth + 1)

    walk(None, "", 0)

    # For 言语 after dropping 文章阅读, filter expected
    if tree_key == "言语理解与表达":
        expected_paths = [p for p in expected_paths if p != "文章阅读" and not p.startswith("文章阅读/")]

    actual = iter_paths(roots)
    if expect_node_count is not None and len(actual) != expect_node_count:
        errors.append(f"{tree_key}: nodeCount {len(actual)} != expect {expect_node_count}")
    if Counter(actual) != Counter(expected_paths):
        only_exp = sorted(Counter(expected_paths) - Counter(actual))
        only_act = sorted(Counter(actual) - Counter(expected_paths))
        errors.append(
            f"{tree_key}: path multiset mismatch; only_expected={only_exp[:10]} only_actual={only_act[:10]}"
        )
    return errors


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--also-runtime", action="store_true", help=f"同步写到 {RUNTIME_OUT}")
    ap.add_argument(
        "--merge-unique-shenlun-tixing",
        action="store_true",
        help="把「申论题型」独有子树合并进「申论」后丢弃该树",
    )
    ap.add_argument("--verify", action="store_true")
    ap.add_argument(
        "--keep-empty-yuedu",
        action="store_true",
        help="保留「言语理解与表达 / 文章阅读」空分支（默认删除）",
    )
    args = ap.parse_args()

    if not args.db.is_file():
        raise SystemExit(f"数据库不存在: {args.db}")

    conn = open_ro(args.db)
    all_trees = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT tree_key FROM knowledge_nodes ORDER BY tree_key"
        )
    ]
    trees = [t for t in all_trees if not should_skip_tree(t) and t != "申论题型"]
    warns: list[Warn] = []
    forest: dict[str, list[Node]] = {}

    for tk in trees:
        roots, w = load_tree(conn, tk)
        warns.extend(w)
        if tk == "言语理解与表达" and not args.keep_empty_yuedu:
            drop_empty_branch(roots, "文章阅读", tk, warns)
        forest[tk] = roots

    if args.merge_unique_shenlun_tixing and "申论题型" in all_trees and "申论" in forest:
        src, w = load_tree(conn, "申论题型")
        warns.extend(w)
        added = merge_unique_paths(forest["申论"], src, "申论", warns)
        print(f"merged unique from 申论题型: +{added} nodes into 申论")
    elif "申论题型" in all_trees:
        warns.append(
            Warn(
                "TREE_SKIPPED",
                "申论题型",
                "",
                "已跳过整棵「申论题型」（与申论高度重叠）；可用 --merge-unique-shenlun-tixing 合并独有子树",
            )
        )

    # recompute depths after merge
    def redepth(nodes: list[Node], d: int = 0) -> None:
        for n in nodes:
            n.depth = d
            redepth(n.children, d + 1)

    for roots in forest.values():
        redepth(roots, 0)

    manifest = {"sourceDb": str(args.db), "trees": [], "warnings": []}
    for tk, roots in forest.items():
        md = serialize(tk, roots)
        info = write_outputs(args.out, tk, md, roots)
        manifest["trees"].append(info)
        print(
            f"wrote {info['file']}: nodes={info['nodeCount']} leaves={info['leafCount']} "
            f"maxDepth={info['maxDepth']} bytes={info['bytes']}"
        )
        if args.also_runtime:
            write_outputs(RUNTIME_OUT, tk, md, roots)

    # remove stale 申论题型.md in out dirs
    for d in [args.out, RUNTIME_OUT if args.also_runtime else None]:
        if not d:
            continue
        stale = d / "申论题型.md"
        if stale.exists():
            stale.unlink()
            print(f"removed stale {stale}")

    for w in warns:
        manifest["warnings"].append(
            {"code": w.code, "treeKey": w.tree_key, "path": w.path, "message": w.message}
        )
        print(f"WARN [{w.code}] {w.tree_key} {w.path}: {w.message}")

    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifest → {manifest_path}")

    if args.verify:
        errors: list[str] = []
        expect = {
            "申论": None,  # may grow if merged
            "判断推理": 245,
            "数量关系": 206,
            "资料分析": 159,
            "言语理解与表达": 101,  # 102 - 1 empty 文章阅读
        }
        # spot checks
        shenlun = forest["申论"]
        if not find_by_path(
            shenlun,
            "申发论述题/加工要点/书写成文/主体/举例论证/介绍事例方法/叙述故事法/典型故事型事例",
        ):
            errors.append("missing spot path 申发论述题/.../典型故事型事例")
        n = find_by_path(shenlun, "归纳概括题/类型/隐性要素/概括变化/变化分类/主观变化")
        if not n or len(n.children) != 2:
            errors.append("主观变化 children != 2")
        # 注意：有的节点 title 自身含「/」（如「比重/倍数/平均数」），不能按 path 字符串 split
        ziliao_roots = forest["资料分析"]
        parent = next((n for n in ziliao_roots if n.title == "比重/倍数/平均数"), None)
        z = next((c for c in (parent.children if parent else []) if c.title == "现期"), None)
        if not z or z.depth != 1:
            errors.append(
                f"资料分析「比重/倍数/平均数」/「现期」 depth={getattr(z, 'depth', None)} want 1"
            )
        y = find_by_path(forest["言语理解与表达"], "文章阅读")
        if y is not None:
            errors.append("文章阅读 should be removed")

        for tk, roots in forest.items():
            if tk == "申论" and args.merge_unique_shenlun_tixing:
                # only check path consistency vs merged forest, not raw db
                if count_nodes(roots) < 514:
                    errors.append(f"申论 nodes {count_nodes(roots)} < 514 after merge")
                continue
            exp = expect.get(tk)
            if exp is not None and count_nodes(roots) != exp:
                errors.append(f"{tk}: nodes {count_nodes(roots)} != {exp}")
            # parent-chain max depth vs plan
            want_depth = {
                "申论": 7,
                "判断推理": 6,
                "数量关系": 5,
                "资料分析": 5,
                "言语理解与表达": 4,
            }.get(tk)
            if want_depth is not None and max_depth(roots) != want_depth:
                # 言语 after drop still max 4
                errors.append(f"{tk}: maxDepth {max_depth(roots)} != {want_depth}")

        # verify non-merged trees path multiset vs db (with duplicate collapse + 文章阅读 drop)
        for tk in ["判断推理", "数量关系", "资料分析"]:
            errors.extend(verify_against_db(conn, tk, forest[tk], expect_node_count=expect[tk]))
        if not args.merge_unique_shenlun_tixing:
            # 申论: collapse duplicates only (-1 node)
            errs = verify_against_db(conn, "申论", forest["申论"])
            # expected paths after duplicate collapse = 513
            if count_nodes(forest["申论"]) != 513:
                # 514 - 1 duplicate
                errors.append(f"申论 nodes after dedupe want 513 got {count_nodes(forest['申论'])}")
            errors.extend(errs)

        if errors:
            print("VERIFY FAILED:")
            for e in errors:
                print(" -", e)
            raise SystemExit(1)
        print("VERIFY OK")


if __name__ == "__main__":
    main()
