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
from app.models import RmrbArticle, ShenlunExercise, ShenlunExerciseJob
from app.schemas.shenlun_exercises import ShenlunExerciseIn
from app.services.shenlun_exercise_generation import RULE_VERSION, create_job, job_output, run_job, standards_public
from app.config import get_settings

router = APIRouter(prefix='/shenlun-exercises', tags=['申论练习'])

class GenerateBody(BaseModel):
    issue_date: date
    article_ids: list[str] = Field(default_factory=list, max_length=30)

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
        'source_date': row.source_date, 'source_excerpt': row.source_excerpt,
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
        'source_article_id': row.source_article_id, 'source_title': row.source_title,
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
                                          'source_date', 'source_excerpt', 'prompt', 'requirements',
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

@router.post('')
def create(body: ShenlunExerciseIn, admin=Depends(require_permission('rmrb:write')), db: Session=Depends(get_db)):
    if body.source_article_id:
        article=db.get(RmrbArticle, body.source_article_id)
        if not article or not article.is_published: return ApiResponse.fail('关联文章不存在或尚未发布', code=400)
    row=assign(ShenlunExercise(), body, admin.username); db.add(row); db.commit(); db.refresh(row)
    return ApiResponse.ok(output(row))

@router.put('/{exercise_id}')
def update(exercise_id: str, body: ShenlunExerciseIn, admin=Depends(require_permission('rmrb:write')), db: Session=Depends(get_db)):
    row=db.get(ShenlunExercise, exercise_id)
    if not row:return ApiResponse.fail('练习不存在', code=404)
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
