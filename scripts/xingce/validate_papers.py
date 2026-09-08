#!/usr/bin/env python3
"""行测真题数据校验（schema v2 不变式）。

规范定义见 xingce-structured-data/_schema/conventions.md。
只读，不修改任何文件；发现问题以非零退出码返回，可直接挂 CI。

用法：
    python3 scripts/xingce/validate_papers.py            # 校验全部年份
    python3 scripts/xingce/validate_papers.py --year 2025
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_papers import needs_enumeration  # 复用规则，避免两处漂移

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "xingce-structured-data"
PAPERS = ("shengji", "shidi", "xingzhengzhifa")
VOCAB_FILE = DATA / "_schema" / "topic-vocabulary.json"


def load_vocab() -> dict:
    if not VOCAB_FILE.exists():
        return {}
    return json.loads(VOCAB_FILE.read_text(encoding="utf-8")).get("topics", {})


VOCAB = load_vocab()

SECTION_TYPES = {
    "政治理论": {"政治理论"},
    "常识判断": {"常识判断"},
    "言语理解与表达": {"选词填空", "片段阅读", "语句排序", "语句填空", "标题选择", "文章阅读"},
    "数量关系": {"数量关系"},
    "判断推理": {"图形推理", "定义判断", "类比推理", "逻辑判断"},
    "资料分析": {"资料分析"},
}
ROLES = {"main", "shared", "province_only", "shared_with_shidi",
         "diff_book", "mapped_from_shidi", "backfilled", "unknown"}
OPTION_KEYS = {"A", "B", "C", "D"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, scope: str, msg: str) -> None:
        self.errors.append(f"[{scope}] {msg}")

    def warn(self, scope: str, msg: str) -> None:
        self.warnings.append(f"[{scope}] {msg}")


def validate_paper(path: Path, rep: Report, stats: Counter) -> dict:
    scope = f"{path.parts[-4]}/{path.name}"
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema_version") != 2:
        rep.err(scope, f"schema_version={doc.get('schema_version')}，应为 2（先跑 normalize_papers.py）")
        return doc

    base = path.parent.parent          # {YEAR}/xingce/
    sections = doc.get("sections", [])
    total = 0
    all_numbers: list[int] = []

    # 顶层 materials 字段（dict，key 为 material id）——D6a 新增
    paper_material_ids = set((doc.get("materials") or {}).keys())

    for s in sections:
        name = s.get("name", "")
        if name not in SECTION_TYPES:
            rep.err(scope, f"未知模块 name={name!r}")
            continue
        questions = s.get("questions", [])
        declared = s.get("question_count")
        if declared != len(questions):
            rep.err(scope, f"{name}: question_count={declared} 与实际 {len(questions)} 不符")
        total += len(questions)

        # 模块级 materials（list of {id,...}）+ 顶层 materials dict 合并
        section_material_ids = {m.get("id") for m in (s.get("materials") or [])}
        material_ids = section_material_ids | paper_material_ids
        numbers = [q.get("number") for q in questions]
        all_numbers.extend(n for n in numbers if isinstance(n, int))

        # 模块内题号唯一且连续
        dup = [n for n, c in Counter(numbers).items() if c > 1]
        if dup:
            rep.err(scope, f"{name}: 模块内题号重复 {sorted(dup)}")
        nums = sorted(n for n in numbers if isinstance(n, int))
        if nums and nums != list(range(nums[0], nums[-1] + 1)):
            rep.err(scope, f"{name}: 题号不连续 {nums[0]}–{nums[-1]}")

        for q in questions:
            qnum = q.get("number")
            where = f"{scope} {name}#{qnum}"
            flags = set(q.get("flags") or [])

            def issue(cond_ok: bool, flag: str, msg: str) -> None:
                """cond_ok 为真即通过；否则：已登记该 flag 记警告，未登记记错误。"""
                if cond_ok:
                    return
                (rep.warn if flag in flags else rep.err)(
                    where, msg + ("" if flag in flags else "（未登记 flag，需修复或补登记）"))

            if q.get("section") != name:
                rep.err(where, f"section={q.get('section')!r} 与所属模块 {name!r} 不一致")

            # type 枚举 + 与模块匹配（错配题若已登记 section_type_mismatch 则降级）
            qtype = q.get("type")
            issue(qtype in SECTION_TYPES[name], "section_type_mismatch",
                  f"type={qtype!r} 不在模块 {name} 的允许集合 {sorted(SECTION_TYPES[name])}")

            # options / 媒体硬约束
            options = q.get("options")
            media_paths = [m.get("path", "") for m in (q.get("media") or [])]
            if options is None:
                if not q.get("options_in_media"):
                    rep.err(where, "options 为 null 但 options_in_media 非 true")
                issue(bool(media_paths), "media_missing", "options 为 null 且无 media，题目不可作答")
            else:
                if not isinstance(options, dict):
                    rep.err(where, f"options 应为对象，实际 {type(options).__name__}")
                elif set(options) != OPTION_KEYS:
                    rep.err(where, f"options 键应为 A/B/C/D，实际 {sorted(options)}")
                elif any(not str(v).strip() for v in options.values()):
                    rep.err(where, "options 存在空选项")

            for p in media_paths:
                if not p.startswith("media/"):
                    rep.err(where, f"media 路径未以 media/ 开头：{p!r}")
                else:
                    issue((base / p).exists(), "media_file_absent", f"media 文件不存在：{p}")

            # 答案约束（未入库时 null 是允许的，由 flags 统计）
            answer = q.get("answer")
            if answer and isinstance(options, dict):
                letters = set(str(answer))
                if not letters <= set(options):
                    rep.err(where, f"answer={answer!r} 含 options 之外的字母")

            prov = q.get("provenance") or {}
            if prov.get("role") not in ROLES:
                rep.err(where, f"provenance.role={prov.get('role')!r} 非法")
            if "raw_note" not in prov:
                rep.err(where, "provenance 缺少 raw_note（v1 原文必须保留）")

            dangling = [m for m in (q.get("material_ids") or []) if m not in material_ids]
            issue(not dangling, "material_ref_dangling",
                  f"material_ids={dangling} 在本模块 materials 中不存在（材料可能漏提取）")

            # 列举设问必须有条目正文（items 或材料），否则题目不完整
            if needs_enumeration(q) and not q.get("items") and not q.get("material_ids"):
                issue(False, "enumeration_missing",
                      "题干以「相符的有：」「正确的有几项？」收尾，但既无 items 也无材料引用，条目正文缺失")

            # 考点标签受控词表（未标注时不报错，由覆盖率统计反映）
            topic, tag = q.get("topic"), q.get("tag")
            if topic and topic not in VOCAB:
                rep.err(where, f"topic={topic!r} 不在 _schema/topic-vocabulary.json 中")
            elif tag and tag not in (VOCAB.get(topic) or []):
                rep.err(where, f"tag={tag!r} 不在 topic={topic!r} 的专题列表内")
            if q.get("answer"):
                stats["answer_ok"] += 1
            if topic and tag:
                stats["tagged"] += 1
            stats["questions"] += 1

    # 全卷题号 1..N 连续
    if all_numbers and sorted(all_numbers) != list(range(1, len(all_numbers) + 1)):
        missing = set(range(1, len(all_numbers) + 1)) - set(all_numbers)
        rep.err(scope, f"全卷题号非 1..N 连续，缺失 {sorted(missing)[:12]}")

    if doc.get("actual_question_count") != total:
        rep.err(scope, f"actual_question_count={doc.get('actual_question_count')} 与实算 {total} 不符")

    # modules 区间自洽
    for m in doc.get("modules", []):
        sec = next((s for s in sections if s.get("name") == m.get("name")), None)
        if not sec:
            rep.err(scope, f"modules 中的 {m.get('name')} 在 sections 里不存在")
            continue
        nums = sorted(q["number"] for q in sec["questions"] if isinstance(q.get("number"), int))
        if nums and list(m.get("number_range") or []) != [nums[0], nums[-1]]:
            rep.err(scope, f"modules[{m['name']}].number_range={m.get('number_range')} "
                           f"与实际 {nums[0]}–{nums[-1]} 不符")

    # 卷内重复
    keys = Counter(json.dumps([str(q.get("stem", ""))[:200], q.get("options"), q.get("items"),
                               sorted(x["path"] for x in q.get("media") or [])],
                              ensure_ascii=False, sort_keys=True)
                   for s in sections for q in s["questions"])
    for k, c in keys.items():
        if c > 1:
            rep.warn(scope, f"卷内重复题 {c} 次：{json.loads(k)[0][:40]}…")
    return doc


def validate_catalog(rep: Report) -> None:
    f = DATA / "catalog.json"
    if not f.exists():
        rep.err("catalog", "catalog.json 不存在")
        return
    cat = json.loads(f.read_text(encoding="utf-8"))
    for entry in cat.get("years", []):
        for paper in entry.get("papers", []):
            path = DATA / paper["file"]
            if not path.exists():
                rep.err("catalog", f"{paper['file']} 登记但文件不存在")
                continue
            doc = json.loads(path.read_text(encoding="utf-8"))
            actual = doc.get("actual_question_count")
            if actual != paper.get("total_questions"):
                rep.err("catalog", f"{paper['file']} catalog 记 {paper.get('total_questions')} "
                                   f"但实际 {actual}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", help="只校验指定年份")
    args = ap.parse_args()

    rep = Report()
    stats: Counter = Counter()
    checked = 0
    for year_dir in sorted(DATA.glob("20*")):
        if args.year and year_dir.name != args.year:
            continue
        for paper in PAPERS:
            f = year_dir / "xingce" / "papers" / f"{paper}.json"
            if f.exists():
                validate_paper(f, rep, stats)
                checked += 1
    validate_catalog(rep)

    total = stats["questions"]
    print(f"校验 {checked} 个卷文件，共 {total} 题")
    if total:
        print(f"  答案覆盖率：{stats['answer_ok']}/{total} = {stats['answer_ok'] / total:.1%}")
        print(f"  考点标签覆盖率：{stats['tagged']}/{total} = {stats['tagged'] / total:.1%}")
    for w in rep.warnings:
        print(f"  ⚠️  {w}")
    for e in rep.errors:
        print(f"  ❌ {e}")
    print(f"\n错误 {len(rep.errors)} 项，警告 {len(rep.warnings)} 项")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
