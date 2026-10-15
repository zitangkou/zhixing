"""大模型用量日志与按日期/用途汇总。"""
from datetime import date, datetime, time, timedelta
from sqlalchemy import func, case
from app.config import get_settings
from app.database import SessionLocal
from app.models import LlmUsageLog
from app.models.base import utcnow

def record_usage(*, purpose, model, status, usage=None, duration_ms=0, error_code=''):
    usage=usage if isinstance(usage,dict) else {}
    prompt=usage.get('prompt_tokens',usage.get('input_tokens'))
    completion=usage.get('completion_tokens',usage.get('output_tokens'))
    total=usage.get('total_tokens')
    try:
        with SessionLocal() as db:
            db.add(LlmUsageLog(purpose=purpose[:64],model=model[:128],status=status,
                prompt_tokens=int(prompt) if prompt is not None else None,
                completion_tokens=int(completion) if completion is not None else None,
                total_tokens=int(total) if total is not None else None,
                duration_ms=max(0,int(duration_ms)),error_code=error_code[:64],created_at=utcnow()))
            db.commit()
    except Exception:
        # 成本遥测故障不能让业务采集失败。
        return False
    return True

def summarize(db, start: date, end: date):
    # The app stores business timestamps as Beijing local time; SQLite strips tzinfo.
    begin=datetime.combine(start,time.min); finish=datetime.combine(end+timedelta(days=1),time.min)
    day_expr=func.date(LlmUsageLog.created_at)
    rows=(db.query(day_expr.label('day'),LlmUsageLog.purpose,LlmUsageLog.model,
        func.count(LlmUsageLog.id).label('calls'),
        func.sum(func.coalesce(LlmUsageLog.prompt_tokens,0)).label('prompt_tokens'),
        func.sum(func.coalesce(LlmUsageLog.completion_tokens,0)).label('completion_tokens'),
        func.sum(func.coalesce(LlmUsageLog.total_tokens,0)).label('total_tokens'),
        func.sum(case((LlmUsageLog.status=='success',1),else_=0)).label('successes'),
        func.sum(case((LlmUsageLog.status!='success',1),else_=0)).label('failures'),
        func.avg(LlmUsageLog.duration_ms).label('avg_duration_ms'))
        .filter(LlmUsageLog.created_at>=begin,LlmUsageLog.created_at<finish)
        .group_by(day_expr,LlmUsageLog.purpose,LlmUsageLog.model)
        .order_by(day_expr.desc(),LlmUsageLog.purpose).all())
    cfg=get_settings(); input_rate=cfg.llm_input_price_per_million; output_rate=cfg.llm_output_price_per_million
    pricing_configured=input_rate>0 and output_rate>0
    result=[]
    for r in rows:
        prompt=int(r.prompt_tokens or 0); completion=int(r.completion_tokens or 0)
        estimated=(prompt*input_rate+completion*output_rate)/1_000_000 if pricing_configured else None
        result.append({'date':str(r.day),'purpose':r.purpose,'model':r.model,'calls':r.calls,
            'successes':int(r.successes or 0),'failures':int(r.failures or 0),
            'promptTokens':prompt,'completionTokens':completion,'totalTokens':int(r.total_tokens or prompt+completion),
            'avgDurationMs':int(r.avg_duration_ms or 0),'estimatedCost':estimated})
    return {'items':result,'pricingConfigured':pricing_configured,
            'inputPricePerMillion':input_rate,'outputPricePerMillion':output_rate}
