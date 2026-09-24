"""学员端行测真题抽题与判分。"""
from __future__ import annotations

import random
from typing import Any

from sqlalchemy.orm import Session

from app.models.question_bank import (
    ExamPaperUnified,
    Material,
    PaperQuestionPosition,
    QuestionItem,
    QuestionMaterialLink,
    QuestionVersion,
)

HIGH_RISK_FLAGS = {
    "content_mismatch",
    "content_mismatch_needs_source",
    "answer_conflict",
    "answer_mismatch",
    "missing_answer",
    "stem_incomplete",
    "options_incomplete",
    "ocr_error",
    "duplicate_question",
    "section_type_mismatch",
    "media_missing",
    "media_file_absent",
}

MODULES = [
    "政治理论",
    "常识判断",
    "言语理解与表达",
    "数量关系",
    "判断推理",
    "资料分析",
]

PAPER_TYPE_ORDER = ("省级", "市地级", "行政执法类")

PRACTICE_YEARS = (2023, 2024, 2025, 2026)


def _paper_display_title(year: int, paper_type: str) -> str:
    suffix = {
        "省级": "省级",
        "市地级": "市地",
        "行政执法类": "执法",
    }.get(paper_type, paper_type)
    return f"{year} 国考行测·{suffix}"


def _flag_names(raw: list | None) -> list[str]:
    names: list[str] = []
    for item in raw or []:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            name = item.get("flag") or item.get("name") or ""
            if name:
                names.append(str(name))
    return names


def _has_answer(answer: Any) -> bool:
    if answer is None or answer == "":
        return False
    if isinstance(answer, list):
        return any(str(x).strip() for x in answer)
    return bool(str(answer).strip())


def _needs_missing_figure(version: QuestionVersion) -> bool:
    media = version.media_json or []
    has_media = isinstance(media, list) and len(media) > 0
    options = version.options_json
    if not options and not has_media:
        return True
    if not options and has_media:
        return True
    return False


def _is_practiceable(item: QuestionItem, version: QuestionVersion, flags: list[str]) -> bool:
    if item.origin_type != "real" or item.subject != "行测":
        return False
    if item.lifecycle_status not in ("active", "approved"):
        return False
    if not _has_answer(version.correct_answer_json):
        return False
    if any(flag in HIGH_RISK_FLAGS for flag in flags):
        return False
    if _needs_missing_figure(version):
        return False
    return True


def _normalize_options(options: Any) -> list[tuple[str, str]]:
    if not options:
        return []
    if isinstance(options, dict):
        keys = sorted(options.keys(), key=lambda k: (len(str(k)), str(k)))
        return [(str(k), str(options[k] or "")) for k in keys]
    if isinstance(options, list):
        letters = "ABCDEFGH"
        out: list[tuple[str, str]] = []
        for idx, item in enumerate(options):
            out.append((letters[idx] if idx < len(letters) else str(idx + 1), str(item)))
        return out
    return []


def _option_labels(pairs: list[tuple[str, str]]) -> list[str]:
    return [f"{letter}. {text}" if text else letter for letter, text in pairs]


def _answer_labels(answer: Any, pairs: list[tuple[str, str]]) -> str | list[str]:
    lookup = {letter: f"{letter}. {text}" if text else letter for letter, text in pairs}
    values = {text: f"{letter}. {text}" if text else letter for letter, text in pairs}

    def one(raw: Any) -> str:
        token = str(raw).strip()
        if token in lookup:
            return lookup[token]
        if token in values:
            return values[token]
        if len(token) == 1 and token.upper() in lookup:
            return lookup[token.upper()]
        return token

    if isinstance(answer, list):
        return [one(x) for x in answer]
    text = str(answer).strip()
    if len(text) >= 2 and text.isalpha() and all(ch.upper() in lookup for ch in text):
        return [one(ch.upper()) for ch in text]
    return one(text)


def _materials_for(db: Session, question_id: str) -> str:
    links = (
        db.query(QuestionMaterialLink, Material)
        .join(Material, Material.id == QuestionMaterialLink.material_id)
        .filter(QuestionMaterialLink.question_id == question_id)
        .order_by(QuestionMaterialLink.sort_order.asc())
        .all()
    )
    chunks: list[str] = []
    for _link, material in links:
        title = (material.title or "").strip()
        content = (material.content or "").strip()
        if title and content:
            chunks.append(f"{title}\n{content}")
        elif content:
            chunks.append(content)
        elif title:
            chunks.append(title)
    return "\n\n".join(chunks)


