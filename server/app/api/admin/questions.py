from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ---- 试题管理 ----
@router.get("/questions")
def list_questions_admin(
    article_id: str | None = None,
    page: int = 1,
    page_size: int = Query(20, ge=1, le=200),
    _admin=Depends(require_permission("question:read")),
    db: Session = Depends(get_db),
):
    q = db.query(Question)
    if article_id:
        q = q.filter(Question.article_id == article_id)
    total = q.count()
    pending_total = 0
    if article_id:
        pending_total = (
            db.query(Question)
            .filter(Question.article_id == article_id, Question.status == "pending")
            .count()
        )
    rows = q.order_by(Question.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ApiResponse.ok({
        "total": total,
        "pending_total": pending_total,
        "items": [question_to_out(r).model_dump() for r in rows],
    })


@router.post("/questions")
def create_question(body: QuestionCreate, _admin=Depends(require_permission("question:write")), db: Session = Depends(get_db)):
    status = body.status or "approved"
    q = Question(
        article_id=body.article_id,
        type=body.type,
        stem=body.stem,
        options=json.dumps(body.options, ensure_ascii=False),
        correct_answer=json.dumps(body.correct_answer, ensure_ascii=False)
        if isinstance(body.correct_answer, list)
        else str(body.correct_answer),
        analysis=body.analysis,
        source_sentence=body.source_sentence,
        status=status,
        origin=body.origin or "manual",
        is_active=body.is_active if body.is_active is not None else status == "approved",
    )
    db.add(q)
    db.commit()
    return ApiResponse.ok(question_to_out(q).model_dump())


@router.put("/questions/{question_id}")
def update_question(
    question_id: str,
    body: QuestionUpdate,
    _admin=Depends(require_permission("question:write")),
    db: Session = Depends(get_db),
):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, "题目不存在")
    data = body.model_dump(exclude_unset=True)
    if "options" in data:
        q.options = json.dumps(data.pop("options"), ensure_ascii=False)
    if "correct_answer" in data:
        ca = data.pop("correct_answer")
        q.correct_answer = json.dumps(ca, ensure_ascii=False) if isinstance(ca, list) else str(ca)
    for k, v in data.items():
        setattr(q, k, v)
    if q.status == "approved":
        q.is_active = True
    db.commit()
    return ApiResponse.ok(question_to_out(q).model_dump())


@router.post("/questions/batch-approve")
def batch_approve_questions(
    body: QuestionBatchApprove,
    _admin=Depends(require_permission("question:write")),
    db: Session = Depends(get_db),
):
    if not body.question_ids:
        return ApiResponse.ok({"count": 0})
    rows = db.query(Question).filter(Question.id.in_(body.question_ids)).all()
    for q in rows:
        q.status = "approved"
        q.is_active = True
    db.commit()
    return ApiResponse.ok({"count": len(rows)}, message=f"已通过 {len(rows)} 道题目")


@router.post("/questions/batch-delete")
def batch_delete_questions(
    body: QuestionBatchDelete,
    _admin=Depends(require_permission("question:write")),
    db: Session = Depends(get_db),
):
    if not body.question_ids:
        return ApiResponse.ok({"count": 0})
    rows = db.query(Question).filter(Question.id.in_(body.question_ids)).all()
    for q in rows:
        delete_question_record(db, q)
    db.commit()
    return ApiResponse.ok({"count": len(rows)}, message=f"已删除 {len(rows)} 道题目")


@router.delete("/questions/{question_id}")
def delete_question(question_id: str, _admin=Depends(require_permission("question:write")), db: Session = Depends(get_db)):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, "题目不存在")
    delete_question_record(db, q)
    db.commit()
    return ApiResponse.ok(None, message="已删除")


