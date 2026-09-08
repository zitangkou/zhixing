from app.api.public._deps import *  # noqa: F401,F403

router = APIRouter()
# ===== 真题/题库 =====


@router.get("/exam/papers")
def exam_papers(
    exam_type: str | None = None,
    subject: str | None = None,
    year: int | None = None,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([p.model_dump() for p in list_exam_papers(
        db, exam_type=exam_type, subject=subject, year=year, is_published=True
    )])


@router.get("/exam/paper/{paper_id}")
def exam_paper_detail(
    paper_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    detail = get_exam_paper_detail(db, paper_id)
    if not detail:
        return ApiResponse.fail("试卷不存在", code=404)
    return ApiResponse.ok(detail.model_dump())


@router.post("/exam/start/{paper_id}")
def exam_start(
    paper_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    result = start_exam_attempt(db, user, paper_id)
    if not result:
        return ApiResponse.fail("试卷不存在或未发布", code=404)
    return ApiResponse.ok(result)


@router.post("/exam/answer")
def exam_answer(
    body: ExamAnswerSubmit,
    attempt_id: str = Query(...),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = submit_exam_answer(db, user, attempt_id, body)
    if not out:
        return ApiResponse.fail("作答失败，attempt 不存在或已交卷", code=400)
    return ApiResponse.ok(out)


@router.post("/exam/submit")
def exam_submit(
    attempt_id: str = Query(...),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    detail = finish_exam_attempt(db, user, attempt_id)
    if not detail:
        return ApiResponse.fail("交卷失败，attempt 不存在", code=400)
    return ApiResponse.ok(detail.model_dump())


@router.get("/exam/attempts")
def exam_attempts(
    paper_id: str | None = None,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([a.model_dump() for a in list_exam_attempts(db, user, paper_id)])


@router.get("/exam/attempt/{attempt_id}")
def exam_attempt_detail(
    attempt_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    detail = get_exam_attempt_detail(db, user, attempt_id)
    if not detail:
        return ApiResponse.fail("作答记录不存在", code=404)
    return ApiResponse.ok(detail.model_dump())


