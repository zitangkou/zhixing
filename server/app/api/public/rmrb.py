from app.api.public._deps import *  # noqa: F401,F403
import json
from app.models import ShenlunExercise, ShenlunExerciseAttempt, ShenlunMaterial
from app.schemas.shenlun_exercises import ShenlunExerciseAnswerIn, ShenlunExerciseRevisionIn
from app.services.activity_service import record_event

router = APIRouter()
# ===== 人民日报模块（独立：时评 / 开采本 / 规范词） =====

def _fact_material_snapshot_current(row: ShenlunExercise, db: Session) -> bool:
    if not row.source_material_id:
        return True
    material = db.get(ShenlunMaterial, row.source_material_id)
    if (not material or material.item_type != 'case' or material.review_status != 'confirmed'
            or material.veto or material.quality_score is None or material.quality_score < 8):
        return False
    try:
        payload = json.loads(material.payload_json or '{}')
    except (ValueError, TypeError):
        return False
    compact = lambda value: ''.join(str(value or '').split())
    evidence = payload.get('source_evidence') or payload.get('source_anchor') or ''
    valid_anchor = (
        compact(row.fact_material_summary) == compact(material.text)
        and compact(row.fact_material_limit) == compact(payload.get('do_not_use_for', ''))
        and bool(evidence)
        and compact(evidence) in compact(row.source_excerpt)
    )
    if not valid_anchor:
        return False
    try: training = json.loads(row.fact_training_json or '{}')
    except (ValueError, TypeError): return False
    if not training:
        return True  # legacy published exercise; new publication requires a reviewed bundle.
    if training.get('anchor_material_id') != material.id:
        return False
    related = training.get('related_materials', [])
    themes = training.get('themes', [])
    if not isinstance(related, list) or not 1 <= len(related) <= 3 or not isinstance(themes, list) or not 2 <= len(themes) <= 4:
        return False
    snapshots = {material.id: (material, payload)}
    for snapshot in related:
        related_row = db.get(ShenlunMaterial, snapshot.get('id')) if isinstance(snapshot, dict) else None
        if (not related_row or related_row.item_type != 'case' or related_row.review_status != 'confirmed'
                or related_row.veto or related_row.quality_score is None or related_row.quality_score < 8):
            return False
        try: related_payload = json.loads(related_row.payload_json or '{}')
        except (ValueError, TypeError): return False
        related_evidence = related_payload.get('source_evidence') or related_payload.get('source_anchor') or ''
        if (compact(snapshot.get('text')) != compact(related_row.text)
                or compact(snapshot.get('evidence')) != compact(related_evidence)
                or snapshot.get('source_title') != related_row.source_title
                or snapshot.get('source_url') != related_row.source_url
                or snapshot.get('source_date') != related_row.source_date.isoformat()
                or compact(snapshot.get('fact')) != compact(related_payload.get('fact', ''))
                or compact(snapshot.get('result')) != compact(related_payload.get('result', ''))
                or compact(snapshot.get('proves')) != compact(related_payload.get('proves', ''))):
            return False
        snapshots[related_row.id] = (related_row, related_payload)
    for theme in themes:
        if not isinstance(theme, dict) or not isinstance(theme.get('citations'), list):
            return False
        cited = set()
        for citation in theme['citations']:
            if not isinstance(citation, dict) or citation.get('material_id') not in snapshots:
                return False
            cited_row, cited_payload = snapshots[citation['material_id']]
            cited_evidence = cited_payload.get('source_evidence') or cited_payload.get('source_anchor') or ''
            if not compact(citation.get('exact_evidence')) or compact(citation.get('exact_evidence')) not in compact(cited_evidence):
                return False
            cited.add(cited_row.id)
        if material.id not in cited:
            return False
    return True

