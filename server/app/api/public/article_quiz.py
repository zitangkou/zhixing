from datetime import date

from app.api.public._deps import *  # noqa: F401,F403
import json

from app.models import DailyQuote, Feedback, TheoryPoint, ArticleQuizProgress, WrongAnswer
from app.product import ProductContext
from app.services.daily_quote_service import out as quote_out
from app.services.serializers import student_article_dict
from app.services.theory_brief_service import approved_count, approved_count_for_point
router = APIRouter()

def _with_brief():
    return (
        Article.is_published.is_(True),
        Article.status == "published",
        Article.brief_status == "published",
    )

def _student(db: Session, article: Article) -> dict:
    data = student_article_dict(article)
    data["quizReady"] = approved_count(db, article.id) > 0
    return data

from fastapi.security import HTTPBearer

_optional_bearer = HTTPBearer(auto_error=False)


def _viewer(creds=Depends(_optional_bearer), db: Session = Depends(get_db)):
    if not creds:
        return None
    from app.core.security import decode_token
    user_id = decode_token(creds.credentials)
    if not user_id:
        return None
    user = db.get(AppUser, user_id)
    return user if user and user.is_active else None


@router.get("/theory-points")
def public_theory_points(db: Session = Depends(get_db), user: AppUser | None = Depends(_viewer)):
    rows = (
        db.query(TheoryPoint)
        .filter(TheoryPoint.is_published.is_(True))
        .order_by(TheoryPoint.sort_order, TheoryPoint.created_at.desc())
        .all()
    )
    point_ids = [row.id for row in rows]
    answered: dict[str, int] = {}
    wrong_left: dict[str, int] = {}
    if user and point_ids:
        q_rows = (
            db.query(Question.id, Question.theory_point_id)
            .filter(Question.theory_point_id.in_(point_ids), Question.status == "approved", Question.is_active.is_(True))
            .all()
        )
        q_point = {item.id: item.theory_point_id for item in q_rows}
        if q_point:
            progress_rows = (
                db.query(ArticleQuizProgress)
                .filter(ArticleQuizProgress.user_id == user.id, ArticleQuizProgress.question_id.in_(list(q_point)))
                .all()
            )
            wrong_ids = {
                item.question_id
                for item in db.query(WrongAnswer).filter(WrongAnswer.user_id == user.id).all()
            }
            for item in progress_rows:
                pid = q_point.get(item.question_id)
                if not pid:
                    continue
                answered[pid] = answered.get(pid, 0) + 1
                if item.question_id in wrong_ids:
                    wrong_left[pid] = wrong_left.get(pid, 0) + 1

    def card(row: TheoryPoint, sections: list | None = None) -> dict:
        data = {
            "id": row.id,
            "title": row.title,
            "articleId": "",
            "questionCount": approved_count_for_point(db, row.id),
            "answered": answered.get(row.id, 0),
            "wrongLeft": wrong_left.get(row.id, 0),
            "isKey": bool(row.is_key),
            "summary": (row.highlights or "").strip(),
        }
        if sections is not None:
            data["sections"] = sections
        return data

    tops = [row for row in rows if not row.parent_id]
    by_parent: dict[str, list[TheoryPoint]] = {}
    for row in rows:
        if row.parent_id:
            by_parent.setdefault(row.parent_id, []).append(row)
    return ApiResponse.ok([
        card(row, [card(child) for child in by_parent.get(row.id, [])])
        for row in tops
    ])


@router.get("/quotes")
def public_quotes(day: date | None = None, db: Session = Depends(get_db)):
    query = db.query(DailyQuote).filter(DailyQuote.enabled.is_(True))
    if day:
        query = query.filter(DailyQuote.collected_date == day)
    rows = query.order_by(DailyQuote.collected_date.desc(), DailyQuote.created_at.desc()).limit(50).all()
    return ApiResponse.ok([
        {
            "id": item["id"],
            "text": item["text"],
            "collectedDate": item["collectedDate"],
            "highlights": item.get("highlights") or [],
            "topics": item.get("topics") or [],
            "examples": item.get("examples") or [],
            "articleTitle": item.get("articleTitle") or "",
            "articleDate": item.get("articleDate") or "",
            "source": item.get("source") or "",
            "component": item.get("component") or "",
            "quoteType": item.get("quoteType") or "",
            "use": item.get("use") or "",
            "formula": item.get("formula") or "",
            "why": item.get("why") or "",
            "guidance": item.get("guidance") or "",
            "pitfall": item.get("pitfall") or "",
        }
        for item in (quote_out(row) for row in rows)
    ])

@router.get("/articles/daily")
def daily_articles(db: Session = Depends(get_db)):
    published = db.query(Article).filter(*_with_brief())
    rows = (
        published.filter(Article.is_daily.is_(True))
        .order_by(Article.publish_date.desc(), Article.created_at.desc())
        .all()
    )
    if not rows:
        rows = (
            published.order_by(Article.publish_date.desc(), Article.created_at.desc())
            .limit(1)
            .all()
        )
    return ApiResponse.ok([_student(db, a) for a in rows])


