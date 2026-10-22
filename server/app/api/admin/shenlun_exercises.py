"""申论四类题型练习编排与发布管理。"""
import hashlib
import json
from datetime import date, datetime
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import RmrbArticle, ShenlunExercise, ShenlunExerciseJob, ShenlunMaterial
from app.schemas.shenlun_exercises import ShenlunExerciseIn
from app.services.shenlun_exercise_generation import RULE_VERSION, create_job, job_output, run_job, standards_public
from app.config import get_settings
from app.services.ai.llm_client import chat_json, LlmError
from app.services.shenlun_materials import RULES as MATERIAL_RULES

router = APIRouter(prefix='/shenlun-exercises', tags=['申论练习'])

class GenerateBody(BaseModel):
    issue_date: date
    article_ids: list[str] = Field(default_factory=list, max_length=30)

class FactTrainingGenerateBody(BaseModel):
    source_material_id: str = Field(min_length=1, max_length=32)

@router.get('/standards')
def standards(admin=Depends(require_permission('rmrb:read'))):
    return ApiResponse.ok(standards_public())

@router.get('/review-metrics')
def review_metrics(admin=Depends(require_permission('rmrb:read')), db: Session=Depends(get_db)):
    rows = db.query(ShenlunExercise).all()
    decisions = {'pending': 0, 'approved': 0, 'revision_required': 0, 'rejected': 0}
    issue_counts: dict[str, int] = {}
    by_type: dict[str, dict[str, int]] = {}
    by_rule_version: dict[str, dict[str, int]] = {}
    reviewed_count = corrections_count = history_count = 0
    for row in rows:
        try:
            report = json.loads(row.quality_report_json or '{}')
        except (ValueError, TypeError):
            report = {}
        if not isinstance(report, dict):
            report = {}
        review = report.get('human_review') or {}
        if not review and row.status == 'published':
            review = {'decision': 'approved', 'issue_tags': [], 'corrections_made': False}
        if not isinstance(review, dict):
            review = {}
        decision = review.get('decision', 'pending')
        if decision not in decisions:
            decision = 'pending'
        decisions[decision] += 1
        type_counts = by_type.setdefault(row.question_type, {key: 0 for key in decisions})
        type_counts[decision] += 1
        rule_version = row.generation_rule_version or 'manual_or_legacy'
        rule_counts = by_rule_version.setdefault(rule_version, {
            'total': 0, 'reviewed': 0, 'approved': 0, 'revision_required': 0,
            'rejected': 0, 'pending': 0, 'corrections_made': 0,
        })
        rule_counts['total'] += 1
        rule_counts[decision] += 1
        rule_counts['reviewed'] += decision != 'pending'
        rule_counts['corrections_made'] += bool(review.get('corrections_made')) and decision != 'pending'
        if decision != 'pending':
            reviewed_count += 1
            corrections_count += bool(review.get('corrections_made'))
        history = report.get('human_review_history', [])
        if not isinstance(history, list):
            history = []
        history_count += len(history)
        issue_records = history or ([review] if decision != 'pending' else [])
        for event in issue_records:
            if not isinstance(event, dict):
                continue
            tags = event.get('issue_tags', [])
            if isinstance(tags, list):
                for tag in {value for value in tags if isinstance(value, str)}:
                    issue_counts[tag] = issue_counts.get(tag, 0) + 1
    return ApiResponse.ok({
        'total_exercises': len(rows), 'reviewed_count': reviewed_count,
        'corrections_made_count': corrections_count, 'history_event_count': history_count,
        'decision_counts': decisions, 'issue_counts': dict(sorted(issue_counts.items(), key=lambda x: (-x[1], x[0]))),
        'by_type': by_type, 'by_rule_version': by_rule_version,
    })

