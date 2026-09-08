from app.api.public._deps import *  # noqa: F401,F403
from app.models import Feedback
from app.product import ProductContext

router = APIRouter()

@router.get("/articles/daily")
def daily_articles(db: Session = Depends(get_db)):
    rows = (
        db.query(Article)
        .filter(
            Article.is_published.is_(True),
            Article.status == "published",
            Article.is_daily.is_(True),
        )
        .order_by(Article.is_featured.desc(), Article.publish_date.desc(), Article.created_at.desc())
        .all()
    )
    if not rows:
        rows = (
            db.query(Article)
            .filter(Article.is_published.is_(True), Article.status == "published")
            .order_by(Article.created_at.desc())
            .limit(3)
            .all()
        )
    return ApiResponse.ok([article_to_out(a).model_dump() for a in rows])


@router.get("/articles/recommended")
def recommended_articles(
    offset: int = Query(0, ge=0),
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    base = (
        db.query(Article)
        .filter(
            Article.is_published.is_(True),
            Article.status == "published",
            Article.is_featured.is_(False),
        )
        .order_by(Article.publish_date.desc(), Article.created_at.desc())
    )
    total = base.count()
    rows = base.offset(offset).limit(limit).all()
    items = [article_to_out(a).model_dump() for a in rows]
    return ApiResponse.ok(
        {
            "items": items,
            "total": total,
            "hasMore": offset + len(rows) < total,
        }
    )


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    return ApiResponse.ok(build_category_tree(db))


@router.get("/quiz")
def quiz_by_mode(
    mode: str = Query("random"),
    count: int = Query(10, ge=1, le=30),
    categoryId: str | None = None,
    days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_db),
):
    if mode == "timeline":
        rows = pick_timeline_questions(db, count, days)
    elif mode == "key":
        rows = pick_questions(db, count, categoryId, min_importance=4)
    else:
        rows = pick_questions(db, count, categoryId)
    if not rows:
        return ApiResponse.fail("暂无可用题目", code=404)
    return ApiResponse.ok([question_to_out(q).model_dump() for q in rows])


