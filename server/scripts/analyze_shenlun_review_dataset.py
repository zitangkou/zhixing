#!/usr/bin/env python3
"""Summarize an exported admin review dataset into a Markdown calibration report."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DECISIONS = ('approved', 'revision_required', 'rejected')
TYPE_LABELS = {
    'summary': '归纳概括', 'countermeasure': '提出对策',
    'implementation': '贯彻执行', 'essay': '申发论述',
}
ISSUE_LABELS = {
    'source_fidelity': '材料忠实度', 'task_fit': '题型/设问匹配',
    'evidence_support': '证据支撑', 'answer_coverage': '答案覆盖',
    'analysis_quality': '解析教学性', 'format_language': '格式与表达',
    'difficulty': '难度设置', 'other': '其他',
}
SMALL_SAMPLE_THRESHOLD = 10


def read_dataset(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'无法读取 JSON 文件：{exc}') from exc
    if not isinstance(payload, dict) or not isinstance(payload.get('items'), list):
        raise ValueError('文件格式无效：根对象必须包含 items 数组')
    version = payload.get('schema_version', 1)
    if version != 1:
        raise ValueError(f'暂不支持审核样本格式版本：{version}')
    valid: list[dict[str, Any]] = []
    skipped = 0
    for item in payload['items']:
        if not isinstance(item, dict):
            skipped += 1
            continue
        if item.get('decision') not in DECISIONS:
            skipped += 1
            continue
        if not isinstance(item.get('content'), dict):
            skipped += 1
            continue
        valid.append(item)
    if not valid:
        raise ValueError(f'没有可分析的审核样本（跳过 {skipped} 条无效记录）')
    payload['_skipped_records'] = skipped
    return payload, valid


def _rate(numerator: int, denominator: int) -> str:
    return f'{numerator / denominator:.0%}' if denominator else '—'


def _decision_counts(items: list[dict[str, Any]]) -> Counter:
    return Counter(item['decision'] for item in items)


def build_report(payload: dict[str, Any], items: list[dict[str, Any]], source: Path) -> str:
    by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    issue_counts: Counter[str] = Counter()
    for item in items:
        by_rule[str(item.get('generation_rule_version') or 'manual_or_legacy')].append(item)
        by_type[str(item.get('content', {}).get('question_type') or 'unknown')].append(item)
        tags = item.get('issue_tags')
        if isinstance(tags, list):
            issue_counts.update({str(tag) for tag in tags if isinstance(tag, str) and tag.strip()})

    exported_at = payload.get('exported_at') or '未记录'
    distinct_exercises = len({str(item.get('exercise_id')) for item in items if item.get('exercise_id')})
    exported_count = payload.get('count')
    available_count = payload.get('total_available')
    lines = [
        '# 申论教研审核样本复盘', '',
        f'- 来源文件：`{source.name}`',
        f'- 导出时间：{exported_at}',
        f'- 样本格式：v{payload.get("schema_version", 1)}',
        f'- 有效审核事件：{len(items)} 条；涉及题目：{distinct_exercises} 道；无效记录：{payload.get("_skipped_records", 0)} 条',
        '',
        '> 本报告按审核事件统计，同一道题多次审核会分别计数；审核结论和修改率只反映当前导出样本。版本审核事件少于 10 条时仅作线索，不宜据此判断规则优劣。',
        '', '## 按生成规则版本', '',
        '| 规则版本 | 审核事件 | 涉及题目 | 通过 | 退回修改 | 不采用 | 通过率 | 有修改 | 修改率 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    if isinstance(exported_count, int) and isinstance(available_count, int) and exported_count < available_count:
        lines.insert(7, f'> 导出不完整：文件含 {exported_count} 条，当前可用 {available_count} 条。请从后台重新完整导出后再比较。')
    for version, group in sorted(by_rule.items()):
        counts = _decision_counts(group)
        corrected = sum(bool(item.get('corrections_made')) for item in group)
        total = len(group)
        caution = ' ⚠样本少' if total < SMALL_SAMPLE_THRESHOLD else ''
        lines.append(
            f'| {version}{caution} | {total} | {len({str(item.get("exercise_id")) for item in group if item.get("exercise_id")})} | {counts["approved"]} | '
            f'{counts["revision_required"]} | {counts["rejected"]} | '
            f'{_rate(counts["approved"], total)} | {corrected} | {_rate(corrected, total)} |'
        )

    lines.extend(['', '## 按题型', '', '| 题型 | 审核事件 | 通过 | 退回修改 | 不采用 | 通过率 |', '|---|---:|---:|---:|---:|---:|'])
    for question_type, group in sorted(by_type.items()):
        counts = _decision_counts(group)
        total = len(group)
        lines.append(
            f'| {TYPE_LABELS.get(question_type, question_type)} | {total} | '
            f'{counts["approved"]} | {counts["revision_required"]} | '
            f'{counts["rejected"]} | {_rate(counts["approved"], total)} |'
        )

    lines.extend(['', '## 高频问题维度', ''])
    if issue_counts:
        lines.extend(['| 问题维度 | 标注次数 |', '|---|---:|'])
        lines.extend(f'| {ISSUE_LABELS.get(tag, tag)} | {count} |' for tag, count in issue_counts.most_common())
    else:
        lines.append('样本未包含问题维度标注。')

    lines.extend(['', '## 复盘提示', ''])
    if any(len(group) < SMALL_SAMPLE_THRESHOLD for group in by_rule.values()):
        lines.append('- 有规则版本样本少于 10 条；先积累更多人工审核，再比较版本变化。')
    if not any(item.get('generation_rule_version') for item in items):
        lines.append('- 当前样本缺少生成规则版本，无法评估规则版本迭代效果。')
    if not issue_counts:
        lines.append('- 审核时建议尽量选择问题维度并写清可执行修改意见，便于定位提示词、题型标准或证据校验中的具体缺口。')
    lines.append('- 对照退回样本中的题目、材料证据、答案和解析，再决定是否调整规则；不要仅凭单项通过率自动放宽硬性质量门。')
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path, help='管理后台导出的审核样本 JSON 文件')
    parser.add_argument('-o', '--output', type=Path, help='报告路径（默认与输入文件同目录）')
    args = parser.parse_args()
    try:
        payload, items = read_dataset(args.dataset)
        output = args.output or args.dataset.with_name(f'{args.dataset.stem}-复盘.md')
        output.write_text(build_report(payload, items, args.dataset), encoding='utf-8')
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f'已生成：{output}（{len(items)} 条有效样本）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
