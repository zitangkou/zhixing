"""独立金句库，只读写金句和证据，不暴露旧采集触发接口。"""
from datetime import date, timedelta
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.config import get_settings
from app.models.base import utcnow
from app.models import DailyQuote, DailyQuoteJob, DailyQuoteSelection
from app.schemas.daily_quotes import QuoteImportRequest, QuoteSaveRequest, QuoteRunRequest, QuoteSelectionRequest
from app.services.daily_quote_service import listing, out, save, preview_import, import_items
from app.services.daily_quote_jobs import enqueue, worker, job_out, generate_selected_examples

router = APIRouter(prefix='/daily-quotes', tags=['每日金句'])


@router.get('')
def list_quotes(start: date | None = None, end: date | None = None, q: str = '', topic: str = '', component: str = '',
                status: str = '', selected: str = '', selection_date: date | None = None,
                page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                admin=Depends(require_permission('rmrb:read')), db: Session = Depends(get_db)):
    return ApiResponse.ok(listing(db, start, end, q, topic, component, status, selected, selection_date, page, page_size))


@router.get('/export')
def export_quotes(start: date | None = None, end: date | None = None,
                  admin=Depends(require_permission('rmrb:read')), db: Session = Depends(get_db)):
    query = db.query(DailyQuote)
    if start: query = query.filter(DailyQuote.collected_date >= start)
    if end: query = query.filter(DailyQuote.collected_date <= end)
    return ApiResponse.ok([out(x) for x in query.order_by(DailyQuote.collected_date, DailyQuote.id)])


@router.get('/job')
def get_job(issue_date: date, admin=Depends(require_permission('rmrb:read')), db: Session = Depends(get_db)):
    row = db.query(DailyQuoteJob).filter_by(issue_date=issue_date).first(); cfg = get_settings()
    if row and row.status in {'queued', 'running'} and row.updated_at.replace(tzinfo=None) < utcnow().replace(tzinfo=None)-timedelta(hours=2):
        db.query(DailyQuoteJob).filter_by(id=row.id, status=row.status).update({'status':'failed', 'error':'执行进程中断，可重试', 'updated_at':utcnow()})
        db.commit(); db.refresh(row)
    return ApiResponse.ok({'job': job_out(row) if row else None, 'enabled': cfg.daily_quotes_enabled,
                           'llmConfigured': bool(cfg.llm_enabled and cfg.llm_api_key),
                           'schedule': f'{cfg.daily_quotes_hour:02d}:{cfg.daily_quotes_minute:02d}（北京时间）'})


@router.post('/run')
def run(body: QuoteRunRequest, background: BackgroundTasks, admin=Depends(require_permission('rmrb:write')), db: Session = Depends(get_db)):
    if body.issue_date > utcnow().date(): return ApiResponse.fail('不能整理未来刊期', code=400)
    try:
        row = enqueue(db, body.issue_date)
    except ValueError as exc: return ApiResponse.fail(str(exc), code=400)
    background.add_task(worker, row.id)
    return ApiResponse.ok(job_out(row), message='已提交整理；已成功的文章会跳过，失败项重新获取原文')


@router.post('/import-preview')
def preview(body: QuoteImportRequest, admin=Depends(require_permission('rmrb:write')), db: Session = Depends(get_db)):
    try: return ApiResponse.ok(preview_import(db, body.items, body.collected_date))
    except ValueError as exc: return ApiResponse.fail(str(exc), code=400)


@router.post('/import')
def import_quotes(body: QuoteImportRequest, admin=Depends(require_permission('rmrb:write')), db: Session = Depends(get_db)):
    try: return ApiResponse.ok(import_items(db, body.items, body.collected_date))
    except (ValueError, IntegrityError) as exc:
        db.rollback(); return ApiResponse.fail(str(exc) if isinstance(exc, ValueError) else '同时导入出现重复，请刷新后重试', code=400)


@router.get('/selection')
def get_selection(issue_date: date, admin=Depends(require_permission('rmrb:read')), db: Session = Depends(get_db)):
    return ApiResponse.ok([x.quote_id for x in db.query(DailyQuoteSelection).filter_by(issue_date=issue_date).order_by(DailyQuoteSelection.position)])


