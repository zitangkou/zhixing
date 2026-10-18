from app.api.public._deps import *  # noqa: F401,F403
import json
from app.models import ShenlunExercise, ShenlunExerciseAttempt
from app.schemas.shenlun_exercises import ShenlunExerciseAnswerIn, ShenlunExerciseRevisionIn
from app.services.activity_service import record_event

router = APIRouter()
# ===== 人民日报模块（独立：时评 / 开采本 / 规范词） =====

def _exercise_public(row: ShenlunExercise, attempt=None):
    def parsed(value):
        try: return json.loads(value or '[]')
        except (ValueError, TypeError): return []
    reviewed = attempt is not None
    return {
        'id': row.id, 'question_type': row.question_type, 'title': row.title,
        'source_title': row.source_title, 'source_url': row.source_url, 'source_date': row.source_date,
        'source_excerpt': row.source_excerpt, 'prompt': row.prompt, 'requirements': row.requirements,
        'max_chars': row.max_chars, 'hint': row.hint, 'difficulty': row.difficulty,
        'estimated_minutes': row.estimated_minutes, 'is_featured': row.is_featured,
        'key_points': parsed(row.key_points_json) if reviewed else [],
        'rubric': parsed(row.rubric_json) if reviewed else [],
        'sample_answer': row.sample_answer if reviewed else '', 'analysis': row.analysis if reviewed else '',
        'related_assets': parsed(row.related_assets_json) if reviewed else [],
        'attempt': {'id':attempt.id,'answer':attempt.answer,'revision':attempt.revision,'reflection':attempt.reflection} if attempt else None,
    }

@router.get('/rmrb/exercises')
def rmrb_exercises_list(question_type: str | None = None, db: Session = Depends(get_db)):
    query=db.query(ShenlunExercise).filter(ShenlunExercise.status=='published')
    if question_type: query=query.filter(ShenlunExercise.question_type==question_type)
    rows=query.order_by(ShenlunExercise.is_featured.desc(),ShenlunExercise.sort_order,ShenlunExercise.published_at.desc()).limit(100).all()
    return ApiResponse.ok([_exercise_public(x) for x in rows])