@router.get("/articles/recommended")
def recommended_articles(
    offset: int = Query(0, ge=0),
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    base = (
        db.query(Article)
        .filter(*_with_brief())
        .order_by(Article.is_featured.desc(), Article.publish_date.desc(), Article.created_at.desc())
    )
    total = base.count()
    rows = base.offset(offset).limit(limit).all()
    items = [_student(db, a) for a in rows]
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
    if not article or not article.is_published or article.status != "published" or article.brief_status != "published":
        return ApiResponse.fail("要点尚未发布", code=404)
    return ApiResponse.ok(_student(db, article))


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
    articleId: str = Query(""),
    theoryPointId: str = Query(""),
    product: ProductContext = Depends(get_product_context),
    db: Session = Depends(get_db),
):
    if theoryPointId:
        rows = (
            db.query(Question)
            .filter(
                Question.theory_point_id == theoryPointId,
                Question.is_active.is_(True),
                Question.status == "approved",
            )
            .order_by(Question.created_at.asc(), Question.id.asc())
            .all()
        )
        return ApiResponse.ok([question_to_out(q).model_dump() for q in rows])
    article = db.get(Article, articleId) if articleId else None
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
    rows = query.order_by(Question.created_at.asc(), Question.id.asc()).all()
    return ApiResponse.ok([question_to_out(q).model_dump() for q in rows])


@router.get("/theory/packs")
def theory_packs(db: Session = Depends(get_db)):
    from app.services.theory_learning_entry_service import list_public_entries

    return ApiResponse.ok(list_public_entries(db))


@router.get("/theory/packs/{article_id}")
def theory_pack_detail(article_id: str, db: Session = Depends(get_db)):
    from app.services.theory_learning_entry_service import get_public_entry

    row, parts = get_public_entry(db, article_id)
    article = db.get(Article, article_id)
    if not article:
        return ApiResponse.fail("学习入口尚未开放", code=404)
    from app.services.theory_learning_entry_service import _entry_out

    return ApiResponse.ok(_entry_out(row, article, parts))


@router.post("/answer")
def submit_answer(body: AnswerSubmit, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    q = db.get(Question, body.questionId)
    if not q or not q.is_active or getattr(q, "status", "approved") != "approved":
        return ApiResponse.fail("题目不存在", code=404)
    existing = (
        db.query(ArticleQuizProgress)
        .filter(ArticleQuizProgress.user_id == user.id, ArticleQuizProgress.question_id == q.id)
        .first()
    )
    correct_answer = parse_correct_answer(q.correct_answer or "")
    if existing and not body.practice:
        return ApiResponse.ok(
            AnswerResult(
                correct=existing.is_correct,
                analysis=q.analysis,
                correctAnswer=correct_answer,
                pointsEarned=0,
            ).model_dump()
        )
    if existing and body.practice:
        from app.services.wrong_service import apply_wrong_redo_result

        correct = check_answer(q, body.answer)
        if correct:
            apply_wrong_redo_result(db, user.id, q.id, True)
        else:
            in_book = (
                db.query(WrongAnswer)
                .filter(WrongAnswer.user_id == user.id, WrongAnswer.question_id == q.id)
                .first()
            )
            if in_book:
                apply_wrong_redo_result(db, user.id, q.id, False)
            else:
                record_wrong(db, user.id, q.id, body.answer)
        existing.user_answer = json.dumps(body.answer, ensure_ascii=False)
        existing.is_correct = correct
        db.commit()
        return ApiResponse.ok(
            AnswerResult(
                correct=correct,
                analysis=q.analysis,
                correctAnswer=correct_answer,
                pointsEarned=0,
            ).model_dump()
        )
    correct = check_answer(q, body.answer)
    points = 0
    if correct:
        add_points_log(db, user, 2, "答题", "答对题目")
        points = 2
    else:
        record_wrong(db, user.id, q.id, body.answer)
    db.add(ArticleQuizProgress(
        user_id=user.id,
        article_id=q.theory_point_id or q.article_id or "",
        question_id=q.id,
        user_answer=json.dumps(body.answer, ensure_ascii=False),
        is_correct=correct,
    ))
    db.commit()
    db.refresh(user)
    return ApiResponse.ok(
        AnswerResult(
            correct=correct,
            analysis=q.analysis,
            correctAnswer=correct_answer,
            pointsEarned=points,
        ).model_dump()
    )


@router.get("/quiz-progress")
def quiz_progress(
    articleId: str = Query(""),
    theoryPointId: str = Query(""),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    query = db.query(ArticleQuizProgress).filter(ArticleQuizProgress.user_id == user.id)
    if theoryPointId:
        qids = [
            item.id for item in db.query(Question.id).filter(Question.theory_point_id == theoryPointId).all()
        ]
        query = query.filter(ArticleQuizProgress.question_id.in_(qids or [""]))
    elif articleId:
        query = query.filter(ArticleQuizProgress.article_id == articleId)
    else:
        return ApiResponse.ok([])
    rows = query.all()
    return ApiResponse.ok([
        {
            "questionId": row.question_id,
            "userAnswer": json.loads(row.user_answer) if row.user_answer else "",
            "correct": row.is_correct,
        }
        for row in rows
    ])


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
    progress = (
        db.query(ArticleQuizProgress)
        .filter(ArticleQuizProgress.user_id == user.id, ArticleQuizProgress.question_id == q.id)
        .first()
    )
    if progress and correct:
        progress.is_correct = True
        db.commit()
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
