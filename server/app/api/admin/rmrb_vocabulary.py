from datetime import date
from typing import Literal
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import not_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import RmrbVocabulary, RmrbVocabularyJob
from app.services.rmrb_vocabulary_service import RULES, out, job_out, run_job

router=APIRouter(prefix='/rmrb-vocabulary',tags=['人民日报词汇素材'])
class CollectBody(BaseModel):
    issue_date: date
class ReviewBody(BaseModel):
    ids: list[str]=Field(min_length=1,max_length=100)
    status: Literal['pending','approved','rejected']
    note: str=Field(default='',max_length=2000)

@router.get('/rules')
def rules(admin=Depends(require_permission('rmrb:read'))):return ApiResponse.ok(RULES)

@router.get('')
def listing(issue_date: date|None=None,q: str='',kind: str='',status: str='',priority: str='',page: int=Query(1,ge=1),page_size: int=Query(20,ge=1,le=100),admin=Depends(require_permission('rmrb:read')),db: Session=Depends(get_db)):
    query=db.query(RmrbVocabulary)
    if issue_date:query=query.filter(RmrbVocabulary.issue_date==issue_date)
    if q:query=query.filter(or_(RmrbVocabulary.phrase.contains(q),RmrbVocabulary.source_title.contains(q),RmrbVocabulary.payload_json.contains(q)))
    if kind:query=query.filter(RmrbVocabulary.kind==kind)
    if status:query=query.filter(RmrbVocabulary.review_status==status)
    if priority in RULES['priorities']:
        # JSON 由历史版本以带空格或紧凑格式序列化；旧记录按补充项兼容展示。
        spaced='"studyPriority": "'+priority+'"'; compact='"studyPriority":"'+priority+'"'
        match=or_(RmrbVocabulary.payload_json.contains(spaced),RmrbVocabulary.payload_json.contains(compact))
        if priority=='supplementary':match=or_(match,not_(RmrbVocabulary.payload_json.contains('studyPriority')))
        query=query.filter(match)
    elif priority:
        return ApiResponse.fail('学习优先级不在允许范围',code=400)
    total=query.count()
    return ApiResponse.ok({'items':[out(r) for r in query.order_by(RmrbVocabulary.issue_date.desc(),RmrbVocabulary.created_at.desc()).offset((page-1)*page_size).limit(page_size)],'total':total})

@router.get('/jobs')
def jobs(admin=Depends(require_permission('rmrb:read')),db: Session=Depends(get_db)):
    return ApiResponse.ok([job_out(j) for j in db.query(RmrbVocabularyJob).order_by(RmrbVocabularyJob.updated_at.desc()).limit(20)])

@router.post('/collect')
def collect(body: CollectBody,tasks: BackgroundTasks,admin=Depends(require_permission('rmrb:write')),db: Session=Depends(get_db)):
    from app.timezone import now
    if body.issue_date>now().date():return ApiResponse.fail('不能采集未来日期',code=400)
    job=db.query(RmrbVocabularyJob).filter_by(issue_date=body.issue_date).first()
    if job and job.status in ('pending','running'):return ApiResponse.ok(job_out(job),message='当天任务正在运行')
    if job is None:
        job=RmrbVocabularyJob(issue_date=body.issue_date);db.add(job)
    job.status='pending';job.error='';job.progress_json='{}'
    try:db.commit()
    except IntegrityError:
        db.rollback();return ApiResponse.fail('当天任务已提交，请刷新采集批次',code=409)
    tasks.add_task(run_job,job.id)
    return ApiResponse.ok(job_out(job))

@router.put('/review')
def review(body: ReviewBody,admin=Depends(require_permission('rmrb:write')),db: Session=Depends(get_db)):
    rows=db.query(RmrbVocabulary).filter(RmrbVocabulary.id.in_(set(body.ids))).all()
    if len(rows)!=len(set(body.ids)):return ApiResponse.fail('部分素材不存在，请刷新',code=400)
    for row in rows:
        row.review_status=body.status;row.review_note=body.note;row.reviewed_by=admin.username
    db.commit();return ApiResponse.ok({'updated':len(rows)})

class EditBody(BaseModel):
    kind: Literal['idiom','expression','term']
    studyPriority: Literal['core','useful','supplementary'] | None = None
    meaning: str=Field(min_length=1,max_length=2000)
    topics: list[str]=Field(min_length=1,max_length=10)
    useCases: list[str]=Field(min_length=1,max_length=10)
    sample: str=Field(min_length=1,max_length=2000)
    usageNote: str=Field(default='',max_length=2000)

@router.put('/{item_id}')
def edit(item_id: str,body: EditBody,admin=Depends(require_permission('rmrb:write')),db: Session=Depends(get_db)):
    import json
    row=db.get(RmrbVocabulary,item_id)
    if not row:return ApiResponse.fail('词汇素材不存在',code=404)
    values=body.model_dump(exclude_none=True)
    if any(not str(values[key]).strip() for key in ('meaning','sample')) or any(not v.strip() for k in ('topics','useCases') for v in values[k]):
        return ApiResponse.fail('释义、示例、主题和场景不能为空',code=400)
    payload=json.loads(row.payload_json);payload.update(values);row.payload_json=json.dumps(payload,ensure_ascii=False)
    row.kind=body.kind;row.review_status='pending';row.reviewed_by=admin.username
    row.review_note='内容已编辑，请重新审核'
    db.commit();return ApiResponse.ok(out(row))
