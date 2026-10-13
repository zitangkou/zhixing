from datetime import date
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import DailyQuote, DailyQuoteSelection, DailyQuoteJob
from app.services.daily_quote_service import import_items, listing, normalize, save, preview_import
from app.services import daily_quote_jobs as jobs
DAY=date(2026,10,13)
@pytest.fixture
def db(tmp_path):
    engine=create_engine(f'sqlite:///{tmp_path}/quotes.db')
    for m in (DailyQuote,DailyQuoteSelection,DailyQuoteJob):m.__table__.create(engine)
    factory=sessionmaker(bind=engine,autoflush=False)
    with factory() as session:yield session,factory
    engine.dispose()
def item(text='问题在哪里，行动就在哪里。'):
    return {'text':text,'url':'https://paper.people.com.cn/rmrb/pc/content/202610/13/content_1.html','title':'问题与行动','articleDate':DAY.isoformat(),'component':'论证句','evidence':f'前文。{text}后文。','topics':['基层治理'],'examples':[{'topic':'民生服务','text':'回应具体诉求。','highlights':['具体诉求']},{'topic':'科技创新','text':'科研回应真实问题。'}]}
def test_duplicate_and_source_protocol(db):
    s,_=db;assert import_items(s,[item(),item()],DAY)=={'added':1,'skipped':1}
    x=item();x['url']=x['url'].replace('https:','http:')+'?ref=1'
    assert import_items(s,[x],DAY)['added']==0
    assert s.query(DailyQuote).one().text==item()['text']
def test_evidence_highlight_validation(db):
    s,_=db;x=item();x['evidence']='伪证据'
    with pytest.raises(ValueError,match='逐字'):normalize(x,DAY)
    x=item();x['highlights']=['不存在']
    with pytest.raises(ValueError,match='高亮'):normalize(x,DAY)
    x=item();x['evidence']='';x['reviewStatus']='confirmed'
    with pytest.raises(ValueError,match='证据'):save(s,x,DAY)
    x['reviewStatus']='pending';save(s,x,DAY)
def test_exact_topic_and_global_stats(db):
    s,_=db;import_items(s,[item(),item('坚持长期投入。')],DAY)
    r=listing(s,start=DAY,end=DAY,topic='民生服务',page_size=1)
    assert len(r['items'])==1 and r['total']==2
    assert r['stats']=={'quotes':2,'sources':1,'examples':4,'selected':0}
    assert listing(s,topic='民生')['total']==0
def test_archive_selection(db):
    s,_=db;x=item();x['reviewStatus']='confirmed';r=save(s,x,DAY)
    s.add(DailyQuoteSelection(issue_date=DAY,quote_id=r.id));s.commit()
    x['reviewStatus']='archived';save(s,x,DAY,row=r)
    assert s.query(DailyQuoteSelection).count()==0
def test_atomic_invalid_import(db):
    s,_=db;x=item();x['examples']=[{'topic':'','text':'示例'}]
    assert preview_import(s,[x],DAY)[0]['status']=='invalid'
    with pytest.raises(ValueError):import_items(s,[item(),x],DAY)
    assert s.query(DailyQuote).count()==0
def test_partial_retry_no_fulltext(db,monkeypatch):
    s,f=db;monkeypatch.setattr(jobs,'SessionLocal',f)
    monkeypatch.setattr(jobs,'get_settings',lambda:SimpleNamespace(llm_enabled=True,llm_api_key='test'))
    articles=[{'url':item()['url']},{'url':item()['url'].replace('_1.html','_2.html')}]
    monkeypatch.setattr(jobs,'discover',lambda _: (articles,[]))
    full='全文标记不应持久化'*30
    monkeypatch.setattr(jobs,'original',lambda a: ([item()['text'],full],{'sourceUrl':a['url'],'articleTitle':'文章','source':'人民日报'}))
    calls=[]
    def ai(*_):
        calls.append(1)
        if len(calls)==2:raise RuntimeError(full)
        return {'items':[item()]}
    monkeypatch.setattr(jobs,'chat_json',ai)
    j=jobs.enqueue(s,DAY);jid=j.id;jobs.worker(jid);s.expire_all();j=s.get(DailyQuoteJob,jid)
    assert j.status=='partial' and s.query(DailyQuote).count()==1
    assert full not in j.progress_json and full not in j.error
    assert full not in s.query(DailyQuote).one().attributes_json
    jobs.enqueue(s,DAY);jobs.worker(jid);s.expire_all()
    assert s.get(DailyQuoteJob,jid).status=='completed' and len(calls)==3
    assert s.query(DailyQuote).count()==2
def test_old_routes_removed():
    from app.main import app
    paths=[getattr(x,'path','') for x in app.routes]
    assert '/admin/daily-quotes/run' in paths
    assert not any(p.startswith(('/admin/rmrb-archive','/admin/rmrb-comments','/admin/rmrb-quotes')) for p in paths)

def test_retirement_preserves_confirmed_data(tmp_path,monkeypatch):
    import importlib.util,sys
    from pathlib import Path
    from app.models import Base,RmrbArchiveIssue,RmrbArchiveArticle,RmrbCommentArticle,RmrbCommentQuote
    data=tmp_path/'data';data.mkdir()
    e=create_engine(f'sqlite:///{data}/database.db');Base.metadata.create_all(e);factory=sessionmaker(bind=e,autoflush=False)
    with factory() as s:
        s.add(RmrbArchiveIssue(id='i',issue_date=DAY));s.flush()
        s.add(RmrbArchiveArticle(id='a',issue_id='i',issue_date=DAY,display_title='来源',primary_source_url=item()['url']));s.flush()
        s.add(RmrbCommentArticle(id='c',article_id='a'));s.flush()
        s.add(RmrbCommentQuote(id='q',comment_article_id='c',text=item()['text'],review_status='approved',source_evidence=item()['evidence'],application_example='仿写内容'));s.commit()
    spec=importlib.util.spec_from_file_location('retire',Path(__file__).parents[1]/'scripts/retire_rmrb_archive.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'engine',e);monkeypatch.setattr(module,'SessionLocal',factory);monkeypatch.setattr(module,'DATA_DIR',data);monkeypatch.setattr(sys,'argv',['retire','--apply']);module.main()
    with factory() as s:
        row=s.query(DailyQuote).one();assert row.text==item()['text'] and row.review_status=='confirmed'
        assert item()['text'] in module.parse(row.attributes_json)['evidence']
        assert s.query(RmrbArchiveArticle).count()==0 and s.query(RmrbCommentQuote).count()==0
    assert list((data/'backups').glob('*/database.db'))
    e.dispose()