def _reviewed_content_snapshot(row: ShenlunExercise) -> dict:
    def parsed(value, fallback):
        try: return json.loads(value or '')
        except (ValueError, TypeError): return fallback
    return {
        'question_type': row.question_type, 'title': row.title,
        'source_title': row.source_title, 'source_url': row.source_url,
        'source_date': row.source_date, 'source_material_id': row.source_material_id,
        'fact_material_summary': row.fact_material_summary, 'fact_material_limit': row.fact_material_limit,
        'fact_training': parsed(row.fact_training_json, {}),
        'source_excerpt': row.source_excerpt,
        'prompt': row.prompt, 'requirements': row.requirements, 'max_chars': row.max_chars,
        'key_points': parsed(row.key_points_json, []), 'rubric': parsed(row.rubric_json, []),
        'sample_answer': row.sample_answer, 'analysis': row.analysis,
    }

@router.get('/review-dataset')
def review_dataset(question_type: str='', decision: str='', limit: int=Query(300, ge=1, le=1000),
                   offset: int=Query(0, ge=0),
                   admin=Depends(require_permission('rmrb:read')), db: Session=Depends(get_db)):
    if question_type and question_type not in {'summary', 'countermeasure', 'implementation', 'essay'}:
        return ApiResponse.fail('题型筛选值无效', code=400)
    if decision and decision not in {'approved', 'revision_required', 'rejected'}:
        return ApiResponse.fail('审核结论筛选值无效', code=400)
    rows = db.query(ShenlunExercise)
    if question_type:
        rows = rows.filter(ShenlunExercise.question_type == question_type)
    rows = rows.order_by(ShenlunExercise.updated_at.desc()).all()
    samples = []
    for row in rows:
        try:
            report = json.loads(row.quality_report_json or '{}')
        except (ValueError, TypeError):
            report = {}
        if not isinstance(report, dict):
            report = {}
        history = report.get('human_review_history', [])
        if not isinstance(history, list):
            history = []
        for event in history:
            if not isinstance(event, dict) or not isinstance(event.get('content_snapshot'), dict):
                continue
            event_decision = event.get('decision')
            if event_decision not in {'approved', 'revision_required', 'rejected'}:
                continue
            if decision and event_decision != decision:
                continue
            samples.append({
                'exercise_id': row.id, 'reviewed_at': event.get('reviewed_at'),
                'reviewer': event.get('reviewer'), 'decision': event_decision,
                'issue_tags': event.get('issue_tags', []), 'notes': event.get('notes', ''),
                'corrections_made': bool(event.get('corrections_made')),
                'generation_rule_version': row.generation_rule_version,
                'benchmark_set_version': report.get('benchmarkSetVersion'),
                'content': event['content_snapshot'],
            })
        latest = report.get('human_review') or {}
        latest_decision = latest.get('decision') if isinstance(latest, dict) else None
        latest_fingerprint = latest.get('content_fingerprint') if isinstance(latest, dict) else None
        historical_fingerprints = {
            item.get('content_fingerprint') for item in history
            if isinstance(item, dict) and isinstance(item.get('content_snapshot'), dict)
        }
        if not latest and row.status == 'published':
            latest = {
                'decision': 'approved', 'reviewer': row.reviewed_by,
                'reviewed_at': row.published_at.isoformat() if row.published_at else None,
                'issue_tags': [], 'notes': '', 'corrections_made': False,
            }
            latest_decision = 'approved'
        if latest_decision not in {'approved', 'revision_required', 'rejected'}:
            continue
        if latest_fingerprint and latest_fingerprint in historical_fingerprints:
            continue
        if decision and latest_decision != decision:
            continue
        samples.append({
            'exercise_id': row.id, 'reviewed_at': latest.get('reviewed_at'),
            'reviewer': latest.get('reviewer') or row.reviewed_by, 'decision': latest_decision,
            'issue_tags': latest.get('issue_tags', []), 'notes': latest.get('notes', ''),
            'corrections_made': bool(latest.get('corrections_made')),
            'generation_rule_version': row.generation_rule_version,
            'benchmark_set_version': report.get('benchmarkSetVersion'),
            'legacy_snapshot': True, 'content': _reviewed_content_snapshot(row),
        })
    samples.sort(key=lambda item: item.get('reviewed_at') or '', reverse=True)
    from app.timezone import now
    page = samples[offset:offset + limit]
    return ApiResponse.ok({'schema_version': 1, 'exported_at': now().isoformat(timespec='seconds'),
                           'count': len(page), 'total_available': len(samples), 'items': page})

