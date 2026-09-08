"""资料分析 · 教学资源 + 材料组专项刷题"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    AppUser,
    ExamPaper,
    ExamQuestion,
    ZiliaoFormula,
    ZiliaoPracticeLog,
    ZiliaoQuestionType,
    ZiliaoTrick,
    gen_id,
)
from app.services.activity_service import record_event
from app.schemas import (
    ManualWrongCreate,
    ZiliaoDrillQuestionOut,
    ZiliaoDrillSetDetailOut,
    ZiliaoDrillSetOut,
    ZiliaoDrillSubmitIn,
    ZiliaoDrillSubmitOut,
    ZiliaoDrillWrongItem,
    ZiliaoFormulaCreate,
    ZiliaoFormulaImportResult,
    ZiliaoFormulaOut,
    ZiliaoFormulaUpdate,
    ZiliaoOverviewOut,
    ZiliaoQuestionTypeCreate,
    ZiliaoQuestionTypeOut,
    ZiliaoQuestionTypeUpdate,
    ZiliaoTrickCreate,
    ZiliaoTrickOut,
    ZiliaoTrickUpdate,
    ZiliaoWeakTypeOut,
)
from app.timezone import now

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "ziliao"
SECTION_NAME = "资料分析"
SAMPLE_PAPER_ID = "ziliao_sample_paper"


def _safe_json(s: str | None, default: Any) -> Any:
    if not s:
        return default
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default


def _dumps(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False)


def _bool_value(v: Any, default: bool) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() not in {"0", "false", "no", "off", "否", "不发布"}
    return bool(v)


def _load_json(name: str) -> list[dict]:
    path = DATA_DIR / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _formula_out(row: ZiliaoFormula) -> ZiliaoFormulaOut:
    return ZiliaoFormulaOut(
        id=row.id,
        code=row.code,
        name=row.name,
        category=row.category or "",
        definition=row.definition or "",
        latex=row.latex or "",
        formulaPlain=getattr(row, "formula_plain", None) or "",
        scenarios=row.scenarios or "",
        pitfalls=row.pitfalls or "",
        relatedTypeCodes=_safe_json(row.related_type_codes, []),
        relatedTrickCodes=_safe_json(row.related_trick_codes, []),
        keywords=_safe_json(row.keywords, []),
        examFreq=row.exam_freq or 3,
        sortOrder=row.sort_order or 0,
        isPublished=bool(row.is_published),
    )


def _type_out(row: ZiliaoQuestionType) -> ZiliaoQuestionTypeOut:
    return ZiliaoQuestionTypeOut(
        id=row.id,
        code=row.code,
        name=row.name,
        category=row.category or "",
        description=row.description or "",
        ability=row.ability or "",
        difficulty=row.difficulty or 3,
        examFreq=row.exam_freq or 3,
        formulaCodes=_safe_json(row.formula_codes, []),
        trickCodes=_safe_json(row.trick_codes, []),
        keywords=_safe_json(row.keywords, []),
        sortOrder=row.sort_order or 0,
        isPublished=bool(row.is_published),
    )


def _trick_out(row: ZiliaoTrick) -> ZiliaoTrickOut:
    return ZiliaoTrickOut(
        id=row.id,
        code=row.code,
        name=row.name,
        category=row.category or "",
        principle=row.principle or "",
        whenToUse=row.when_to_use or "",
        whenNot=row.when_not or "",
        errorNote=row.error_note or "",
        formulaCodes=_safe_json(row.formula_codes, []),
        example=row.example or "",
        sortOrder=row.sort_order or 0,
        isPublished=bool(row.is_published),
    )


def _apply_formula_seed(row: ZiliaoFormula, item: dict) -> None:
    row.name = item.get("name", row.code)
    row.category = item.get("category", "")
    row.definition = item.get("definition", "")
    row.latex = item.get("latex", "")
    row.formula_plain = item.get("formulaPlain") or item.get("formula_plain") or ""
    row.scenarios = item.get("scenarios", "")
    row.pitfalls = item.get("pitfalls", "")
    row.related_type_codes = _dumps(item.get("related_type_codes", []))
    row.related_trick_codes = _dumps(item.get("related_trick_codes", []))
    row.keywords = _dumps(item.get("keywords", []))
    row.exam_freq = int(item.get("exam_freq", 3))
    row.sort_order = int(item.get("sort_order", 0))
    row.is_published = True


def seed_ziliao_resources(db: Session, *, force: bool = False) -> dict[str, int]:
    """从 JSON 种子写入公式/题型/技巧；force 时按 code upsert。"""
    counts = {"formulas": 0, "types": 0, "tricks": 0}

    # 公式：空库全量写入；已有则补 latex / formulaPlain（不覆盖 Admin 手改过的正式 LaTeX）
    formula_items = _load_json("formulas.json")
    if force or db.query(ZiliaoFormula).count() == 0:
        for item in formula_items:
            code = item["code"]
            row = db.query(ZiliaoFormula).filter(ZiliaoFormula.code == code).first()
            if row and not force:
                continue
            if not row:
                row = ZiliaoFormula(id=gen_id("zf"), code=code)
                db.add(row)
            _apply_formula_seed(row, item)
            counts["formulas"] += 1
    else:
        for item in formula_items:
            code = item["code"]
            row = db.query(ZiliaoFormula).filter(ZiliaoFormula.code == code).first()
            if not row:
                row = ZiliaoFormula(id=gen_id("zf"), code=code)
                db.add(row)
                _apply_formula_seed(row, item)
                counts["formulas"] += 1
                continue
            plain = getattr(row, "formula_plain", None) or ""
            latex = row.latex or ""
            # 旧种子是中文可读式写在 latex 里，无反斜杠命令 → 升级为真正 LaTeX
            if not plain or ("\\" not in latex and latex.strip()):
                row.latex = item.get("latex", latex)
                row.formula_plain = item.get("formulaPlain") or item.get("formula_plain") or plain or latex
                counts["formulas"] += 1

    if force or db.query(ZiliaoQuestionType).count() == 0:
        for item in _load_json("types.json"):
            code = item["code"]
            row = db.query(ZiliaoQuestionType).filter(ZiliaoQuestionType.code == code).first()
            if row and not force:
                continue
            if not row:
                row = ZiliaoQuestionType(id=gen_id("zt"), code=code)
                db.add(row)
            row.name = item.get("name", code)
            row.category = item.get("category", "")
            row.description = item.get("description", "")
            row.ability = item.get("ability", "")
            row.difficulty = int(item.get("difficulty", 3))
            row.exam_freq = int(item.get("exam_freq", 3))
            row.formula_codes = _dumps(item.get("formula_codes", []))
            row.trick_codes = _dumps(item.get("trick_codes", []))
            row.keywords = _dumps(item.get("keywords", []))
            row.sort_order = int(item.get("sort_order", 0))
            row.is_published = True
            counts["types"] += 1

    if force or db.query(ZiliaoTrick).count() == 0:
        for item in _load_json("tricks.json"):
            code = item["code"]
            row = db.query(ZiliaoTrick).filter(ZiliaoTrick.code == code).first()
            if row and not force:
                continue
            if not row:
                row = ZiliaoTrick(id=gen_id("zk"), code=code)
                db.add(row)
            row.name = item.get("name", code)
            row.category = item.get("category", "")
            row.principle = item.get("principle", "")
            row.when_to_use = item.get("when_to_use", "")
            row.when_not = item.get("when_not", "")
            row.error_note = item.get("error_note", "")
            row.formula_codes = _dumps(item.get("formula_codes", []))
            row.example = item.get("example", "")
            row.sort_order = int(item.get("sort_order", 0))
            row.is_published = True
            counts["tricks"] += 1

    db.commit()
    return counts


def seed_sample_drill_paper(db: Session) -> bool:
    """确保至少有一套带材料的资料分析样例题可练。"""
    existing = db.get(ExamPaper, SAMPLE_PAPER_ID)
    if existing:
        q_count = (
            db.query(ExamQuestion)
            .filter(ExamQuestion.paper_id == SAMPLE_PAPER_ID, ExamQuestion.section == SECTION_NAME)
            .count()
        )
        if q_count > 0:
            return False

    material = (
        "2023年，某市新能源汽车产量为 48 万辆，同比增长 25%；"
        "其中纯电动汽车产量 36 万辆，同比增长 20%。"
        "同年该市汽车总产量 120 万辆，同比增长 10%。"
    )

    if not existing:
        db.add(
            ExamPaper(
                id=SAMPLE_PAPER_ID,
                title="资料分析专项样例（入门）",
                exam_type="custom",
                subject="行测",
                year=2023,
                region="样例",
                level="",
                total_count=3,
                time_limit_min=15,
                tags=_dumps(["资料分析", "样例"]),
                is_published=True,
                is_free=True,
                sort_order=9990,
                description="系统内置联调样例（有真题入库后默认练习池会自动排除）。",
            )
        )
    else:
        existing.total_count = 3
        existing.is_published = True
        existing.sort_order = 9990
        existing.description = "系统内置联调样例（有真题入库后默认练习池会自动排除）。"

    # 清掉旧样例题再写入
    db.query(ExamQuestion).filter(ExamQuestion.paper_id == SAMPLE_PAPER_ID).delete()

    samples = [
        {
            "stem": "2023年该市新能源汽车产量比上年增长了多少万辆？",
            "options": ["8.4", "9.6", "12.0", "14.4"],
            "correct": "B",
            "analysis": "基期=48/1.25=38.4，增长量=48-38.4=9.6。选 B。",
            "tags": ["增长量"],
        },
        {
            "stem": "2023年纯电动汽车产量占新能源汽车产量的比重约为？",
            "options": ["65%", "75%", "80%", "85%"],
            "correct": "B",
            "analysis": "36/48=0.75，即 75%。选 B。",
            "tags": ["比重"],
        },
        {
            "stem": "与上年相比，2023年新能源汽车产量占汽车总产量的比重：",
            "options": ["上升了", "下降了", "基本持平", "无法判断"],
            "correct": "A",
            "analysis": "部分增速 25% > 整体增速 10%，比重上升。选 A。",
            "tags": ["两期比重差"],
        },
    ]
    for i, item in enumerate(samples, start=1):
        db.add(
            ExamQuestion(
                id=gen_id("eq"),
                paper_id=SAMPLE_PAPER_ID,
                section=SECTION_NAME,
                section_index=i,
                sort_order=i,
                type="single",
                material=material,
                stem=item["stem"],
                options=_dumps(item["options"]),
                correct_answer=item["correct"],
                analysis=item["analysis"],
                difficulty=2,
                knowledge_tags=_dumps(item["tags"]),
                knowledge_tree_key="资料分析",
                is_active=True,
            )
        )
    db.commit()
    return True


# ----- CRUD: formulas -----


def list_formulas(db: Session, *, published_only: bool = True) -> list[ZiliaoFormulaOut]:
    q = db.query(ZiliaoFormula)
    if published_only:
        q = q.filter(ZiliaoFormula.is_published.is_(True))
    return [_formula_out(r) for r in q.order_by(ZiliaoFormula.sort_order, ZiliaoFormula.code).all()]


def get_formula(db: Session, formula_id: str) -> ZiliaoFormulaOut | None:
    row = db.get(ZiliaoFormula, formula_id)
    return _formula_out(row) if row else None


def create_formula(db: Session, body: ZiliaoFormulaCreate) -> ZiliaoFormulaOut:
    row = ZiliaoFormula(
        id=gen_id("zf"),
        code=body.code,
        name=body.name,
        category=body.category,
        definition=body.definition,
        latex=body.latex,
        formula_plain=body.formulaPlain,
        scenarios=body.scenarios,
        pitfalls=body.pitfalls,
        related_type_codes=_dumps(body.relatedTypeCodes),
        related_trick_codes=_dumps(body.relatedTrickCodes),
        keywords=_dumps(body.keywords),
        exam_freq=body.examFreq,
        sort_order=body.sortOrder,
        is_published=body.isPublished,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _formula_out(row)


def import_formulas_from_json(
    db: Session,
    content: str,
    *,
    overwrite: bool = True,
    publish_default: bool = True,
) -> ZiliaoFormulaImportResult:
    """Import formula resources from a JSON array or {"formulas": [...]} payload.

    Rows are matched by code. Existing rows are updated when overwrite=True;
    otherwise they are counted as skipped.
    """
    result = ZiliaoFormulaImportResult()
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as e:
        result.errors.append(f"JSON 格式错误：第 {e.lineno} 行第 {e.colno} 列，{e.msg}")
        return result

    if isinstance(raw, dict):
        items = raw.get("formulas")
        if items is None:
            result.errors.append("JSON 对象必须包含 formulas 数组字段")
            return result
    else:
        items = raw

    if not isinstance(items, list):
        result.errors.append("导入内容必须是公式数组，或包含 formulas 数组的对象")
        return result

    result.total = len(items)
    seen_codes: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            result.errors.append(f"第 {index} 条不是对象，已跳过")
            result.skipped += 1
            continue

        code = str(item.get("code") or "").strip()
        name = str(item.get("name") or "").strip()
        if not code:
            result.errors.append(f"第 {index} 条缺少 code，已跳过")
            result.skipped += 1
            continue
        if code in seen_codes:
            result.errors.append(f"第 {index} 条 code「{code}」在本次 JSON 中重复，已跳过")
            result.skipped += 1
            continue
        seen_codes.add(code)
        if not name:
            result.errors.append(f"第 {index} 条 code「{code}」缺少 name，已跳过")
            result.skipped += 1
            continue

        try:
            exam_freq = int(item.get("examFreq") or item.get("exam_freq") or 3)
            sort_order = int(item.get("sortOrder") or item.get("sort_order") or 0)
        except (TypeError, ValueError):
            result.errors.append(f"第 {index} 条 code「{code}」的 examFreq/sortOrder 必须是数字，已跳过")
            result.skipped += 1
            continue

        row = db.query(ZiliaoFormula).filter(ZiliaoFormula.code == code).first()
        is_new = row is None
        if row and not overwrite:
            result.skipped += 1
            continue
        if not row:
            row = ZiliaoFormula(id=gen_id("zf"), code=code)
            db.add(row)
        row.name = name
        row.category = str(item.get("category") or "")
        row.definition = str(item.get("definition") or "")
        row.latex = str(item.get("latex") or "")
        row.formula_plain = str(item.get("formulaPlain") or item.get("formula_plain") or "")
        row.scenarios = str(item.get("scenarios") or "")
        row.pitfalls = str(item.get("pitfalls") or "")
        row.related_type_codes = _dumps(item.get("relatedTypeCodes") or item.get("related_type_codes") or [])
        row.related_trick_codes = _dumps(item.get("relatedTrickCodes") or item.get("related_trick_codes") or [])
        row.keywords = _dumps(item.get("keywords") or [])
        row.exam_freq = exam_freq
        row.sort_order = sort_order
        row.is_published = _bool_value(item.get("isPublished", item.get("is_published")), publish_default)
        if is_new:
            result.inserted += 1
        else:
            result.updated += 1

    if result.inserted or result.updated:
        db.commit()
    else:
        db.rollback()
    return result


def update_formula(db: Session, formula_id: str, body: ZiliaoFormulaUpdate) -> ZiliaoFormulaOut | None:
    row = db.get(ZiliaoFormula, formula_id)
    if not row:
        return None
    data = body.model_dump(exclude_unset=True)
    mapping = {
        "formulaPlain": ("formula_plain", False),
        "relatedTypeCodes": ("related_type_codes", True),
        "relatedTrickCodes": ("related_trick_codes", True),
        "keywords": ("keywords", True),
        "examFreq": ("exam_freq", False),
        "sortOrder": ("sort_order", False),
        "isPublished": ("is_published", False),
    }
    for key, val in data.items():
        if key in mapping:
            col, is_json = mapping[key]
            setattr(row, col, _dumps(val) if is_json else val)
        elif hasattr(row, key):
            setattr(row, key, val)
    db.commit()
    db.refresh(row)
    return _formula_out(row)


def delete_formula(db: Session, formula_id: str) -> bool:
    row = db.get(ZiliaoFormula, formula_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ----- CRUD: types -----


def list_types(db: Session, *, published_only: bool = True) -> list[ZiliaoQuestionTypeOut]:
    q = db.query(ZiliaoQuestionType)
    if published_only:
        q = q.filter(ZiliaoQuestionType.is_published.is_(True))
    return [_type_out(r) for r in q.order_by(ZiliaoQuestionType.sort_order, ZiliaoQuestionType.code).all()]


def get_type(db: Session, type_id: str) -> ZiliaoQuestionTypeOut | None:
    row = db.get(ZiliaoQuestionType, type_id)
    return _type_out(row) if row else None


def get_type_by_code(db: Session, code: str) -> ZiliaoQuestionType | None:
    return db.query(ZiliaoQuestionType).filter(ZiliaoQuestionType.code == code).first()


def create_type(db: Session, body: ZiliaoQuestionTypeCreate) -> ZiliaoQuestionTypeOut:
    row = ZiliaoQuestionType(
        id=gen_id("zt"),
        code=body.code,
        name=body.name,
        category=body.category,
        description=body.description,
        ability=body.ability,
        difficulty=body.difficulty,
        exam_freq=body.examFreq,
        formula_codes=_dumps(body.formulaCodes),
        trick_codes=_dumps(body.trickCodes),
        keywords=_dumps(body.keywords),
        sort_order=body.sortOrder,
        is_published=body.isPublished,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _type_out(row)


def update_type(db: Session, type_id: str, body: ZiliaoQuestionTypeUpdate) -> ZiliaoQuestionTypeOut | None:
    row = db.get(ZiliaoQuestionType, type_id)
    if not row:
        return None
    data = body.model_dump(exclude_unset=True)
    mapping = {
        "formulaCodes": ("formula_codes", True),
        "trickCodes": ("trick_codes", True),
        "keywords": ("keywords", True),
        "examFreq": ("exam_freq", False),
        "sortOrder": ("sort_order", False),
        "isPublished": ("is_published", False),
    }
    for key, val in data.items():
        if key in mapping:
            col, is_json = mapping[key]
            setattr(row, col, _dumps(val) if is_json else val)
        elif hasattr(row, key):
            setattr(row, key, val)
    db.commit()
    db.refresh(row)
    return _type_out(row)


def delete_type(db: Session, type_id: str) -> bool:
    row = db.get(ZiliaoQuestionType, type_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ----- CRUD: tricks -----


def list_tricks(db: Session, *, published_only: bool = True) -> list[ZiliaoTrickOut]:
    q = db.query(ZiliaoTrick)
    if published_only:
        q = q.filter(ZiliaoTrick.is_published.is_(True))
    return [_trick_out(r) for r in q.order_by(ZiliaoTrick.sort_order, ZiliaoTrick.code).all()]


def get_trick(db: Session, trick_id: str) -> ZiliaoTrickOut | None:
    row = db.get(ZiliaoTrick, trick_id)
    return _trick_out(row) if row else None


def create_trick(db: Session, body: ZiliaoTrickCreate) -> ZiliaoTrickOut:
    row = ZiliaoTrick(
        id=gen_id("zk"),
        code=body.code,
        name=body.name,
        category=body.category,
        principle=body.principle,
        when_to_use=body.whenToUse,
        when_not=body.whenNot,
        error_note=body.errorNote,
        formula_codes=_dumps(body.formulaCodes),
        example=body.example,
        sort_order=body.sortOrder,
        is_published=body.isPublished,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _trick_out(row)


def update_trick(db: Session, trick_id: str, body: ZiliaoTrickUpdate) -> ZiliaoTrickOut | None:
    row = db.get(ZiliaoTrick, trick_id)
    if not row:
        return None
    data = body.model_dump(exclude_unset=True)
    mapping = {
        "whenToUse": ("when_to_use", False),
        "whenNot": ("when_not", False),
        "errorNote": ("error_note", False),
        "formulaCodes": ("formula_codes", True),
        "sortOrder": ("sort_order", False),
        "isPublished": ("is_published", False),
    }
    for key, val in data.items():
        if key in mapping:
            col, is_json = mapping[key]
            setattr(row, col, _dumps(val) if is_json else val)
        elif hasattr(row, key):
            setattr(row, key, val)
    db.commit()
    db.refresh(row)
    return _trick_out(row)


def delete_trick(db: Session, trick_id: str) -> bool:
    row = db.get(ZiliaoTrick, trick_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ----- Drill -----


def _material_key(material: str, question_id: str) -> str:
    text = (material or "").strip()
    if text:
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    return f"q_{question_id}"


def make_set_id(paper_id: str, material: str, question_id: str) -> str:
    return f"{paper_id}:{_material_key(material, question_id)}"


def _parse_set_id(set_id: str) -> tuple[str, str] | None:
    if ":" not in set_id:
        return None
    paper_id, mat_hash = set_id.split(":", 1)
    return paper_id, mat_hash


def _answers_equal(user: Any, correct: Any) -> bool:
    def norm(v: Any) -> Any:
        if isinstance(v, list):
            return sorted(str(x).strip().upper() for x in v)
        s = str(v).strip().upper()
        # 字母答案 vs 选项全文：取首字母
        if len(s) == 1 and s.isalpha():
            return s
        return s

    u, c = norm(user), norm(correct)
    if u == c:
        return True
    # 用户选了完整选项文本，正确答案是 A/B/C/D
    if isinstance(c, str) and len(c) == 1 and c.isalpha() and isinstance(user, str):
        return False
    return False


def _letter_answer(user: Any, options: list[str]) -> str:
    if isinstance(user, list):
        return ",".join(str(x) for x in user)
    s = str(user or "").strip()
    if len(s) == 1 and s.isalpha():
        return s.upper()
    for i, opt in enumerate(options):
        if str(opt).strip() == s:
            return chr(ord("A") + i)
    return s


def _has_real_ziliao_questions(db: Session) -> bool:
    """是否存在非样例卷的资料分析题。"""
    row = (
        db.query(ExamQuestion.id)
        .filter(
            ExamQuestion.section == SECTION_NAME,
            ExamQuestion.is_active.is_(True),
            ExamQuestion.paper_id != SAMPLE_PAPER_ID,
        )
        .first()
    )
    return row is not None


def list_drill_sets(
    db: Session,
    *,
    type_code: str | None = None,
    include_sample: bool | None = None,
) -> list[ZiliaoDrillSetOut]:
    """材料组列表。默认：有真题时排除样例卷；无真题时保留样例以便联调。"""
    has_real = _has_real_ziliao_questions(db)
    if include_sample is None:
        include_sample = not has_real

    rows = (
        db.query(ExamQuestion, ExamPaper)
        .join(ExamPaper, ExamPaper.id == ExamQuestion.paper_id)
        .filter(
            ExamQuestion.section == SECTION_NAME,
            ExamQuestion.is_active.is_(True),
            ExamPaper.is_published.is_(True),
        )
        .order_by(ExamPaper.sort_order, ExamQuestion.sort_order)
        .all()
    )

    type_keywords: list[str] = []
    if type_code:
        t = get_type_by_code(db, type_code)
        if t:
            type_keywords = [str(k) for k in _safe_json(t.keywords, [])]

    groups: dict[str, dict[str, Any]] = {}
    for q, paper in rows:
        is_sample = paper.id == SAMPLE_PAPER_ID
        if is_sample and not include_sample:
            continue
        set_id = make_set_id(paper.id, q.material or "", q.id)
        if set_id not in groups:
            preview = (q.material or q.stem or "")[:80]
            groups[set_id] = {
                "setId": set_id,
                "paperId": paper.id,
                "paperTitle": paper.title,
                "materialPreview": preview,
                "questionCount": 0,
                "tags": set(),
                "stems": [],
                "isSample": is_sample,
                "sortOrder": paper.sort_order or 0,
            }
        g = groups[set_id]
        g["questionCount"] += 1
        tags = _safe_json(q.knowledge_tags, [])
        for t in tags:
            g["tags"].add(str(t))
        g["stems"].append(q.stem or "")

    out: list[ZiliaoDrillSetOut] = []
    for g in groups.values():
        hints = sorted(g["tags"])
        blob = " ".join(hints + g["stems"])
        if type_keywords and not any(k in blob for k in type_keywords):
            continue
        out.append(
            ZiliaoDrillSetOut(
                setId=g["setId"],
                paperId=g["paperId"],
                paperTitle=g["paperTitle"],
                materialPreview=g["materialPreview"],
                questionCount=g["questionCount"],
                section=SECTION_NAME,
                typeHints=hints,
                isSample=bool(g["isSample"]),
            )
        )
    # 真题优先，样例垫底
    out.sort(key=lambda x: (1 if x.isSample else 0, x.paperTitle))
    return out


def get_drill_set(db: Session, set_id: str) -> ZiliaoDrillSetDetailOut | None:
    parsed = _parse_set_id(set_id)
    if not parsed:
        return None
    paper_id, mat_hash = parsed
    paper = db.get(ExamPaper, paper_id)
    if not paper or not paper.is_published:
        return None

    qs = (
        db.query(ExamQuestion)
        .filter(
            ExamQuestion.paper_id == paper_id,
            ExamQuestion.section == SECTION_NAME,
            ExamQuestion.is_active.is_(True),
        )
        .order_by(ExamQuestion.sort_order)
        .all()
    )
    matched = [q for q in qs if _material_key(q.material or "", q.id) == mat_hash]
    if not matched:
        return None

    material = matched[0].material or ""
    questions = [
        ZiliaoDrillQuestionOut(
            id=q.id,
            section=q.section or SECTION_NAME,
            sortOrder=q.sort_order,
            type=q.type or "single",
            material=q.material or "",
            stem=q.stem,
            options=_safe_json(q.options, []),
            difficulty=q.difficulty or 3,
        )
        for q in matched
    ]
    return ZiliaoDrillSetDetailOut(
        setId=set_id,
        paperId=paper.id,
        paperTitle=paper.title,
        material=material,
        questions=questions,
    )


def submit_drill(
    db: Session,
    user: AppUser,
    body: ZiliaoDrillSubmitIn,
) -> ZiliaoDrillSubmitOut | None:
    detail = get_drill_set(db, body.setId)
    if not detail:
        return None

    q_map = {
        q.id: db.get(ExamQuestion, q.id)
        for q in detail.questions
    }
    answer_map = {a.questionId: a.userAnswer for a in body.answers}

    correct_count = 0
    wrongs: list[ZiliaoDrillWrongItem] = []
    for q_out in detail.questions:
        q = q_map.get(q_out.id)
        if not q:
            continue
        correct = _safe_json(q.correct_answer, q.correct_answer or "")
        user_ans = answer_map.get(q.id, "")
        options = _safe_json(q.options, [])
        user_letter = _letter_answer(user_ans, options)
        correct_letter = _letter_answer(correct, options) if not isinstance(correct, list) else correct
        ok = _answers_equal(user_letter, correct_letter)
        if ok:
            correct_count += 1
        else:
            wrongs.append(
                ZiliaoDrillWrongItem(
                    questionId=q.id,
                    stem=q.stem,
                    material=q.material or "",
                    options=options,
                    userAnswer=user_letter,
                    correctAnswer=correct_letter,
                    analysis=q.analysis or "",
                )
            )

    total = len(detail.questions)
    today = now().strftime("%Y-%m-%d")
    paper_id = detail.paperId

    type_code = (body.typeCode or "").strip()
    if not type_code:
        # 从题目知识点标签反推题型，便于薄弱推荐
        tag_blob = " "
        for q_out in detail.questions:
            q = q_map.get(q_out.id)
            if not q:
                continue
            tags = _safe_json(q.knowledge_tags, [])
            tag_blob += " ".join(str(t) for t in tags) + " " + (q.stem or "")
        for t in list_types(db):
            kws = t.keywords or []
            if kws and any(k in tag_blob for k in kws):
                type_code = t.code
                break

    db.add(
        ZiliaoPracticeLog(
            id=gen_id("zpl"),
            user_id=user.id,
            set_id=body.setId,
            paper_id=paper_id,
            type_code=type_code,
            total_count=total,
            correct_count=correct_count,
            time_used_sec=body.timeUsedSec,
            practice_date=today,
        )
    )
    db.commit()

    record_event(
        db,
        user.id,
        "drill_done",
        {
            "setId": body.setId,
            "paperId": paper_id,
            "typeCode": type_code,
            "total": total,
            "correct": correct_count,
            "timeUsedSec": body.timeUsedSec,
        },
    )

    saved = 0
    if body.saveWrongs and wrongs:
        from app.services.manual_wrong_service import create_wrong

        for w in wrongs:
            material_note = (w.material or "")[:200]
            analysis = w.analysis or ""
            if material_note:
                analysis = f"【材料】{material_note}\n{analysis}".strip()
            create_wrong(
                db,
                user,
                ManualWrongCreate(
                    subject="资料",
                    questionType="资料分析",
                    stem=w.stem,
                    options=_dumps(w.options) if isinstance(w.options, list) else str(w.options),
                    myAnswer=str(w.userAnswer),
                    correctAnswer=str(w.correctAnswer),
                    analysis=analysis,
                    wrongReason="专项练习",
                    source="ziliao_drill",
                    knowledgeTreeKey="资料分析",
                ),
            )
            saved += 1

    return ZiliaoDrillSubmitOut(
        setId=body.setId,
        totalCount=total,
        correctCount=correct_count,
        timeUsedSec=body.timeUsedSec,
        wrongs=wrongs,
        savedWrongCount=saved,
    )


def _compute_weak_types(db: Session, user_id: str | None, limit: int = 3) -> list[ZiliaoWeakTypeOut]:
    """基于练习日志推荐薄弱题型；无记录则推荐高频未练题型。"""
    types = (
        db.query(ZiliaoQuestionType)
        .filter(ZiliaoQuestionType.is_published.is_(True))
        .order_by(ZiliaoQuestionType.exam_freq.desc(), ZiliaoQuestionType.sort_order)
        .all()
    )
    if not types:
        return []

    stats: dict[str, dict[str, int]] = {}
    if user_id:
        logs = (
            db.query(ZiliaoPracticeLog)
            .filter(ZiliaoPracticeLog.user_id == user_id)
            .order_by(ZiliaoPracticeLog.created_at.desc())
            .limit(200)
            .all()
        )
        for log in logs:
            code = (log.type_code or "").strip()
            if not code:
                continue
            st = stats.setdefault(code, {"attempts": 0, "correct": 0, "total": 0})
            st["attempts"] += 1
            st["correct"] += int(log.correct_count or 0)
            st["total"] += int(log.total_count or 0)

    practiced: list[ZiliaoWeakTypeOut] = []
    unpracticed: list[ZiliaoWeakTypeOut] = []
    for t in types:
        st = stats.get(t.code)
        if st and st["total"] > 0:
            acc = st["correct"] / st["total"]
            practiced.append(
                ZiliaoWeakTypeOut(
                    id=t.id,
                    code=t.code,
                    name=t.name,
                    category=t.category or "",
                    attemptCount=st["attempts"],
                    correctCount=st["correct"],
                    totalCount=st["total"],
                    accuracy=round(acc, 3),
                    reason="正确率偏低" if acc < 0.7 else "可继续巩固",
                )
            )
        else:
            unpracticed.append(
                ZiliaoWeakTypeOut(
                    id=t.id,
                    code=t.code,
                    name=t.name,
                    category=t.category or "",
                    attemptCount=0,
                    correctCount=0,
                    totalCount=0,
                    accuracy=None,
                    reason="尚未专项练习",
                )
            )

    # 已练：正确率升序；未练：按考试频率（types 已按 freq 排）
    practiced.sort(key=lambda x: (x.accuracy if x.accuracy is not None else 1.0, -x.attemptCount))
    # 优先推正确率 < 0.75 的，再补未练高频
    weak = [x for x in practiced if (x.accuracy or 1) < 0.75]
    result: list[ZiliaoWeakTypeOut] = []
    for item in weak + unpracticed + practiced:
        if item.code in {r.code for r in result}:
            continue
        result.append(item)
        if len(result) >= limit:
            break
    return result


def get_overview(db: Session, user_id: str | None = None) -> ZiliaoOverviewOut:
    formula_count = db.query(ZiliaoFormula).filter(ZiliaoFormula.is_published.is_(True)).count()
    type_count = db.query(ZiliaoQuestionType).filter(ZiliaoQuestionType.is_published.is_(True)).count()
    trick_count = db.query(ZiliaoTrick).filter(ZiliaoTrick.is_published.is_(True)).count()
    has_real = _has_real_ziliao_questions(db)
    sets = list_drill_sets(db)
    drill_set_count = len(sets)
    using_sample_only = (not has_real) and any(s.isSample for s in sets)

    today_sets = today_correct = today_total = week_sets = 0
    if user_id:
        today = now().strftime("%Y-%m-%d")
        logs = (
            db.query(ZiliaoPracticeLog)
            .filter(ZiliaoPracticeLog.user_id == user_id, ZiliaoPracticeLog.practice_date == today)
            .all()
        )
        today_sets = len(logs)
        today_correct = sum(l.correct_count for l in logs)
        today_total = sum(l.total_count for l in logs)
        from datetime import timedelta

        start = (now() - timedelta(days=6)).strftime("%Y-%m-%d")
        week_sets = (
            db.query(ZiliaoPracticeLog)
            .filter(
                ZiliaoPracticeLog.user_id == user_id,
                ZiliaoPracticeLog.practice_date >= start,
            )
            .count()
        )

    return ZiliaoOverviewOut(
        formulaCount=formula_count,
        typeCount=type_count,
        trickCount=trick_count,
        drillSetCount=drill_set_count,
        todaySets=today_sets,
        todayCorrect=today_correct,
        todayTotal=today_total,
        weekSets=week_sets,
        hasRealDrill=has_real,
        usingSampleOnly=using_sample_only,
        weakTypes=_compute_weak_types(db, user_id, limit=3),
    )
