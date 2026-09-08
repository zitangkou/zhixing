#!/usr/bin/env python3
"""
D12 导出层 — 国考行测真题导出为 xlsx / Anki / Markdown 三种格式。

数据源：xingce-structured-data/{year}/xingce/papers/{paper_id}.json
答案覆盖以 DATA_STATUS.md 为准（2025/2024 全量、2023 95.2%，2020-2022 待接入）；缺答案年份输出统一占位符，禁止编造。

用法：
  python3 scripts/xingce/export_questions.py --format all
  python3 scripts/xingce/export_questions.py --format xlsx --year 2025
  python3 scripts/xingce/export_questions.py --format anki
  python3 scripts/xingce/export_questions.py --format md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

# ── 路径常量 ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "xingce-structured-data"
CATALOG_PATH = DATA_ROOT / "catalog.json"
EXPORT_DIR = DATA_ROOT / "export"
MD_DIR = EXPORT_DIR / "markdown"

ANSWER_MISSING_XLSX = "[answer_missing]"
ANSWER_MISSING_ANKI = "[答案待接入]"
ANSWER_MISSING_MD = "[待接入]"

PAPER_ID_TO_LABEL = {
    "shengji": "省级",
    "shidi": "市地级",
    "xingzhengzhifa": "行政执法类",
}


# ── 数据加载 ──────────────────────────────────────────────
def load_catalog() -> dict[str, Any]:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_paper(year: int, paper_id: str) -> dict[str, Any]:
    path = DATA_ROOT / str(year) / "xingce" / "papers" / f"{paper_id}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def flatten_questions(paper: dict[str, Any]) -> list[dict[str, Any]]:
    """将 sections[].questions[] 拍平为一维列表，保留 section 名。"""
    flat: list[dict[str, Any]] = []
    for sec in paper.get("sections", []):
        sec_name = sec.get("name", "")
        for q in sec.get("questions", []):
            q["_section"] = sec_name
            flat.append(q)
    return flat


def is_answer_present(q: dict[str, Any]) -> bool:
    ans = q.get("answer")
    return ans is not None and str(ans).strip() != ""


def safe_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    if isinstance(val, list):
        return "\n".join(str(x) for x in val) if val else default
    return str(val)


def format_items(items: Any) -> str:
    """组合条目（多选/不定项的 ①②③④ 列表）转为换行文本。"""
    if not items:
        return ""
    if isinstance(items, list):
        return "\n".join(str(x) for x in items)
    return str(items)


def format_options(options: Any) -> dict[str, str]:
    """options dict → {A:..., B:..., C:..., D:...}，缺失填空。"""
    result = {"A": "", "B": "", "C": "", "D": ""}
    if isinstance(options, dict):
        for k in ("A", "B", "C", "D"):
            result[k] = safe_str(options.get(k, ""))
    return result


def format_flags(flags: Any) -> str:
    if not flags:
        return ""
    if isinstance(flags, list):
        return ",".join(str(x) for x in flags)
    return str(flags)


def stem_with_material_prefix(q: dict[str, Any]) -> str:
    """材料题在题干前标注 [材料题]。"""
    stem = safe_str(q.get("stem", ""))
    mids = q.get("material_ids") or []
    if mids:
        return f"[材料题] {stem}"
    return stem


# ── xlsx 导出 ─────────────────────────────────────────────
def export_xlsx(papers: list[tuple[int, str, dict[str, Any]]]) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXPORT_DIR / "xingce_all_questions.xlsx"

    wb = Workbook()
    wb.remove(wb.active)

    headers = [
        "题号", "模块", "细题型", "题干", "组合条目",
        "选项A", "选项B", "选项C", "选项D",
        "答案", "解析", "考点", "标签", "质量标记", "来源卷",
    ]
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="D0021B", end_color="D0021B", fill_type="solid")
    wrap_align = Alignment(wrap_text=True, vertical="top")

    for year, paper_id, paper in papers:
        label = PAPER_ID_TO_LABEL.get(paper_id, paper_id)
        sheet_name = f"{year}-{label}"[:31]
        ws = wb.create_sheet(title=sheet_name)

        # 表头
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")

        questions = flatten_questions(paper)
        source_label = f"{year}-{label}"

        for row_idx, q in enumerate(questions, 2):
            opts = format_options(q.get("options"))
            ans_present = is_answer_present(q)
            answer_val = safe_str(q.get("answer"), ANSWER_MISSING_XLSX) if ans_present else ANSWER_MISSING_XLSX
            expl_val = safe_str(q.get("explanation"), ANSWER_MISSING_XLSX) if ans_present else ANSWER_MISSING_XLSX

            row_data = [
                q.get("number", ""),
                q.get("_section", ""),
                safe_str(q.get("subtype"), ""),
                stem_with_material_prefix(q),
                format_items(q.get("items")),
                opts["A"], opts["B"], opts["C"], opts["D"],
                answer_val,
                expl_val,
                safe_str(q.get("topic"), ""),
                safe_str(q.get("tag"), ""),
                format_flags(q.get("flags")),
                source_label,
            ]
            for col_idx, val in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.alignment = wrap_align

        # 列宽自适应（基于内容长度估算，设上限）
        col_widths = [6, 12, 18, 60, 40, 30, 30, 30, 30, 8, 60, 18, 18, 16, 14]
        for col_idx, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = w

        # 冻结首行
        ws.freeze_panes = "A2"

    wb.save(out_path)
    return out_path


# ── Anki 导出 ─────────────────────────────────────────────
def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_anki(papers: list[tuple[int, str, dict[str, Any]]]) -> tuple[Path, Path]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    txt_path = EXPORT_DIR / "anki_xingce_import.txt"
    readme_path = EXPORT_DIR / "anki_import_README.md"

    lines: list[str] = []
    total = 0

    for year, paper_id, paper in papers:
        label = PAPER_ID_TO_LABEL.get(paper_id, paper_id)
        questions = flatten_questions(paper)

        for q in questions:
            opts = format_options(q.get("options"))
            ans_present = is_answer_present(q)
            answer_text = safe_str(q.get("answer"), ANSWER_MISSING_ANKI) if ans_present else ANSWER_MISSING_ANKI
            expl_text = safe_str(q.get("explanation"), ANSWER_MISSING_ANKI) if ans_present else ANSWER_MISSING_ANKI

            stem = _html_escape(stem_with_material_prefix(q))
            items_text = _html_escape(format_items(q.get("items")))
            section = _html_escape(q.get("_section", ""))

            # 正面
            front_parts = [
                f"<b>{year}-{label}-Q{q.get('number', '')}</b> [{section}]<br><br>",
                stem,
            ]
            if items_text:
                front_parts.append(f"<br><br>{items_text.replace(chr(10), '<br>')}")
            front_parts.append("<br><br>")
            front_parts.append(f"A. {_html_escape(opts['A'])}<br>")
            front_parts.append(f"B. {_html_escape(opts['B'])}<br>")
            front_parts.append(f"C. {_html_escape(opts['C'])}<br>")
            front_parts.append(f"D. {_html_escape(opts['D'])}")
            front = "".join(front_parts).replace("\n", "<br>")

            # 背面
            back = (
                f"<b>答案：{_html_escape(answer_text)}</b><br><br>"
                f"{_html_escape(expl_text).replace(chr(10), '<br>')}"
            ).replace("\n", "<br>")

            # 标签
            tag_section = q.get("_section", "").replace(" ", "_")
            tag_label = label.replace(" ", "_")
            tags = f"xingce::{year}::{tag_label}::{tag_section}"

            # 制表符分隔：正面 | 背面 | 标签
            lines.append(f"{front}\t{back}\t{tags}")
            total += 1

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # README
    readme = f"""# Anki 导入说明 — 国考行测真题