@router.put('/selection')
def selection(body: QuoteSelectionRequest, background: BackgroundTasks, admin=Depends(require_permission('rmrb:write')), db: Session = Depends(get_db)):
    ids = list(dict.fromkeys(body.quote_ids))
    if len(ids) != db.query(DailyQuote).filter(DailyQuote.id.in_(ids), DailyQuote.review_status == 'confirmed').count():
        return ApiResponse.fail('精选只能选择已确认且存在的金句', code=400)
    db.query(DailyQuoteSelection).filter_by(issue_date=body.issue_date).delete()
    for n, qid in enumerate(ids): db.add(DailyQuoteSelection(issue_date=body.issue_date, quote_id=qid, position=n))
    db.commit()
    can_generate = bool(get_settings().llm_enabled and get_settings().llm_api_key)
    if ids and can_generate: background.add_task(generate_selected_examples, ids)
    message = '精选已保存；仅为已选金句补充仿写示例' if can_generate else '精选已保存；服务端模型未启用，仿写暂未生成'
    return ApiResponse.ok({'selected': len(ids), 'examplesQueued': len(ids) if can_generate else 0}, message=message)


@router.post('/{quote_id}/examples')
def generate_examples(quote_id: str, background: BackgroundTasks,
                      admin=Depends(require_permission('rmrb:write')), db: Session = Depends(get_db)):
    row = db.get(DailyQuote, quote_id)
    if row is None: return ApiResponse.fail('金句不存在', code=404)
    if not row.enabled or row.audit_status != 'passed':
        return ApiResponse.fail('请先审核通过并启用金句，再生成仿写', code=400)
    cfg = get_settings()
    if not cfg.llm_enabled or not cfg.llm_api_key:
        return ApiResponse.fail('服务端模型未启用，暂不能生成仿写', code=400)
    attrs = parse(row.attributes_json)
    if attrs.get('examples'):
        return ApiResponse.ok({'generated': False, 'existing': True}, message='该金句已有仿写示例')
    if attrs.get('examplesStatus') == 'generating':
        return ApiResponse.ok({'generated': False, 'queued': True}, message='仿写正在生成')
    background.add_task(generate_selected_examples, [quote_id])
    return ApiResponse.ok({'generated': False, 'queued': True}, message='已提交仿写生成任务')


@router.get('/{quote_id}')
def detail(quote_id: str, admin=Depends(require_permission('rmrb:read')), db: Session = Depends(get_db)):
    row = db.get(DailyQuote, quote_id)
    return ApiResponse.ok(out(row)) if row else ApiResponse.fail('金句不存在', code=404)


def persist(body, db, admin, row=None):
    try:
        result = save(db, body.item, body.collected_date, row=row, reviewer=admin.username)
        return ApiResponse.ok(out(result))
    except (ValueError, IntegrityError) as exc:
        db.rollback(); return ApiResponse.fail(str(exc) if isinstance(exc, ValueError) else '该来源已有相同金句', code=400)


@router.post('')
def create(body: QuoteSaveRequest, admin=Depends(require_permission('rmrb:write')), db: Session = Depends(get_db)):
    return persist(body, db, admin)


@router.put('/{quote_id}')
def update(quote_id: str, body: QuoteSaveRequest, admin=Depends(require_permission('rmrb:write')), db: Session = Depends(get_db)):
    row = db.get(DailyQuote, quote_id)
    if row is None: return ApiResponse.fail('金句不存在', code=404)
    return persist(body, db, admin, row)


@router.delete('/{quote_id}')
def delete_quote(quote_id: str, admin=Depends(require_permission('rmrb:write')), db: Session = Depends(get_db)):
    row = db.get(DailyQuote, quote_id)
    if row is None: return ApiResponse.fail('金句不存在', code=404)
    db.query(DailyQuoteSelection).filter_by(quote_id=quote_id).delete()
    db.delete(row)
    db.commit()
    return ApiResponse.ok({'deleted': quote_id})
