#!/usr/bin/env bash
# 生产宿主机使用北京时间 cron 调用；不等待联合分析，不重复启动当天成功/运行中的任务。
set -euo pipefail
docker exec -i -w /app/server zhixing-gongkao python -u - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import get_settings
from app.database import SessionLocal
from app.models import DailyQuoteJob
from app.services.daily_quote_jobs import enqueue, worker

issue_date = datetime.now(ZoneInfo('Asia/Shanghai')).date()
db = SessionLocal()
try:
    if not get_settings().daily_quotes_enabled:
        print(f'{issue_date}: daily quotes disabled', flush=True)
        raise SystemExit(0)
    old = db.query(DailyQuoteJob).filter_by(issue_date=issue_date).first()
    if old and old.status in {'queued', 'running', 'completed', 'empty'}:
        print(f'{issue_date}: skip existing job {old.id} ({old.status})', flush=True)
        raise SystemExit(0)
    job = enqueue(db, issue_date)
    job_id = job.id
    print(f'{issue_date}: started {job_id}', flush=True)
finally:
    db.close()
worker(job_id)
db = SessionLocal()
try:
    job = db.get(DailyQuoteJob, job_id)
    print(f'{issue_date}: finished {job_id} ({job.status})', flush=True)
    if job.status == 'failed':
        raise SystemExit(1)
finally:
    db.close()
PY