## 文件
- `anki_xingce_import.txt`：制表符分隔，共 {total} 张卡片，UTF-8 编码，无表头。

## 导入步骤
1. 打开 Anki → 文件 → 导入 → 选择 `anki_xingce_import.txt`
2. 类型：**基础（含反向可选）** 或 **基础**
3. 字段分隔符：**制表符**
4. 允许在字段中使用 HTML：**勾选**
5. 字段映射：
   - 字段 1 → 正面（Front）
   - 字段 2 → 背面（Back）
   - 字段 3 → 标签（Tags）
6. 点击导入。

## 卡片模板建议
- 正面样式：题干 + 选项（已含 HTML 加粗与换行）
- 背面样式：答案 + 解析
- 建议开启"显示答案后自动播放音频"（如有）
- 卡片间隔默认即可，新卡每天 20-30 张为宜。

## 标签体系
```
xingce::{{年份}}::{{卷种}}::{{模块}}
```
示例：
- `xingce::2025::省级::政治理论`
- `xingce::2024::市地级::言语理解与表达`
- `xingce::2023::行政执法类::资料分析`

可在 Anki 中按标签筛选、构建子牌组或自定义学习计划。

## 答案覆盖率
- 2025 三卷：答案 + 解析完整（395/395）
- 2020-2024 十三卷：答案缺失，背面显示 `{ANSWER_MISSING_ANKI}`，**未编造**
- 后续答案入库后可重新导出覆盖。

