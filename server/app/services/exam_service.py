"""真题/题库 service：试卷 CRUD、开考、作答、交卷、算分、历史"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    AppUser,
    ExamAnswer,
    ExamAttempt,
    ExamPaper,
    ExamQuestion,
    gen_id,
)
from app.services.activity_service import record_event
from app.schemas import (
    ExamAnswerSubmit,
    ExamAttemptDetailOut,
    ExamAttemptOut,
    ExamPaperCreate,
    ExamPaperDetailOut,
    ExamPaperOut,
    ExamPaperUpdate,
    ExamQuestionCreate,
    ExamQuestionOut,
    ExamQuestionUpdate,
)
from app.timezone import now

# 默认每题分值（行测每题1分）
DEFAULT_SCORE_PER_Q = 1


def _safe_json_loads(s: str | None, default: Any) -> Any:
    if not s:
        return default
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default


def _paper_to_out(p: ExamPaper) -> ExamPaperOut:
    return ExamPaperOut(
        id=p.id,
        title=p.title,
        examType=p.exam_type,
        subject=p.subject,
        year=p.year,
        region=p.region or "",
        level=p.level or "",
        totalCount=p.total_count,
        timeLimitMin=p.time_limit_min,
        tags=_safe_json_loads(p.tags, []),
        isPublished=bool(p.is_published),
        isFree=bool(p.is_free),
        sortOrder=p.sort_order,
        description=p.description or "",
        createdAt=p.created_at,
    )


def _question_to_out(q: ExamQuestion) -> ExamQuestionOut:
    return ExamQuestionOut(
        id=q.id,
        paperId=q.paper_id,
        section=q.section or "",
        sectionIndex=q.section_index,
        sortOrder=q.sort_order,
        type=q.type,
        material=q.material or "",
        stem=q.stem,
        options=_safe_json_loads(q.options, []),
        correctAnswer=_safe_json_loads(q.correct_answer, q.correct_answer or ""),
        analysis=q.analysis or "",
        difficulty=q.difficulty,
        knowledgeTags=_safe_json_loads(q.knowledge_tags, []),
        knowledgeNodeId=getattr(q, "knowledge_node_id", None),
        knowledgeTreeKey=getattr(q, "knowledge_tree_key", None) or "",
        knowledgePath=getattr(q, "knowledge_path", None) or "",
        isActive=bool(q.is_active),
    )


# ===== 试卷 CRUD =====


def list_papers(
    db: Session,
    *,
    exam_type: str | None = None,
    subject: str | None = None,
    year: int | None = None,
    is_published: bool | None = True,
) -> list[ExamPaperOut]:
    q = db.query(ExamPaper)
    if exam_type:
        q = q.filter(ExamPaper.exam_type == exam_type)
    if subject:
        q = q.filter(ExamPaper.subject == subject)
    if year:
        q = q.filter(ExamPaper.year == year)
    if is_published is not None:
        q = q.filter(ExamPaper.is_published.is_(is_published))
    rows = q.order_by(ExamPaper.year.desc(), ExamPaper.sort_order, ExamPaper.created_at.desc()).all()
    return [_paper_to_out(p) for p in rows]


def get_paper(db: Session, paper_id: str) -> ExamPaper | None:
    return db.get(ExamPaper, paper_id)


def get_paper_detail(db: Session, paper_id: str) -> ExamPaperDetailOut | None:
    p = db.get(ExamPaper, paper_id)
    if not p:
        return None
    questions = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.paper_id == paper_id, ExamQuestion.is_active.is_(True))
        .order_by(ExamQuestion.sort_order, ExamQuestion.id)
        .all()
    )
    # 按 section 分组
    sections_map: dict[str, list[dict]] = {}
    section_order: list[str] = []
    for q in questions:
        sec = q.section or "未分类"
        if sec not in sections_map:
            sections_map[sec] = []
            section_order.append(sec)
        sections_map[sec].append(_question_to_out(q).model_dump())
    sections = [{"section": s, "questions": sections_map[s]} for s in section_order]
    return ExamPaperDetailOut(
        id=p.id,
        title=p.title,
        examType=p.exam_type,
        subject=p.subject,
        year=p.year,
        region=p.region or "",
        level=p.level or "",
        totalCount=p.total_count,
        timeLimitMin=p.time_limit_min,
        tags=_safe_json_loads(p.tags, []),
        isPublished=bool(p.is_published),
        isFree=bool(p.is_free),
        description=p.description or "",
        sections=sections,
    )


def create_paper(db: Session, body: ExamPaperCreate) -> ExamPaperOut:
    p = ExamPaper(
        id=gen_id("paper"),
        title=body.title,
        exam_type=body.examType,
        subject=body.subject,
        year=body.year,
        region=body.region,
        level=body.level,
        total_count=0,
        time_limit_min=body.timeLimitMin,
        tags=json.dumps(body.tags, ensure_ascii=False),
        is_published=body.isPublished,
        is_free=body.isFree,
        sort_order=body.sortOrder,
        description=body.description,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _paper_to_out(p)


def update_paper(db: Session, paper_id: str, body: ExamPaperUpdate) -> ExamPaperOut | None:
    p = db.get(ExamPaper, paper_id)
    if not p:
        return None
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        key = {
            "examType": "exam_type",
            "timeLimitMin": "time_limit_min",
            "isPublished": "is_published",
            "isFree": "is_free",
            "sortOrder": "sort_order",
        }.get(k, k)
        if key == "tags":
            p.tags = json.dumps(v, ensure_ascii=False)
        else:
            setattr(p, key, v)
    db.commit()
    db.refresh(p)
    return _paper_to_out(p)


def delete_paper(db: Session, paper_id: str) -> bool:
    p = db.get(ExamPaper, paper_id)
    if not p:
        return False
    # 删除所有题目（SQL 直接删，避免 ORM 外键）
    from sqlalchemy import text as _text

    # 先删作答明细 → 作答记录 → 题目 → 试卷
    attempt_ids = [a.id for a in db.query(ExamAttempt).filter(ExamAttempt.paper_id == paper_id).all()]
    if attempt_ids:
        placeholders = ",".join(f":id{i}" for i in range(len(attempt_ids)))
        params = {f"id{i}": aid for i, aid in enumerate(attempt_ids)}
        db.execute(_text(f"DELETE FROM exam_answers WHERE attempt_id IN ({placeholders})"), params)
        db.execute(_text(f"DELETE FROM exam_attempts WHERE id IN ({placeholders})"), params)
    db.execute(_text("DELETE FROM exam_questions WHERE paper_id = :pid"), {"pid": paper_id})
    db.delete(p)
    db.commit()
    return True


def _refresh_paper_count(db: Session, paper_id: str) -> None:
    cnt = db.query(ExamQuestion).filter(ExamQuestion.paper_id == paper_id, ExamQuestion.is_active.is_(True)).count()
    p = db.get(ExamPaper, paper_id)
    if p:
        p.total_count = cnt
        db.commit()


# ===== 题目 CRUD =====


def create_question(db: Session, paper_id: str, body: ExamQuestionCreate) -> ExamQuestionOut | None:
    from app.services.knowledge_service import resolve_knowledge_ref

    p = db.get(ExamPaper, paper_id)
    if not p:
        return None
    if body.sortOrder == 0:
        body.sortOrder = db.query(ExamQuestion).filter(ExamQuestion.paper_id == paper_id).count() + 1
    nid, tk, path = resolve_knowledge_ref(
        db,
        node_id=body.knowledgeNodeId,
        tree_key=body.knowledgeTreeKey,
        path=body.knowledgePath,
    )
    q = ExamQuestion(
        id=gen_id("eq"),
        paper_id=paper_id,
        section=body.section,
        section_index=body.sectionIndex,
        sort_order=body.sortOrder,
        type=body.type,
        material=body.material,
        stem=body.stem,
        options=json.dumps(body.options, ensure_ascii=False),
        correct_answer=json.dumps(body.correctAnswer, ensure_ascii=False) if not isinstance(body.correctAnswer, str) else body.correctAnswer,
        analysis=body.analysis,
        difficulty=body.difficulty,
        knowledge_tags=json.dumps(body.knowledgeTags, ensure_ascii=False),
        knowledge_node_id=nid,
        knowledge_tree_key=tk,
        knowledge_path=path,
        is_active=True,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    _refresh_paper_count(db, paper_id)
    return _question_to_out(q)


def update_question(db: Session, question_id: str, body: ExamQuestionUpdate) -> ExamQuestionOut | None:
    from app.services.knowledge_service import resolve_knowledge_ref

    q = db.get(ExamQuestion, question_id)
    if not q:
        return None
    data = body.model_dump(exclude_unset=True)
    kb_touched = any(k in data for k in ("knowledgeNodeId", "knowledgeTreeKey", "knowledgePath"))
    kn_id = data.pop("knowledgeNodeId", q.knowledge_node_id) if kb_touched else None
    kn_tk = data.pop("knowledgeTreeKey", q.knowledge_tree_key) if kb_touched else None
    kn_path = data.pop("knowledgePath", q.knowledge_path) if kb_touched else None
    for k, v in data.items():
        key = {
            "sectionIndex": "section_index",
            "sortOrder": "sort_order",
            "correctAnswer": "correct_answer",
            "knowledgeTags": "knowledge_tags",
            "isActive": "is_active",
        }.get(k, k)
        if key in ("options", "knowledge_tags"):
            setattr(q, key, json.dumps(v, ensure_ascii=False))
        elif key == "correct_answer":
            setattr(q, key, json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)
        else:
            setattr(q, key, v)
    if kb_touched:
        if not kn_id and not kn_path:
            q.knowledge_node_id = None
            q.knowledge_tree_key = ""
            q.knowledge_path = ""
        else:
            nid, tk, path = resolve_knowledge_ref(
                db, node_id=kn_id, tree_key=kn_tk or "", path=kn_path or ""
            )
            q.knowledge_node_id = nid
            q.knowledge_tree_key = tk
            q.knowledge_path = path
    db.commit()
    db.refresh(q)
    _refresh_paper_count(db, q.paper_id)
    return _question_to_out(q)


def delete_question(db: Session, question_id: str) -> bool:
    q = db.get(ExamQuestion, question_id)
    if not q:
        return False
    paper_id = q.paper_id
    db.delete(q)
    db.commit()
    _refresh_paper_count(db, paper_id)
    return True


def batch_create_questions(db: Session, paper_id: str, questions: list[dict]) -> dict:
    """批量录入题目（来自 md/json/csv 解析后）"""
    p = db.get(ExamPaper, paper_id)
    if not p:
        return {"ok": False, "error": "试卷不存在"}
    inserted = 0
    errors: list[str] = []
    base_order = db.query(ExamQuestion).filter(ExamQuestion.paper_id == paper_id).count()
    from app.services.knowledge_service import resolve_knowledge_ref

    for i, item in enumerate(questions):
        try:
            options = item.get("options", [])
            correct = item.get("correct_answer") or item.get("correctAnswer", "")
            tags = item.get("knowledge_tags", item.get("knowledgeTags", [])) or []
            kn_path = item.get("knowledge_path") or item.get("knowledgePath") or ""
            kn_tk = item.get("knowledge_tree_key") or item.get("knowledgeTreeKey") or ""
            kn_id = item.get("knowledge_node_id") or item.get("knowledgeNodeId")
            # 旧标签如「言语-概括归纳」尝试当 path 兜底（取最后一段拼不强求）
            if not kn_path and tags:
                kn_path = str(tags[0]).replace("-", "/").replace("－", "/")
            nid, tk, path = resolve_knowledge_ref(
                db, node_id=kn_id, tree_key=kn_tk, path=kn_path
            )
            q = ExamQuestion(
                id=gen_id("eq"),
                paper_id=paper_id,
                section=item.get("section", ""),
                section_index=int(item.get("section_index", i + 1)),
                sort_order=base_order + i + 1,
                type=item.get("type", "single"),
                material=item.get("material", ""),
                stem=item.get("stem", ""),
                options=json.dumps(options, ensure_ascii=False),
                correct_answer=json.dumps(correct, ensure_ascii=False) if not isinstance(correct, str) else correct,
                analysis=item.get("analysis", ""),
                difficulty=int(item.get("difficulty", 3)),
                knowledge_tags=json.dumps(tags, ensure_ascii=False),
                knowledge_node_id=nid,
                knowledge_tree_key=tk,
                knowledge_path=path,
                is_active=True,
            )
            db.add(q)
            inserted += 1
        except Exception as e:
            errors.append(f"第{i + 1}题: {e}")
    db.commit()
    _refresh_paper_count(db, paper_id)
    return {"ok": True, "inserted": inserted, "errors": errors}


# ===== 作答 =====


def start_attempt(db: Session, user: AppUser, paper_id: str) -> dict | None:
    """开考：创建 attempt 记录，返回 attempt_id + 题目列表"""
    p = db.get(ExamPaper, paper_id)
    if not p or not p.is_published:
        return None
    # 同一卷未交卷的 attempt 直接复用
    unfinished = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.user_id == user.id,
            ExamAttempt.paper_id == paper_id,
            ExamAttempt.is_finished.is_(False),
        )
        .first()
    )
    if unfinished:
        att = unfinished
    else:
        att = ExamAttempt(
            id=gen_id("ea"),
            user_id=user.id,
            paper_id=paper_id,
            started_at=now(),
            total_count=p.total_count,
        )
        db.add(att)
        db.commit()
        db.refresh(att)
    # 返回题目（不打乱顺序）
    questions = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.paper_id == paper_id, ExamQuestion.is_active.is_(True))
        .order_by(ExamQuestion.sort_order)
        .all()
    )
    # 已答明细
    answers = (
        db.query(ExamAnswer)
        .filter(ExamAnswer.attempt_id == att.id)
        .all()
    )
    answer_map = {a.question_id: a for a in answers}
    q_list = []
    for q in questions:
        a = answer_map.get(q.id)
        q_list.append({
            "id": q.id,
            "section": q.section or "",
            "sortOrder": q.sort_order,
            "type": q.type,
            "material": q.material or "",
            "stem": q.stem,
            "options": _safe_json_loads(q.options, []),
            "myAnswer": _safe_json_loads(a.user_answer, "") if a else "",
            "marked": bool(a.marked) if a else False,
            "timeUsedSec": a.time_used_sec if a else 0,
        })
    return {
        "attemptId": att.id,
        "paperId": p.id,
        "paperTitle": p.title,
        "timeLimitMin": p.time_limit_min,
        "totalCount": p.total_count,
        "startedAt": att.started_at.isoformat(),
        "questions": q_list,
    }


def submit_answer(
    db: Session, user: AppUser, attempt_id: str, body: ExamAnswerSubmit
) -> dict | None:
    """提交单题作答（不立即判分，交卷时统一判分）"""
    att = db.get(ExamAttempt, attempt_id)
    if not att or att.user_id != user.id or att.is_finished:
        return None
    q = db.get(ExamQuestion, body.questionId)
    if not q or q.paper_id != att.paper_id:
        return None
    a = (
        db.query(ExamAnswer)
        .filter(ExamAnswer.attempt_id == attempt_id, ExamAnswer.question_id == body.questionId)
        .first()
    )
    answer_json = json.dumps(body.answer, ensure_ascii=False) if not isinstance(body.answer, str) else body.answer
    if a:
        a.user_answer = answer_json
        a.marked = body.marked
        a.time_used_sec = body.timeUsedSec
    else:
        a = ExamAnswer(
            attempt_id=attempt_id,
            question_id=body.questionId,
            user_answer=answer_json,
            marked=body.marked,
            time_used_sec=body.timeUsedSec,
            is_correct=False,
        )
        db.add(a)
    db.commit()
    return {"ok": True}


def _check_answer(q: ExamQuestion, user_answer: str | list[str]) -> bool:
    correct = _safe_json_loads(q.correct_answer, q.correct_answer or "")
    if isinstance(correct, list):
        if not isinstance(user_answer, list):
            return False
        return sorted(correct) == sorted(user_answer)
    return str(user_answer) == str(correct)


def finish_attempt(db: Session, user: AppUser, attempt_id: str) -> ExamAttemptDetailOut | None:
    """交卷：判分、统计、返回详情"""
    att = db.get(ExamAttempt, attempt_id)
    if not att or att.user_id != user.id:
        return None
    if att.is_finished:
        # 已交卷，直接返回
        return _build_attempt_detail(db, att)
    # 判分
    questions = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.paper_id == att.paper_id, ExamQuestion.is_active.is_(True))
        .all()
    )
    answers = (
        db.query(ExamAnswer)
        .filter(ExamAnswer.attempt_id == att.id)
        .all()
    )
    answer_map = {a.question_id: a for a in answers}
    correct_count = 0
    answered_count = 0
    score = 0
    for q in questions:
        a = answer_map.get(q.id)
        if not a:
            continue
        answered_count += 1
        user_ans = _safe_json_loads(a.user_answer, a.user_answer or "")
        is_ok = _check_answer(q, user_ans)
        a.is_correct = is_ok
        if is_ok:
            correct_count += 1
            score += DEFAULT_SCORE_PER_Q
    att.answered_count = answered_count
    att.correct_count = correct_count
    att.score = score
    att.is_finished = True
    att.finished_at = now().replace(tzinfo=None)  # SQLite 存 naive，这里统一
    # started_at 从 DB 读出是 naive；如果原本是 aware，统一去 tz
    started = att.started_at
    if started.tzinfo is not None:
        started = started.replace(tzinfo=None)
    att.time_used_sec = int((att.finished_at - started).total_seconds())
    db.commit()
    db.refresh(att)

    record_event(
        db,
        user.id,
        "exam_done",
        {
            "attemptId": att.id,
            "paperId": att.paper_id,
            "score": att.score,
            "correctCount": att.correct_count,
            "answeredCount": att.answered_count,
            "timeUsedSec": att.time_used_sec,
        },
    )
    return _build_attempt_detail(db, att)


def _build_attempt_detail(db: Session, att: ExamAttempt) -> ExamAttemptDetailOut:
    p = db.get(ExamPaper, att.paper_id)
    questions = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.paper_id == att.paper_id)
        .order_by(ExamQuestion.sort_order)
        .all()
    )
    answers = (
        db.query(ExamAnswer)
        .filter(ExamAnswer.attempt_id == att.id)
        .all()
    )
    answer_map = {a.question_id: a for a in answers}
    q_by_id = {q.id: q for q in questions}

    answers_out: list[dict] = []
    section_stats: dict[str, dict] = {}
    for q in questions:
        a = answer_map.get(q.id)
        sec = q.section or "未分类"
        if sec not in section_stats:
            section_stats[sec] = {"section": sec, "total": 0, "correct": 0, "answered": 0}
        section_stats[sec]["total"] += 1
        user_ans = _safe_json_loads(a.user_answer, a.user_answer or "") if a else ""
        is_ok = bool(a.is_correct) if a else False
        if a:
            section_stats[sec]["answered"] += 1
            if is_ok:
                section_stats[sec]["correct"] += 1
        answers_out.append({
            "questionId": q.id,
            "section": sec,
            "sortOrder": q.sort_order,
            "stem": q.stem,
            "options": _safe_json_loads(q.options, []),
            "correctAnswer": _safe_json_loads(q.correct_answer, q.correct_answer or ""),
            "analysis": q.analysis or "",
            "userAnswer": user_ans,
            "isCorrect": is_ok,
            "answered": a is not None,
            "timeUsedSec": a.time_used_sec if a else 0,
            "marked": bool(a.marked) if a else False,
        })
    section_list = []
    for sec, st in section_stats.items():
        st["accuracy"] = round(st["correct"] * 100 / st["answered"]) if st["answered"] else 0
        section_list.append(st)
    return ExamAttemptDetailOut(
        id=att.id,
        paperId=att.paper_id,
        paperTitle=p.title if p else "",
        startedAt=att.started_at,
        finishedAt=att.finished_at,
        timeUsedSec=att.time_used_sec,
        totalCount=att.total_count,
        answeredCount=att.answered_count,
        correctCount=att.correct_count,
        score=att.score,
        isFinished=bool(att.is_finished),
        answers=answers_out,
        sectionStats=section_list,
    )


def list_user_attempts(db: Session, user: AppUser, paper_id: str | None = None) -> list[ExamAttemptOut]:
    q = db.query(ExamAttempt).filter(ExamAttempt.user_id == user.id)
    if paper_id:
        q = q.filter(ExamAttempt.paper_id == paper_id)
    rows = q.order_by(ExamAttempt.created_at.desc()).all()
    out: list[ExamAttemptOut] = []
    for a in rows:
        p = db.get(ExamPaper, a.paper_id)
        out.append(ExamAttemptOut(
            id=a.id,
            paperId=a.paper_id,
            paperTitle=p.title if p else "",
            startedAt=a.started_at,
            finishedAt=a.finished_at,
            timeUsedSec=a.time_used_sec,
            totalCount=a.total_count,
            answeredCount=a.answered_count,
            correctCount=a.correct_count,
            score=a.score,
            isFinished=bool(a.is_finished),
        ))
    return out


def get_attempt_detail(db: Session, user: AppUser, attempt_id: str) -> ExamAttemptDetailOut | None:
    att = db.get(ExamAttempt, attempt_id)
    if not att or att.user_id != user.id:
        return None
    return _build_attempt_detail(db, att)