def _exercise_public(row: ShenlunExercise, attempt=None):
    def parsed(value):
        try: return json.loads(value or '[]')
        except (ValueError, TypeError): return []
    reviewed = attempt is not None
    training = parsed(row.fact_training_json or '{}') if row.source_material_id else {}
    if not isinstance(training, dict): training = {}
    if not reviewed:
        training = {
            'related_materials': training.get('related_materials', []),
            'themes': [{key: theme.get(key, '') for key in ('id', 'theme', 'fit_reason', 'task_prompt')}
                       for theme in training.get('themes', []) if isinstance(theme, dict)],
        }
    return {
        'id': row.id, 'question_type': row.question_type, 'title': row.title,
        'source_material_id': row.source_material_id,
        'fact_material_summary': row.fact_material_summary, 'fact_material_limit': row.fact_material_limit,
        'fact_training': training,
        'source_title': row.source_title, 'source_url': row.source_url, 'source_date': row.source_date,
        'source_excerpt': row.source_excerpt, 'prompt': row.prompt, 'requirements': row.requirements,
        'max_chars': row.max_chars, 'hint': row.hint, 'difficulty': row.difficulty,
        'estimated_minutes': row.estimated_minutes, 'is_featured': row.is_featured,
        'key_points': parsed(row.key_points_json) if reviewed else [],
        'rubric': parsed(row.rubric_json) if reviewed else [],
        'sample_answer': row.sample_answer if reviewed else '', 'analysis': row.analysis if reviewed else '',
        'related_assets': parsed(row.related_assets_json) if reviewed else [],
        'attempt': {'id':attempt.id,'answer':attempt.answer,'work':parsed(attempt.work_json or '{}'),
                    'revision':attempt.revision,'reflection':attempt.reflection} if attempt else None,
    }

@router.get('/rmrb/exercises')
def rmrb_exercises_list(question_type: str | None = None, db: Session = Depends(get_db)):
    query=db.query(ShenlunExercise).filter(ShenlunExercise.status=='published')
    if question_type: query=query.filter(ShenlunExercise.question_type==question_type)
    rows=query.order_by(ShenlunExercise.is_featured.desc(),ShenlunExercise.sort_order,ShenlunExercise.published_at.desc()).limit(100).all()
    return ApiResponse.ok([_exercise_public(x) for x in rows if _fact_material_snapshot_current(x, db)])

@router.get('/rmrb/exercises/{exercise_id}')
def rmrb_exercise_detail(exercise_id: str, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    row=db.get(ShenlunExercise,exercise_id)
    if not row or row.status!='published' or not _fact_material_snapshot_current(row, db): return ApiResponse.fail('练习不存在或已下架',code=404)
    attempt=db.query(ShenlunExerciseAttempt).filter_by(exercise_id=exercise_id,user_id=user.id).order_by(ShenlunExerciseAttempt.submitted_at.desc()).first()
    return ApiResponse.ok(_exercise_public(row,attempt))

@router.post('/rmrb/exercises/{exercise_id}/answers')
def rmrb_exercise_answer(exercise_id: str, body: ShenlunExerciseAnswerIn, user: AppUser = Depends(get_app_user), db: Session = Depends(get_db)):
    row=db.get(ShenlunExercise,exercise_id)
    if not row or row.status!='published' or not _fact_material_snapshot_current(row, db): return ApiResponse.fail('练习不存在或已下架',code=404)
    if row.question_type == 'essay' and body.work:
        required_steps = ('fact', 'theme', 'point', 'analysis', 'paragraph')
        if any(not body.work.get(step, '').strip() for step in required_steps):
            return ApiResponse.fail('请完成事实、主题、观点、分析和论证段五步训练', code=400)
        if body.work['paragraph'].strip() != body.answer.strip():
            return ApiResponse.fail('提交答案需与最后一步论证段一致', code=400)
        try: training = json.loads(row.fact_training_json or '{}')
        except (ValueError, TypeError): training = {}
        themes = training.get('themes', []) if isinstance(training, dict) else []
        if themes:
            selected = next((theme for theme in themes
                             if isinstance(theme, dict) and theme.get('id') == body.work.get('theme_id')), None)
            if not selected or body.work.get('theme', '').strip() != selected.get('theme', '').strip():
                return ApiResponse.fail('请选择本练习提供的适配主题后再提交', code=400)
    attempt=ShenlunExerciseAttempt(exercise_id=exercise_id,user_id=user.id,answer=body.answer.strip(),
                                   work_json=json.dumps(body.work, ensure_ascii=False))
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