def _to_public(db: Session, item: QuestionItem, version: QuestionVersion) -> dict:
    pairs = _normalize_options(version.options_json)
    labels = _option_labels(pairs)
    response = item.response_type or "single"
    qtype = response if response in ("single", "multiple", "judge") else "single"
    correct = _answer_labels(version.correct_answer_json, pairs)
    if qtype == "judge" and not labels:
        labels = ["正确", "错误"]
        raw = str(version.correct_answer_json).strip()
        if raw in ("对", "正确", "T", "√"):
            correct = "正确"
        elif raw in ("错", "错误", "F", "×"):
            correct = "错误"
    material = _materials_for(db, item.id)
    return {
        "id": item.id,
        "articleId": "",
        "type": qtype,
        "stem": version.stem or "",
        "options": labels,
        "correctAnswer": correct,
        "analysis": version.explanation or "",
        "sourceSentence": material,
        "module": item.module,
        "subtype": item.subtype,
    }


def _candidate_rows(db: Session, module: str | None, year: int | None, paper_type: str | None):
    query = (
        db.query(QuestionItem, QuestionVersion, PaperQuestionPosition, ExamPaperUnified)
        .join(QuestionVersion, QuestionVersion.id == QuestionItem.current_version_id)
        .join(PaperQuestionPosition, PaperQuestionPosition.question_id == QuestionItem.id)
        .join(ExamPaperUnified, ExamPaperUnified.id == PaperQuestionPosition.paper_id)
        .filter(QuestionItem.origin_type == "real", QuestionItem.subject == "行测")
        .filter(ExamPaperUnified.exam_kind == "国考")
        .filter(ExamPaperUnified.exam_year.in_(PRACTICE_YEARS))
    )
    if module:
        query = query.filter(QuestionItem.module == module)
    if year is not None:
        query = query.filter(ExamPaperUnified.exam_year == year)
    if paper_type:
        query = query.filter(ExamPaperUnified.paper_type == paper_type)
    return query.all()


def _unique_practiceable(rows) -> list[tuple[QuestionItem, QuestionVersion]]:
    seen: set[str] = set()
    out: list[tuple[QuestionItem, QuestionVersion]] = []
    for item, version, pos, _paper in rows:
        if item.id in seen:
            continue
        if not _is_practiceable(item, version, _flag_names(pos.quality_flags_json)):
            continue
        seen.add(item.id)
        out.append((item, version))
    return out


def catalog(db: Session, year: int | None = None, paper_type: str | None = None) -> dict:
    rows = _candidate_rows(db, None, year, paper_type)
    years: set[int] = set()
    paper_types: set[str] = set()
    counts: dict[str, int] = {name: 0 for name in MODULES}
    seen: set[tuple[str, str]] = set()
    paper_ids: dict[tuple[int, str], set[str]] = {}
    unfiltered = year is None and not paper_type

    for item, version, pos, paper in rows:
        if not _is_practiceable(item, version, _flag_names(pos.quality_flags_json)):
            continue
        years.add(paper.exam_year)
        paper_types.add(paper.paper_type)
        if unfiltered:
            pk = (paper.exam_year, paper.paper_type)
            paper_ids.setdefault(pk, set()).add(item.id)
        key = (item.module, item.id)
        if key in seen:
            continue
        seen.add(key)
        if item.module in counts:
            counts[item.module] += 1
        else:
            counts[item.module] = counts.get(item.module, 0) + 1

    modules = [{"key": name, "name": name, "count": counts.get(name, 0)} for name in MODULES]
    extra = [
        {"key": name, "name": name, "count": count}
        for name, count in counts.items()
        if name not in MODULES and count
    ]
    papers_out: list[dict] = []
    if unfiltered:
        for y in sorted({k[0] for k in paper_ids}, reverse=True):
            for pt in PAPER_TYPE_ORDER:
                ids = paper_ids.get((y, pt))
                if ids:
                    papers_out.append(
                        {
                            "year": y,
                            "paperType": pt,
                            "title": _paper_display_title(y, pt),
                            "count": len(ids),
                        }
                    )
    return {
        "modules": modules + extra,
        "years": sorted(years, reverse=True),
        "paperTypes": [name for name in PAPER_TYPE_ORDER if name in paper_types],
        "papers": papers_out,
    }


def pick_questions(
    db: Session,
    module: str,
    year: int | None = None,
    paper_type: str | None = None,
    count: int = 10,
) -> list[dict]:
    rows = _candidate_rows(db, module, year, paper_type)
    pool = _unique_practiceable(rows)
    random.shuffle(pool)
    chosen = pool[: max(1, min(count, 30))]
    return [_to_public(db, item, version) for item, version in chosen]


def grade_answer(db: Session, question_id: str, answer: Any) -> dict | None:
    item = db.get(QuestionItem, question_id)
    if not item or not item.current_version_id:
        return None
    version = db.get(QuestionVersion, item.current_version_id)
    if not version:
        return None
    payload = _to_public(db, item, version)
    correct = payload["correctAnswer"]
    user = answer
    if isinstance(correct, list):
        left = sorted(str(x) for x in (user if isinstance(user, list) else [user]))
        right = sorted(str(x) for x in correct)
        ok = left == right
    else:
        ok = str(user).strip() == str(correct).strip()
    return {
        "correct": ok,
        "analysis": payload["analysis"],
        "correctAnswer": correct,
        "pointsEarned": 2 if ok else 0,
    }