@router.get('/rmrb/exercises/{exercise_id}')
def rmrb_exercise_detail(exercise_id: str, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    row=db.get(ShenlunExercise,exercise_id)
    if not row or row.status!='published': return ApiResponse.fail('练习不存在或已下架',code=404)
    attempt=db.query(ShenlunExerciseAttempt).filter_by(exercise_id=exercise_id,user_id=user.id).order_by(ShenlunExerciseAttempt.submitted_at.desc()).first()
    return ApiResponse.ok(_exercise_public(row,attempt))

@router.post('/rmrb/exercises/{exercise_id}/answers')
def rmrb_exercise_answer(exercise_id: str, body: ShenlunExerciseAnswerIn, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    row=db.get(ShenlunExercise,exercise_id)
    if not row or row.status!='published': return ApiResponse.fail('练习不存在或已下架',code=404)
    attempt=ShenlunExerciseAttempt(exercise_id=exercise_id,user_id=user.id,answer=body.answer.strip())
    db.add(attempt)
    try:
        record_event(db,user.id,'shenlun_exercise_done',{'exercise_id':exercise_id,'question_type':row.question_type},commit=False)
        db.commit();db.refresh(attempt)
    except Exception:
        db.rollback();raise
    return ApiResponse.ok(_exercise_public(row,attempt))

@router.put('/rmrb/exercises/{exercise_id}/answers/{attempt_id}')
def rmrb_exercise_revision(exercise_id: str, attempt_id: str, body: ShenlunExerciseRevisionIn, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    row=db.get(ShenlunExercise,exercise_id)
    attempt=db.get(ShenlunExerciseAttempt,attempt_id)
    if not row or row.status!='published' or not attempt or attempt.exercise_id!=exercise_id or attempt.user_id!=user.id:
        return ApiResponse.fail('练习记录不存在',code=404)
    attempt.revision=body.revision.strip();attempt.reflection=body.reflection.strip();db.commit()
    return ApiResponse.ok(_exercise_public(row,attempt))


@router.get("/rmrb/meta")
def rmrb_meta(
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """三刀解剖元数据：规范词分类 / 骨架模版 / 句式类型"""
    return ApiResponse.ok(get_rmrb_meta(db, enabled_only=True).model_dump())


@router.post("/rmrb/skeleton-templates")
def rmrb_skeleton_create(
    body: ShenlunSkeletonTemplateCreate,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """用户在三刀页快捷新增骨架模版"""
    try:
        out = create_rmrb_skeleton(db, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.post("/rmrb/term-categories")
def rmrb_term_category_create(
    body: ShenlunTermCategoryCreate,
    _user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """移动端快捷新增规范词/动词分类（kind: term | verb）"""
    try:
        out = create_rmrb_term_category(db, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.get("/rmrb/stats")
def rmrb_stats(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(get_shenlun_stats(db, user).model_dump())


@router.get("/rmrb/articles")
def rmrb_articles_list(
    tag: str | None = None,
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(
        [a.model_dump() for a in list_rmrb_articles(db, published_only=True, tag=tag)]
    )


@router.get("/rmrb/articles/today")
def rmrb_articles_today(db: Session = Depends(get_db)):
    return ApiResponse.ok([a.model_dump() for a in list_rmrb_today_articles(db)])


@router.get("/rmrb/articles/{article_id}")
def rmrb_article_detail(
    article_id: str,
    db: Session = Depends(get_db),
):
    a = get_rmrb_article(db, article_id, bump_read=True)
    if not a or not a.isPublished:
        return ApiResponse.fail("文章不存在", code=404)
    return ApiResponse.ok(a.model_dump())


@router.get("/rmrb/mines")
def rmrb_mines_list(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([m.model_dump() for m in list_shenlun_mines(db, user)])


@router.get("/rmrb/mines/by-date/{mine_date}")
def rmrb_mine_by_date(
    mine_date: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    m = get_shenlun_mine_by_date(db, user, mine_date)
    if not m:
        return ApiResponse.fail("当日尚无开采记录", code=404)
    return ApiResponse.ok(m.model_dump())


@router.get("/rmrb/mines/{mine_id}")
def rmrb_mine_detail(
    mine_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    m = get_shenlun_mine(db, user, mine_id)
    if not m:
        return ApiResponse.fail("开采记录不存在", code=404)
    return ApiResponse.ok(m.model_dump())


@router.post("/rmrb/mines")
def rmrb_mine_upsert(
    body: ShenlunMineLogUpsert,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = upsert_shenlun_mine(db, user, body)
    return ApiResponse.ok(out.model_dump())


@router.put("/rmrb/mines/{mine_id}")
def rmrb_mine_update(
    mine_id: str,
    body: ShenlunMineLogUpdate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = update_shenlun_mine(db, user, mine_id, body)
    if not out:
        return ApiResponse.fail("开采记录不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/rmrb/mines/{mine_id}")
def rmrb_mine_delete(
    mine_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if not delete_shenlun_mine(db, user, mine_id):
        return ApiResponse.fail("开采记录不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.get("/rmrb/terms")
def rmrb_terms_list(
    status: str | None = None,
    category: str | None = None,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(
        [t.model_dump() for t in list_shenlun_terms(db, user, status=status, category=category)]
    )


@router.post("/rmrb/terms")
def rmrb_term_add(
    body: ShenlunNormTermAdd,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        out = add_shenlun_term(db, user, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.put("/rmrb/terms/{term_id}")
def rmrb_term_update(
    term_id: str,
    body: ShenlunNormTermUpdate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    out = update_shenlun_term(db, user, term_id, body)
    if not out:
        return ApiResponse.fail("规范词不存在", code=404)
    return ApiResponse.ok(out.model_dump())


@router.delete("/rmrb/terms/{term_id}")
def rmrb_term_delete(
    term_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if not delete_shenlun_term(db, user, term_id):
        return ApiResponse.fail("规范词不存在", code=404)
    return ApiResponse.ok({"ok": True})


@router.get("/rmrb/drills")
def rmrb_drills_list(
    drill_type: str | None = None,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok([d.model_dump() for d in list_shenlun_drills(db, user, drill_type)])


@router.post("/rmrb/drills")
def rmrb_drill_add(
    body: ShenlunDrillCreate,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        out = add_shenlun_drill(db, user, body)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(out.model_dump())


@router.get("/growth/overview")
def growth_overview(
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    """学习足迹：个人成长总览"""
    return ApiResponse.ok(get_growth_overview(db, user).model_dump())


