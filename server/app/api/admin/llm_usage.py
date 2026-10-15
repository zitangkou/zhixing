"""大模型调用量与费用估算。"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.services.ai.llm_usage_service import summarize
from app.timezone import now

router=APIRouter(prefix='/llm-usage',tags=['大模型用量'])
@router.get('/summary')
def summary(start: date|None=None,end: date|None=None,
           admin=Depends(require_permission('setting:read')),db: Session=Depends(get_db)):
    today=now().date(); finish=end or today; begin=start or finish-timedelta(days=29)
    if begin>finish:return ApiResponse.fail('开始日期不能晚于结束日期',code=400)
    if (finish-begin).days>366:return ApiResponse.fail('单次最多查询367天',code=400)
    return ApiResponse.ok({'start':begin.isoformat(),'end':finish.isoformat(),**summarize(db,begin,finish)})