@router.get('/jobs')
def jobs(admin=Depends(require_permission('rmrb:read')), db: Session=Depends(get_db)):
    rows=db.query(ShenlunExerciseJob).order_by(ShenlunExerciseJob.created_at.desc()).limit(30).all()
    return ApiResponse.ok([job_output(row) for row in rows])

@router.post('/generate')
def generate(body: GenerateBody, tasks: BackgroundTasks,
             admin=Depends(require_permission('rmrb:write')), db: Session=Depends(get_db)):
    from app.timezone import now
    if body.issue_date > now().date():
        return ApiResponse.fail('不能为未来刊期生成练习', code=400)
    cfg=get_settings()
    if not cfg.llm_enabled or not cfg.llm_api_key:
        return ApiResponse.fail('请先启用并配置服务端 LLM', code=400)
    active=db.query(ShenlunExerciseJob).filter(ShenlunExerciseJob.issue_date==body.issue_date,
        ShenlunExerciseJob.status.in_(['pending','running'])).first()
    if active:
        return ApiResponse.ok(job_output(active), message='该刊期已有生成任务运行中')
    job=create_job(body.issue_date, 'manual', body.article_ids)
    tasks.add_task(run_job, job.id)
    return ApiResponse.ok(job_output(job), message='已提交自动出题任务；生成内容均为待审核草稿')

def output(row: ShenlunExercise):
    def parsed(value, fallback):
        try: return json.loads(value or '')
        except (ValueError, TypeError): return fallback
    quality_report = parsed(row.quality_report_json, {})
    human_review = quality_report.get('human_review') or {}
    if not human_review and row.status == 'published':
        human_review = {'decision': 'approved', 'reviewer': row.reviewed_by,
                        'reviewed_at': row.published_at.isoformat() if row.published_at else None,
                        'legacy_record': True}
    elif not human_review:
        human_review = {'decision': 'pending', 'issue_tags': [], 'notes': '', 'corrections_made': False}
    review_history = quality_report.get('human_review_history', [])
    if not isinstance(review_history, list):
        review_history = []
    if row.generation_job_id and row.generation_rule_version != RULE_VERSION:
        quality_report = dict(quality_report)
        quality_report['pass'] = False
        errors = quality_report.get('errors') or []
        if not isinstance(errors, list): errors = [str(errors)]
        quality_report['errors'] = list(dict.fromkeys(errors + ['旧规则草稿需按当前质量标准重新复核']))
    return {
        'id': row.id, 'question_type': row.question_type, 'title': row.title,
        'source_article_id': row.source_article_id, 'source_material_id': row.source_material_id,
        'fact_material_summary': row.fact_material_summary, 'fact_material_limit': row.fact_material_limit,
        'fact_training': parsed(row.fact_training_json, {}),
        'source_title': row.source_title,
        'source_url': row.source_url, 'source_date': row.source_date,
        'source_excerpt': row.source_excerpt, 'prompt': row.prompt, 'requirements': row.requirements,
        'max_chars': row.max_chars, 'hint': row.hint, 'key_points': parsed(row.key_points_json, []),
        'rubric': parsed(row.rubric_json, []), 'sample_answer': row.sample_answer,
        'analysis': row.analysis, 'related_assets': parsed(row.related_assets_json, []),
        'difficulty': row.difficulty, 'estimated_minutes': row.estimated_minutes,
        'sort_order': row.sort_order, 'is_featured': row.is_featured, 'status': row.status,
        'reviewed_by': row.reviewed_by, 'published_at': row.published_at.isoformat() if row.published_at else None,
        'human_review': human_review,
        'human_review_history': review_history,
        'generation_job_id': row.generation_job_id, 'generation_model': row.generation_model,
        'generation_rule_version': row.generation_rule_version, 'quality_score': row.quality_score,
        'quality_report': quality_report,
    }