@router.get("/articles/{article_id}")
def article_detail(article_id: str, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article or not article.is_published or article.status != "published":
        return ApiResponse.fail("文章不存在", code=404)
    return ApiResponse.ok(article_to_out(article).model_dump())


@router.post("/articles/{article_id}/read")
def mark_read(
    article_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        return ApiResponse.fail("文章不存在", code=404)

    _, created = upsert_study_record(db, user.id, article_id)
    points = 0
    if created:
        article.read_count += 1
        add_points_log(db, user, 3, "阅读", f"完成文章阅读")
        points = 3
    else:
        db.commit()
    return ApiResponse.ok({"points": points})


@router.get("/questions")
def list_questions(
    articleId: str = Query(...),
    product: ProductContext = Depends(get_product_context),
    db: Session = Depends(get_db),
):
    article = db.get(Article, articleId)
    if not article or not article.allow_quiz or article.status != "published":
        return ApiResponse.ok([])
    query = (
        db.query(Question)
        .filter(
            Question.article_id == articleId,
            Question.is_active.is_(True),
            Question.status == "approved",
        )
    )
    if product.key == "theory":
        query = query.filter(Question.source_sentence != "")
    rows = query.all()
    return ApiResponse.ok([question_to_out(q).model_dump() for q in rows])


@router.post("/answer")
def submit_answer(body: AnswerSubmit, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    q = db.get(Question, body.questionId)
    if not q or not q.is_active or getattr(q, "status", "approved") != "approved":
        return ApiResponse.fail("题目不存在", code=404)
    correct = check_answer(q, body.answer)
    points = 0
    if correct:
        add_points_log(db, user, 2, "答题", "答对题目")
        points = 2
    else:
        record_wrong(db, user.id, q.id, body.answer)
    db.refresh(user)
    correct_answer = parse_correct_answer(q.correct_answer or "")
    return ApiResponse.ok(
        AnswerResult(
            correct=correct,
            analysis=q.analysis,
            correctAnswer=correct_answer,
            pointsEarned=points,
        ).model_dump()
    )


@router.get("/wrong")
def wrong_list(
    status: str = "review",
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """status: review（今日到期，默认）| waiting | all"""
    if status not in ("review", "waiting", "all"):
        status = "review"
    return ApiResponse.ok(list_wrong_questions(db, user.id, status=status))


@router.delete("/wrong/{question_id}")
def wrong_remove(
    question_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    removed = remove_wrong(db, user.id, question_id)
    if not removed:
        return ApiResponse.fail("错题记录不存在", code=404)
    return ApiResponse.ok(None)


@router.post("/wrong/redo")
def wrong_redo(body: WrongRedoBody, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    q = db.get(Question, body.questionId)
    if not q:
        return ApiResponse.fail("题目不存在", code=404)
    correct = check_answer(q, body.answer)
    points = 0
    outcome = apply_wrong_redo_result(db, user.id, q.id, correct)
    if correct:
        if outcome == "removed":
            add_points_log(db, user, 5, "复习", "错题掌握（记忆曲线完成）")
            points = 5
        elif outcome == "scheduled":
            add_points_log(db, user, 3, "复习", "错题复习答对，已安排下次复习")
            points = 3
    db.refresh(user)
    correct_answer = parse_correct_answer(q.correct_answer or "")
    return ApiResponse.ok(
        AnswerResult(
            correct=correct,
            analysis=q.analysis,
            correctAnswer=correct_answer,
            pointsEarned=points,
        ).model_dump()
    )


@router.get("/study/records")
def study_records(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    return ApiResponse.ok(list_study_records(db, user.id))


@router.get("/study/section-reads")
def section_reads(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    return ApiResponse.ok(get_section_read_map(db, user.id))


@router.post("/study/sections/read")
def section_read(
    body: SectionReadBody,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    mark_section_read(db, user.id, body.articleId, body.sectionId)
    return ApiResponse.ok(None)


@router.post("/signin")
def sign_in(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    from app.timezone import today as today_str

    today = today_str()
    exists = (
        db.query(SignRecord)
        .filter(SignRecord.user_id == user.id, SignRecord.sign_date == today)
        .first()
    )
    if exists:
        return ApiResponse.fail("今日已签到", code=400, data={"points": 0, "streak": 0})

    db.add(SignRecord(user_id=user.id, sign_date=today, points=5))
    db.commit()
    record_event(db, user.id, "sign_in", {"points": 5})
    streak = calc_sign_streak(db, user.id, today)
    points = 5 + (10 if streak >= 7 and streak % 7 == 0 else 0)
    add_points_log(db, user, points, "签到", f"第{streak}天连续签到")
    db.refresh(user)
    return ApiResponse.ok({"points": points, "streak": streak})


@router.get("/points")
def get_points(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    db.refresh(user)
    return ApiResponse.ok(user.points)


@router.get("/points/log")
def points_log(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    rows = (
        db.query(PointsLog)
        .filter(PointsLog.user_id == user.id)
        .order_by(PointsLog.created_at.desc())
        .limit(100)
        .all()
    )
    data = [
        PointsLogOut(
            id=r.id,
            amount=r.amount,
            type=r.log_type,
            source=r.source,
            description=r.description,
            createdAt=r.created_at.isoformat(),
        ).model_dump()
        for r in rows
    ]
    return ApiResponse.ok(data)


@router.post("/quiz/complete")
def quiz_complete(
    body: QuizCompleteBody,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if body.correct > body.total:
        return ApiResponse.fail("正确题数不能超过总题数", code=400)
    data = submit_quiz_attempt(
        db,
        user.id,
        article_id=body.articleId,
        quiz_mode=body.mode,
        total=body.total,
        correct=body.correct,
    )
    return ApiResponse.ok(QuizCompleteResult(**data).model_dump())


@router.get("/quiz/rank")
def quiz_rank(
    articleId: str | None = Query(None),
    mode: str = Query("article"),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    items = get_quiz_rank(db, article_id=articleId, quiz_mode=mode, limit=20)
    for item in items:
        item["isSelf"] = item["userId"] == user.id
    return ApiResponse.ok(items)


@router.get("/quiz/stats")
def quiz_stats(
    articleId: str | None = Query(None),
    mode: str = Query("article"),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    stats = get_user_quiz_stats(db, user.id, article_id=articleId, quiz_mode=mode)
    if not stats:
        return ApiResponse.ok(None)
    return ApiResponse.ok(QuizStatsOut(**stats).model_dump())


@router.get("/rank")
def rank_list(
    type: str = Query("weekly"),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    factor = {"daily": 0.1, "weekly": 0.3, "monthly": 0.6, "total": 1.0}.get(type, 0.3)
    users = (
        db.query(AppUser)
        .filter(AppUser.is_active.is_(True), AppUser.username.isnot(None))
        .order_by(AppUser.points.desc())
        .limit(20)
        .all()
    )
    items = [
        RankItemOut(
            rank=i + 1,
            userId=u.id,
            nickname=u.nickname,
            avatar=u.avatar,
            score=int(u.points * factor),
            isSelf=u.id == user.id,
        ).model_dump()
        for i, u in enumerate(users)
    ]
    return ApiResponse.ok(items)


@router.post("/feedback")
def feedback(
    body: FeedbackBody,
    user: AppUser = Depends(get_app_user),
    product: ProductContext = Depends(get_product_context),
    db: Session = Depends(get_db),
):
    """学员反馈：真实落库，采纳与加分由管理端人工处理（不再随机判定）。"""
    content = (body.content or "").strip()
    if not content:
        return ApiResponse.fail("反馈内容不能为空", code=400)
    row = Feedback(user_id=user.id, product_key=product.key, content=content[:500])
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiResponse.ok({"id": row.id, "status": row.status, "adopted": False})


@router.get("/review")
def review_tasks(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    return ApiResponse.ok(generate_review_tasks(db, user.id))


@router.post("/review/complete")
def complete_review_task(
    body: ReviewCompleteBody,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    complete_review(db, user.id, body.articleId)
    return ApiResponse.ok(None)


@router.get("/review/hub")
def review_hub(user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    return ApiResponse.ok(get_review_hub(db, user).model_dump())
