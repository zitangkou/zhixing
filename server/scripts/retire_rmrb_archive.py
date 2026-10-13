"""停服后运行：预览/迁移有效金句/备份/退役旧档案数据。仅SQLite。
PYTHONPATH=. .venv/bin/python scripts/retire_rmrb_archive.py [--apply]
默认只预览，不修改DB。执行前须停止旧后端进程。
"""
import argparse
import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from sqlalchemy import inspect, text
from app.database import engine, SessionLocal
from app.models import DailyQuote, DailyQuoteSelection, DailyQuoteJob, RmrbCommentQuote
from app.services.daily_quote_service import normalize, save, parse
from app.upload_paths import DATA_DIR

TABLES = ['rmrb_quote_ops_package_items','rmrb_quote_ops_packages','rmrb_comment_quotes','rmrb_comment_exclusion_rules','rmrb_comment_articles','rmrb_article_evaluations','rmrb_archive_sources','rmrb_archive_revisions','rmrb_archive_articles','rmrb_archive_pages','rmrb_archive_issues','rmrb_archive_batches']


def build_items(db):
    if 'rmrb_comment_quotes' not in inspect(engine).get_table_names(): return []
    items=[]
    for old in db.query(RmrbCommentQuote).filter_by(review_status='approved'):
        art=old.comment_article.article
        evidence=(old.source_evidence or '').strip()
        # 用旧正文核对并抽取必要片段，不迁移全文。
        for rev in art.revisions:
            if rev.revision_no!=art.current_revision: continue
            candidate=(DATA_DIR/'rmrb'/rev.body_storage_key).resolve()
            allowed=(DATA_DIR/'rmrb/articles').resolve()
            if allowed not in candidate.parents: continue
            if candidate.exists():
                body=candidate.read_text(encoding='utf-8'); pos=body.find(old.text)
                if pos>=0: evidence=body[max(0,pos-90):pos+len(old.text)+90]
        verified=old.text in evidence
        if len(evidence)>1800:
            pos=evidence.find(old.text);evidence=evidence[max(0,pos-90):pos+len(old.text)+90] if pos>=0 else ''
        component={'argument':'论证句','论证':'论证句','opening':'开头点题','ending':'结尾升华','title':'分论点标题'}.get(old.quote_type,old.quote_type)
        if component not in {'论证句','开头点题','结尾升华','分论点标题'}:component='论证句'
        attrs={'text':old.text,'sourceUrl':art.primary_source_url,'articleTitle':art.display_title,'articleDate':art.issue_date.isoformat(),'source':f'人民日报 第{art.page_no}版 · {art.column_label}','author':art.author_line,'evidence':evidence if verified else '',
               'component':component,'topics':parse(old.topics_json,[]),'use':'、'.join(parse(old.use_cases_json,[])),
               'examples':[{'topic':'原有仿写（主题待补）','text':old.application_example}] if old.application_example else [],
               'reviewStatus':'confirmed' if verified else 'pending'}
        collected=old.created_at.date()
        normalize(attrs,collected)  # 无法迁移时阻止整个清理，不能悄悄丢金句。
        items.append((attrs,collected,old.reviewed_by,old.reviewed_at))
    return items


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if engine.dialect.name!='sqlite':raise SystemExit('当前仅支持SQLite安全备份')
    db=SessionLocal()
    try:
        tables=set(inspect(engine).get_table_names());counts={t:db.execute(text(f'SELECT count(*) FROM {t}')).scalar() for t in TABLES if t in tables}
        items=build_items(db);print(json.dumps({'oldRows':counts,'usefulQuotes':len(items),'apply':args.apply},ensure_ascii=False))
        if not args.apply:return
        stamp=datetime.now().strftime('%Y%m%d-%H%M%S');backup=DATA_DIR/'backups'/f'rmrb-retirement-{stamp}';backup.mkdir(parents=True)
        source=sqlite3.connect(engine.url.database);target=sqlite3.connect(backup/'database.db');source.backup(target);target.close();source.close()
        if (DATA_DIR/'rmrb').exists():shutil.copytree(DATA_DIR/'rmrb',backup/'rmrb')
        for model in (DailyQuote,DailyQuoteSelection,DailyQuoteJob):model.__table__.create(engine,checkfirst=True)
        for attrs,collected,reviewer,reviewed_at in items:
            _,_,fp=normalize(attrs,collected)
            row=db.query(DailyQuote).filter_by(fingerprint=fp).first()
            if row is None:
                row=save(db,attrs,collected,reviewer=reviewer,commit=False)
                if row.review_status=='confirmed':row.reviewed_at=reviewed_at
        db.flush()
        for attrs,collected,_,_ in items:
            _,_,fp=normalize(attrs,collected);row=db.query(DailyQuote).filter_by(fingerprint=fp).one()
            if row.text!=attrs['text']:raise RuntimeError('迁移核对失败')
        for table in TABLES:
            if table in tables:db.execute(text(f'DELETE FROM {table}'))
        db.commit()
        # 旧模块专用目录，不删除uploads、学员端rmrb_articles等业务数据。
        if (DATA_DIR/'rmrb').exists():shutil.rmtree(DATA_DIR/'rmrb')
        (backup/'manifest.json').write_text(json.dumps({'counts':counts,'migrated':len(items),'backupRetention':'核对完成后30天内人工清理'},ensure_ascii=False,indent=2))
        print('迁移及清理完成，备份：',backup)
    except Exception:db.rollback();raise
    finally:db.close()


if __name__=='__main__':main()