## 注意事项
- 材料题（`material_ids` 非空）题干前标注 `[材料题]`，材料原文暂未随卡片导出。
- 图形/图表题（`options_in_media` 或 `media` 非空）可能缺少图片，需对照原卷。
- 导出时间：{date.today().isoformat()}
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme)

    return txt_path, readme_path


# ── Markdown 导出 ─────────────────────────────────────────
def export_markdown(papers: list[tuple[int, str, dict[str, Any]]]) -> tuple[list[Path], Path]:
    MD_DIR.mkdir(parents=True, exist_ok=True)
    md_files: list[Path] = []
    index_rows: list[dict[str, Any]] = []

    for year, paper_id, paper in papers:
        label = PAPER_ID_TO_LABEL.get(paper_id, paper_id)
        year_dir = MD_DIR / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)
        md_path = year_dir / f"{label}.md"

        questions = flatten_questions(paper)
        total_q = len(questions)
        answered = sum(1 for q in questions if is_answer_present(q))
        coverage = (answered / total_q * 100) if total_q else 0

        # 按模块分组
        sections_order: list[str] = []
        sections_map: dict[str, list[dict[str, Any]]] = {}
        for q in questions:
            sec = q.get("_section", "未分类")
            if sec not in sections_map:
                sections_map[sec] = []
                sections_order.append(sec)
            sections_map[sec].append(q)

        lines: list[str] = []
        lines.append(f"# {year}国考行测{label}真题")
        lines.append("")
        lines.append(
            f"> 题量：{total_q}题 ｜ 答案覆盖率：{coverage:.0f}% ｜ "
            f"导出时间：{date.today().isoformat()}"
        )
        lines.append("")

        for sec in sections_order:
            sec_qs = sections_map[sec]
            lines.append(f"## {sec}（{len(sec_qs)}题）")
            lines.append("")

            for q in sec_qs:
                opts = format_options(q.get("options"))
                ans_present = is_answer_present(q)
                answer_text = safe_str(q.get("answer"), ANSWER_MISSING_MD) if ans_present else ANSWER_MISSING_MD
                expl_text = safe_str(q.get("explanation"), ANSWER_MISSING_MD) if ans_present else ANSWER_MISSING_MD
                subtype = safe_str(q.get("subtype"), "")
                num = q.get("number", "")

                lines.append(f"### Q{num} [{subtype}]")
                lines.append("")
                lines.append(stem_with_material_prefix(q))
                lines.append("")

                items_text = format_items(q.get("items"))
                if items_text:
                    for item_line in items_text.split("\n"):
                        lines.append(f"{item_line}")
                    lines.append("")

                lines.append(f"- A. {opts['A']}")
                lines.append(f"- B. {opts['B']}")
                lines.append(f"- C. {opts['C']}")
                lines.append(f"- D. {opts['D']}")
                lines.append("")
                lines.append(f"**答案：{answer_text}**")
                lines.append("")
                lines.append(f"**解析：** {expl_text}")
                lines.append("")
                lines.append("---")
                lines.append("")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        md_files.append(md_path)
        index_rows.append({
            "year": year,
            "label": label,
            "paper_id": paper_id,
            "total": total_q,
            "answered": answered,
            "coverage": coverage,
            "sections": [(s, len(sections_map[s])) for s in sections_order],
            "rel_path": f"{year}/{label}.md",
        })

    # 总索引 README
    readme_path = MD_DIR / "README.md"
    readme_lines: list[str] = []
    readme_lines.append("# 国考行测真题 Markdown 导出索引")
    readme_lines.append("")
    readme_lines.append(f"> 共 {len(index_rows)} 卷，总题量 {sum(r['total'] for r in index_rows)} 题，导出时间：{date.today().isoformat()}")
    readme_lines.append("")

    # 按年份分组
    years_sorted = sorted(set(r["year"] for r in index_rows), reverse=True)
    for yr in years_sorted:
        yr_rows = [r for r in index_rows if r["year"] == yr]
        yr_total = sum(r["total"] for r in yr_rows)
        yr_answered = sum(r["answered"] for r in yr_rows)
        yr_cov = (yr_answered / yr_total * 100) if yr_total else 0
        readme_lines.append(f"## {yr}年（{len(yr_rows)}卷，{yr_total}题，答案覆盖率 {yr_cov:.0f}%）")
        readme_lines.append("")
        readme_lines.append("| 卷种 | 题量 | 答案数 | 覆盖率 | 链接 |")
        readme_lines.append("|------|------|--------|--------|------|")
        for r in yr_rows:
            readme_lines.append(
                f"| {r['label']} | {r['total']} | {r['answered']} | "
                f"{r['coverage']:.0f}% | [{r['label']}.md]({r['rel_path']}) |"
            )
        readme_lines.append("")

        # 模块明细
        readme_lines.append("**模块题量明细：**")
        readme_lines.append("")
        for r in yr_rows:
            sec_str = "、".join(f"{s}({n})" for s, n in r["sections"])
            readme_lines.append(f"- **{r['label']}**：{sec_str}")
        readme_lines.append("")

    readme_lines.append("---")
    readme_lines.append("")
    readme_lines.append("## 说明")
    readme_lines.append("")
    readme_lines.append("- 2025 三卷答案 + 解析完整导出。")
    readme_lines.append(f"- 2020-2024 十三卷答案缺失，答案/解析行显示 `{ANSWER_MISSING_MD}`，**未编造**。")
    readme_lines.append("- 材料题（`material_ids` 非空）题干前标注 `[材料题]`。")
    readme_lines.append("- 所有文件 UTF-8 编码，长文本不截断。")
    readme_lines.append("")

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(readme_lines))

    return md_files, readme_path