def assign(row, body: ShenlunExerciseIn, reviewer=''):
    values=body.model_dump(exclude={'human_review'})
    review_input = body.human_review.model_dump()
    for source, target in [('key_points','key_points_json'),('rubric','rubric_json'),('related_assets','related_assets_json')]:
        values[target]=json.dumps(values.pop(source), ensure_ascii=False)
    values['fact_training_json'] = json.dumps(values.pop('fact_training'), ensure_ascii=False)
    old_status=row.status
    previous_report = {}
    try:
        previous_report = json.loads(row.quality_report_json or '{}')
    except (ValueError, TypeError):
        pass
    if not isinstance(previous_report, dict):
        previous_report = {}
    for key,value in values.items(): setattr(row,key,value)
    if row.status == 'published':
        row.published_at = row.published_at or datetime.now()
        row.reviewed_by = reviewer or row.reviewed_by
        review_input['decision'] = 'approved'
        review_input['reviewer'] = row.reviewed_by
        review_input['reviewed_at'] = row.published_at.isoformat()
    elif old_status == 'published':
        row.published_at = None
    if row.status != 'published' and review_input['decision'] != 'pending':
        review_input['reviewer'] = reviewer or ''
        review_input['reviewed_at'] = datetime.now().isoformat()
    review_history = previous_report.get('human_review_history', [])
    if not isinstance(review_history, list):
        review_history = []
    previous_review = previous_report.get('human_review') or {}
    content_fingerprint = hashlib.sha256(json.dumps(
        {key: values.get(key) for key in ('question_type', 'title', 'source_title', 'source_url',
                                          'source_date', 'source_material_id', 'fact_material_summary', 'fact_material_limit',
                                          'fact_training_json',
                                          'source_excerpt', 'prompt', 'requirements',
                                          'max_chars', 'key_points_json', 'rubric_json',
                                          'sample_answer', 'analysis')},
        ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
    if (review_input['decision'] == 'approved' and previous_review
            and previous_review.get('content_fingerprint')
            and previous_review.get('content_fingerprint') != content_fingerprint
            and row.status != 'published'):
        review_input['decision'] = 'pending'
        review_input['issue_tags'] = []
        review_input['notes'] = ''
        review_input['corrections_made'] = False
        review_input['reviewer'] = ''
        review_input['reviewed_at'] = None
    review_input['content_fingerprint'] = content_fingerprint
    signature = lambda value: (value.get('decision'), tuple(value.get('issue_tags', [])),
                              value.get('notes', ''), bool(value.get('corrections_made')),
                              value.get('content_fingerprint'))
    has_review_action = review_input['decision'] != 'pending' or row.status == 'published' or bool(previous_review)
    if has_review_action and (signature(review_input) != signature(previous_review)
                              or (row.status == 'published' and old_status != 'published')):
        review_history.append({**review_input, 'content_snapshot': _reviewed_content_snapshot(row)})
    previous_report['human_review'] = review_input
    previous_report['human_review_history'] = review_history[-50:]
    row.quality_report_json = json.dumps(previous_report, ensure_ascii=False)
    return row

@router.get('')
def listing(question_type: str='', status: str='', q: str='', page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=100), admin=Depends(require_permission('rmrb:read')), db: Session=Depends(get_db)):
    query=db.query(ShenlunExercise)
    if question_type: query=query.filter(ShenlunExercise.question_type==question_type)
    if status: query=query.filter(ShenlunExercise.status==status)
    if q: query=query.filter(or_(ShenlunExercise.title.contains(q),ShenlunExercise.source_title.contains(q),ShenlunExercise.prompt.contains(q)))
    total=query.count()
    items=query.order_by(ShenlunExercise.sort_order,ShenlunExercise.updated_at.desc()).offset((page-1)*page_size).limit(page_size).all()
    return ApiResponse.ok({'items':[output(x) for x in items], 'total':total})

@router.get('/articles')
def articles(admin=Depends(require_permission('rmrb:read')), db: Session=Depends(get_db)):
    rows=db.query(RmrbArticle).filter(RmrbArticle.is_published.is_(True)).order_by(RmrbArticle.publish_date.desc()).limit(200).all()
    return ApiResponse.ok([{'id':x.id,'title':x.title,'source_url':x.source_url,'publish_date':x.publish_date} for x in rows])

@router.get('/fact-materials')
def fact_materials(admin=Depends(require_permission('rmrb:read')), db: Session=Depends(get_db)):
    rows = (db.query(ShenlunMaterial)
            .filter(ShenlunMaterial.item_type == 'case', ShenlunMaterial.review_status == 'confirmed',
                    ShenlunMaterial.veto.is_(False), ShenlunMaterial.quality_score >= 8)
            .order_by(ShenlunMaterial.source_date.desc(), ShenlunMaterial.updated_at.desc())
            .limit(100).all())
    results = []
    for row in rows:
        try:
            payload = json.loads(row.payload_json or '{}')
        except (ValueError, TypeError):
            payload = {}
        if not (payload.get('source_evidence') or payload.get('source_anchor')):
            continue
        results.append({
            'id': row.id, 'text': row.text, 'fact': payload.get('fact', ''),
            'source_evidence': payload.get('source_evidence', ''), 'source_anchor': payload.get('source_anchor', ''),
            'source_title': row.source_title, 'source_section': row.source_section,
            'source_url': row.source_url, 'source_date': row.source_date.isoformat(),
            'result': payload.get('result', ''), 'proves': payload.get('proves', ''),
            'do_not_use_for': payload.get('do_not_use_for', ''), 'theme_code': row.theme_code,
        })
    return ApiResponse.ok(results)

@router.post('/fact-training/generate')
def generate_fact_training(body: FactTrainingGenerateBody,
                           admin=Depends(require_permission('rmrb:write')), db: Session=Depends(get_db)):
    """为已审核事实素材生成主题训练包草稿；仅返回给后台，须人工核验后随练习发布。"""
    anchor = db.get(ShenlunMaterial, body.source_material_id)
    if (not anchor or anchor.item_type != 'case' or anchor.review_status != 'confirmed'
            or anchor.veto or anchor.quality_score is None or anchor.quality_score < 8):
        return ApiResponse.fail('只能以审核通过且质量分不低于8分的事实素材为锚点', code=400)
    def material_data(row):
        try: payload = json.loads(row.payload_json or '{}')
        except (ValueError, TypeError): payload = {}
        return {
            'id': row.id, 'text': row.text, 'fact': payload.get('fact', ''),
            'result': payload.get('result', ''), 'proves': payload.get('proves', ''),
            'use_limit': payload.get('do_not_use_for', ''),
            'evidence': payload.get('source_evidence') or payload.get('source_anchor') or '',
            'source_title': row.source_title, 'source_url': row.source_url,
            'source_date': row.source_date.isoformat(),
            'theme': MATERIAL_RULES['themes'].get(row.theme_code, row.theme_code),
        }
    candidates = (db.query(ShenlunMaterial)
        .filter(ShenlunMaterial.item_type == 'case', ShenlunMaterial.review_status == 'confirmed',
                ShenlunMaterial.veto.is_(False), ShenlunMaterial.quality_score >= 8,
                ShenlunMaterial.id != anchor.id)
        .order_by(ShenlunMaterial.source_date.desc(), ShenlunMaterial.updated_at.desc()).limit(60).all())
    candidate_data = [material_data(row) for row in candidates]
    candidate_data = [row for row in candidate_data if row['evidence']]
    anchor_data = material_data(anchor)
    if not candidate_data:
        return ApiResponse.fail('没有找到可用于交叉训练的其他已审核事实素材', code=400)
    system = (
        '你是公务员申论教研员。按历年申论大作文分论点和教材论证示例的要求设计训练，只基于提供的已审核事实素材，不得补造人物、地点、数据、成效或政策。'
        '生成2至4个具体、可由材料支撑且有考试迁移价值的适配主题；优先从事实体现的问题、治理机制和实际成效归纳，不要只给宏大口号，主题须有区分度。'
        '从候选中选择1至3条与主素材能形成互补论证的相关事实，说明关联理由。每个主题都生成一个参考训练结果，'
        '包含明确分论点、解释“做法如何产生结果”的分析逻辑、80至320字完整论证段和逐条引用的原文证据；段落按“观点—分析—事实支撑—回扣主题”组织。若证据不足以支撑某主题，不要生成该主题。'
        '严格返回 JSON 对象，字段为 themes（数组，每项含 id, theme, fit_reason, task_prompt, point, analysis, paragraph, citations），'
        'related_materials（数组，每项含 id, relation_reason），其中 citations 为数组，每项含 material_id, exact_evidence。'
        '主题 id 使用 T1、T2 等；每个主题 citations 必须引用主素材，并可引用相关素材。exact_evidence 必须逐字复制输入 evidence 或 text 中的连续原文。'
    )
    user = json.dumps({'anchor': anchor_data, 'candidate_materials': candidate_data}, ensure_ascii=False)
    try:
        generated = chat_json(system, user, purpose='shenlun_fact_training')
    except LlmError as exc:
        return ApiResponse.fail(f'主题训练包生成失败：{exc}', code=502)
    themes = generated.get('themes')
    related = generated.get('related_materials')
    if not isinstance(themes, list) or not 2 <= len(themes) <= 4 or not isinstance(related, list) or not 1 <= len(related) <= 3:
        return ApiResponse.fail('AI结果未达到主题数量或相关素材数量要求，请重试', code=502)
    available = {row['id']: row for row in [anchor_data, *candidate_data]}
    related_ids = {item.get('id') for item in related if isinstance(item, dict)}
    if (len(related_ids) != len(related) or anchor.id in related_ids
            or not related_ids.issubset({row['id'] for row in candidate_data})):
        return ApiResponse.fail('AI关联素材引用异常，请重新生成', code=502)
    if any(len(str(item.get('relation_reason', '')).strip()) < 8 for item in related):
        return ApiResponse.fail('AI未能充分说明相关素材关系，请重新生成', code=502)
    related_materials = []
    for item in related:
        source = available[item['id']]
        related_materials.append({**source, 'relation_reason': str(item.get('relation_reason', '')).strip()})
    normalized_themes = []
    seen_ids = set()
    all_cited_ids = set()
    for theme in themes:
        if not isinstance(theme, dict):
            return ApiResponse.fail('AI主题结果格式异常，请重新生成', code=502)
        theme_id = str(theme.get('id', '')).strip()
        citations = theme.get('citations')
        if (not theme_id or theme_id in seen_ids or not isinstance(citations, list) or not citations
                or any(not str(theme.get(key, '')).strip() for key in ('theme','fit_reason','task_prompt','point','analysis','paragraph'))):
            return ApiResponse.fail('AI主题或参考示例字段不完整，请重新生成', code=502)
        seen_ids.add(theme_id)
        citation_rows = []
        cited_ids = set()
        for citation in citations:
            if not isinstance(citation, dict):
                return ApiResponse.fail('AI引用证据格式异常，请重新生成', code=502)
            material_id = citation.get('material_id')
            quote = str(citation.get('exact_evidence', '')).strip()
            if material_id not in available or not quote or quote not in str(available[material_id]['evidence']):
                return ApiResponse.fail('AI示例引用的证据无法逐字回查，请重新生成', code=502)
            cited_ids.add(material_id)
            citation_rows.append({'material_id': material_id, 'exact_evidence': quote})
        if anchor.id not in cited_ids or not cited_ids.issubset(related_ids | {anchor.id}):
            return ApiResponse.fail('AI示例未以主素材为论证依据或引用了未展示素材', code=502)
        if not 80 <= len(str(theme['paragraph'])) <= 320:
            return ApiResponse.fail('AI参考论证段长度不符合单段训练要求，请重新生成', code=502)
        all_cited_ids.update(cited_ids)
        normalized_themes.append({key: str(theme.get(key, '')).strip() for key in
                                  ('id','theme','fit_reason','task_prompt','point','analysis','paragraph')} |
                                 {'citations': citation_rows})
    if not related_ids.issubset(all_cited_ids):
        return ApiResponse.fail('AI筛选的相关素材没有进入任何主题示例的论证，请重新生成', code=502)
    return ApiResponse.ok({'version': 1, 'anchor_material_id': anchor.id,
                           'related_materials': related_materials, 'themes': normalized_themes,
                           'generated_by': get_settings().llm_model,
                           'review_notice': 'AI生成草稿；须逐项核对主题适配、素材关系和引文后方可发布。'})


def validate_fact_material(body: ShenlunExerciseIn, db: Session) -> str | None:
    if not body.source_material_id:
        return None
    material = db.get(ShenlunMaterial, body.source_material_id)
    if (not material or material.item_type != 'case' or material.review_status != 'confirmed'
            or material.veto or material.quality_score is None or material.quality_score < 8):
        return '只能关联审核通过且质量分不低于8分的事实素材'
    if body.question_type != 'essay':
        return '事实素材论证训练仅用于申发论述题'
    normalized = lambda value: ''.join(str(value or '').split())
    if normalized(body.fact_material_summary) != normalized(material.text):
        return '事实摘要应保留已审核素材原文，不要自行改写'
    try:
        payload = json.loads(material.payload_json or '{}')
    except (ValueError, TypeError):
        payload = {}
    evidence = str(payload.get('source_evidence') or payload.get('source_anchor') or '').strip()
    if normalized(body.fact_material_limit) != normalized(payload.get('do_not_use_for', '')):
        return '事实素材使用边界应沿用审核通过版本'
    if not evidence:
        return '事实素材缺少可回查的原文证据，不能用于论证训练'
    if normalized(evidence) not in normalized(body.source_excerpt):
        return '题目材料摘录未包含事实素材对应的原文证据'
    if body.fact_training:
        themes = body.fact_training.get('themes')
        related = body.fact_training.get('related_materials')
        if not isinstance(themes, list) or not 2 <= len(themes) <= 4 or not isinstance(related, list) or not 1 <= len(related) <= 3:
            return '主题训练包须包含2至4个适配主题和1至3条相关素材'
        if body.fact_training.get('anchor_material_id') != material.id:
            return '主题训练包主素材与当前事实素材不一致，请重新生成'
        current = {material.id: (material, payload)}
        related_ids = []
        for item in related:
            if not isinstance(item, dict) or len(str(item.get('relation_reason', '')).strip()) < 8:
                return '每条相关事实素材都须说明与主素材的关联理由'
            related_id = str(item.get('id', ''))
            related_row = db.get(ShenlunMaterial, related_id)
            if (not related_row or related_row.item_type != 'case' or related_row.review_status != 'confirmed'
                    or related_row.veto or related_row.quality_score is None or related_row.quality_score < 8
                    or related_id == material.id or related_id in related_ids):
                return '相关素材必须是互不重复、当前审核通过且质量分不低于8分的其他事实素材'
            try: related_payload = json.loads(related_row.payload_json or '{}')
            except (ValueError, TypeError): related_payload = {}
            related_evidence = str(related_payload.get('source_evidence') or related_payload.get('source_anchor') or '').strip()
            if (normalized(item.get('text')) != normalized(related_row.text)
                    or normalized(item.get('evidence')) != normalized(related_evidence) or not related_evidence
                    or item.get('source_title') != related_row.source_title
                    or item.get('source_url') != related_row.source_url
                    or item.get('source_date') != related_row.source_date.isoformat()
                    or normalized(item.get('fact')) != normalized(related_payload.get('fact', ''))
                    or normalized(item.get('result')) != normalized(related_payload.get('result', ''))
                    or normalized(item.get('proves')) != normalized(related_payload.get('proves', ''))):
                return '相关素材快照或原文证据已变化，请重新生成训练包'
            related_ids.append(related_id)
            current[related_id] = (related_row, related_payload)
        theme_ids = set()
        all_cited_ids = set()
        for theme in themes:
            if not isinstance(theme, dict) or any(not str(theme.get(key, '')).strip() for key in
                    ('id', 'theme', 'fit_reason', 'task_prompt', 'point', 'analysis', 'paragraph')):
                return '适配主题和参考示例内容不完整'
            if theme['id'] in theme_ids:
                return '适配主题标识不能重复'
            theme_ids.add(theme['id'])
            citations = theme.get('citations')
            if not isinstance(citations, list) or not citations:
                return '每个参考示例都须附材料原文依据'
            cited_ids = set()
            for citation in citations:
                if not isinstance(citation, dict) or citation.get('material_id') not in current:
                    return '参考示例引用了训练包之外的素材'
                cited_row, cited_payload = current[citation['material_id']]
                cited_evidence = str(cited_payload.get('source_evidence') or cited_payload.get('source_anchor') or '').strip()
                quote = str(citation.get('exact_evidence', '')).strip()
                if not quote or quote not in cited_evidence:
                    return '参考示例引文必须能在对应素材的原文证据中逐字回查'
                cited_ids.add(citation['material_id'])
            if material.id not in cited_ids:
                return '每个参考示例都须使用主事实素材作为论据'
            if not 80 <= len(str(theme['paragraph'])) <= 320:
                return '每个参考示例需为80至320字的完整单段论证'
            all_cited_ids.update(cited_ids)
        if not set(related_ids).issubset(all_cited_ids):
            return '每条相关素材都须在至少一个主题示例中实际引用'
    return None

@router.post('')
def create(body: ShenlunExerciseIn, admin=Depends(require_permission('rmrb:write')), db: Session=Depends(get_db)):
    fact_error = validate_fact_material(body, db)
    if fact_error: return ApiResponse.fail(fact_error, code=400)
    if body.source_article_id:
        article=db.get(RmrbArticle, body.source_article_id)
        if not article or not article.is_published: return ApiResponse.fail('关联文章不存在或尚未发布', code=400)
    row=assign(ShenlunExercise(), body, admin.username); db.add(row); db.commit(); db.refresh(row)
    return ApiResponse.ok(output(row))

@router.put('/{exercise_id}')
def update(exercise_id: str, body: ShenlunExerciseIn, admin=Depends(require_permission('rmrb:write')), db: Session=Depends(get_db)):
    row=db.get(ShenlunExercise, exercise_id)
    if not row:return ApiResponse.fail('练习不存在', code=404)
    fact_error = validate_fact_material(body, db)
    if fact_error: return ApiResponse.fail(fact_error, code=400)
    if body.source_article_id:
        article=db.get(RmrbArticle, body.source_article_id)
        if not article or not article.is_published:return ApiResponse.fail('关联文章不存在或尚未发布', code=400)
    assign(row, body, admin.username); db.commit(); db.refresh(row)
    return ApiResponse.ok(output(row))

@router.delete('/{exercise_id}')
def delete(exercise_id: str, admin=Depends(require_permission('rmrb:write')), db: Session=Depends(get_db)):
    row=db.get(ShenlunExercise, exercise_id)
    if not row:return ApiResponse.fail('练习不存在', code=404)
    row.status='archived'; db.commit(); return ApiResponse.ok({'archived':exercise_id})