# ── 主流程 ────────────────────────────────────────────────
def collect_papers(year_filter: int | None = None) -> list[tuple[int, str, dict[str, Any]]]:
    catalog = load_catalog()
    papers: list[tuple[int, str, dict[str, Any]]] = []
    for yr_entry in catalog.get("years", []):
        yr = yr_entry["year"]
        if year_filter is not None and yr != year_filter:
            continue
        for p in yr_entry.get("papers", []):
            paper_id = p["id"]
            paper = load_paper(yr, paper_id)
            papers.append((yr, paper_id, paper))
    # 按年份升序、卷种固定顺序
    paper_order = {"shengji": 0, "shidi": 1, "xingzhengzhifa": 2}
    papers.sort(key=lambda x: (x[0], paper_order.get(x[1], 99)))
    return papers


def main() -> None:
    parser = argparse.ArgumentParser(description="国考行测真题导出（xlsx/Anki/Markdown）")
    parser.add_argument(
        "--format",
        choices=["xlsx", "anki", "md", "all"],
        default="all",
        help="导出格式（默认 all）",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="指定年份（默认全部 6 年）",
    )
    args = parser.parse_args()

    papers = collect_papers(args.year)
    total_q = sum(len(flatten_questions(p)) for _, _, p in papers)
    print(f"[INFO] 已加载 {len(papers)} 卷，共 {total_q} 题")

    fmt = args.format
    results: list[str] = []

    if fmt in ("xlsx", "all"):
        path = export_xlsx(papers)
        results.append(f"xlsx → {path}")
        print(f"[OK] xlsx 导出完成：{path}")

    if fmt in ("anki", "all"):
        txt_path, readme_path = export_anki(papers)
        results.append(f"anki → {txt_path}")
        results.append(f"anki readme → {readme_path}")
        print(f"[OK] Anki 导出完成：{txt_path}")

    if fmt in ("md", "all"):
        md_files, readme_path = export_markdown(papers)
        results.append(f"markdown → {len(md_files)} 个文件，索引 {readme_path}")
        print(f"[OK] Markdown 导出完成：{len(md_files)} 个文件")

    print("\n=== 导出汇总 ===")
    for r in results:
        print(f"  {r}")


if __name__ == "__main__":
    main()
