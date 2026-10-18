"""共用人民日报版面目录和短期正文池，供词汇与金句流程复用。"""
import hashlib,json,re
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from urllib.parse import urlsplit,urlunsplit
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models import RmrbDailyPoolIssue,RmrbDailyPoolArticle
from app.models.base import utcnow
from app.services.rmrb_archive_service import _fetch_layout,_parse_index,_parse_page,USER_AGENT

POOL_TTL=timedelta(hours=48)
ANALYSIS_RULE_VERSION='2026-10-18-combined-v3'

def canonical_url(url):
    parsed=urlsplit(url)
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,'',''))


def normalized_source_text(value):
    """忽略网页抽取空白差异，仍保留文字与标点的逐字约束。"""
    return re.sub(r'\s+', '', str(value or ''))


def find_source_span(body, evidence):
    """返回原文中与证据匹配的原始切片；仅允许空白格式不同。"""
    body = str(body or '')
    compact_evidence = normalized_source_text(str(evidence or '').strip())
    if not compact_evidence:
        return ''
    compact_body = []
    offsets = []
    for index, char in enumerate(body):
        if not char.isspace():
            compact_body.append(char)
            offsets.append(index)
    start = ''.join(compact_body).find(compact_evidence)
    if start < 0:
        return ''
    end = start + len(compact_evidence)
    return body[offsets[start]:offsets[end - 1] + 1]

def _fetch_and_parse(url):
    response=httpx.get(url,timeout=30,follow_redirects=True,headers={'User-Agent':USER_AGENT})
    response.raise_for_status();response.encoding='utf-8'
    soup=BeautifulSoup(response.text,'html.parser')
    area=soup.select_one('.article')
    author=''
    if area:
        author_node=area.select_one('.author')
        author=author_node.get_text(' ',strip=True) if author_node else ''
        content=next((x for x in area.find_all('div',recursive=False) if not x.get('class')),None)
        paragraphs=[p.get_text(' ',strip=True) for p in content.find_all('p',recursive=False) if p.get_text(strip=True)] if content else []
        if not author:
            credit=area.select_one('p.sec')
            author=credit.get_text(' ',strip=True).split('《人民日报》')[0].strip() if credit else ''
    else:
        body=soup.select_one('#ozoom')
        if body is None:raise ValueError('文章正文区域未识别')
        for node in body.select('script,style'):node.decompose()
        paragraphs=[p.get_text(' ',strip=True) for p in body.select('p') if p.get_text(strip=True)]
        if not paragraphs:paragraphs=[x.strip() for x in body.get_text('\n',strip=True).splitlines() if x.strip()]
    if not paragraphs:raise ValueError('文章正文为空')
    return paragraphs,author

def discover_issue(issue_date:date,force=False):
    now=utcnow()
    with SessionLocal() as db:
        issue=db.get(RmrbDailyPoolIssue,issue_date)
        discovered_at = issue.discovered_at.replace(tzinfo=None) if issue and issue.discovered_at and issue.discovered_at.tzinfo else (issue.discovered_at if issue else None)
        comparable_now = now.replace(tzinfo=None) if now.tzinfo else now
        if issue and issue.status=='ready' and not force and discovered_at and discovered_at>comparable_now-timedelta(hours=8):
            return {'issueDate':issue_date.isoformat(),'pages':issue.page_count,'articles':issue.article_count,'failures':json.loads(issue.failures_json or '[]'),'cached':True}
    layout_url,html=_fetch_layout(issue_date)
    pages=_parse_index(issue_date,html,layout_url)
    failures=[];found={}
    def parse_page(page):
        try:return _parse_page(page),None
        except Exception as exc:return None,{'stage':'page','page':page['page_no'],'url':page['page_url'],'error':str(exc)[:200]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result,failure in pool.map(parse_page,pages):
            if failure:failures.append(failure);continue
            page,items=result
            for item in items:
                if item['title'].strip() in {'图片报道','图片新闻','图说'}:continue
                url=canonical_url(item['url'])
                if url in found:
                    row=found[url]
                    refs=row.setdefault('pageRefs',[])
                    if page['page_no'] not in [x['pageNo'] for x in refs]:refs.append({'pageNo':page['page_no'],'pageName':page['page_name']})
                else:
                    found[url]={**item,'url':url,'pageNo':page['page_no'],'pageName':page['page_name'],'pageRefs':[{'pageNo':page['page_no'],'pageName':page['page_name']}]}
    with SessionLocal() as db:
        issue=db.get(RmrbDailyPoolIssue,issue_date)
        if issue is None:issue=RmrbDailyPoolIssue(issue_date=issue_date);db.add(issue)
        issue.status='partial' if failures else 'ready';issue.page_count=len(pages);issue.article_count=len(found)
        issue.failures_json=json.dumps(failures,ensure_ascii=False);issue.discovered_at=now
        for item in found.values():
            row=db.query(RmrbDailyPoolArticle).filter_by(issue_date=issue_date,source_url=item['url']).first()
            if row is None:row=RmrbDailyPoolArticle(issue_date=issue_date,source_url=item['url']);db.add(row)
            row.title=item['title'];row.page_no=item['pageNo'];row.page_name=item['pageName']
            row.page_refs_json=json.dumps(item.get('pageRefs',[]),ensure_ascii=False)
        db.commit()
    return {'issueDate':issue_date.isoformat(),'pages':len(pages),'articles':len(found),'failures':failures,'cached':False}

def get_metadata(issue_date:date,force=False):
    discover_issue(issue_date,force=force)
    with SessionLocal() as db:
        rows=db.query(RmrbDailyPoolArticle).filter_by(issue_date=issue_date).order_by(RmrbDailyPoolArticle.page_no,RmrbDailyPoolArticle.source_url).all()
        return [{'url':r.source_url,'title':r.title,'page':r.page_no,'pageNo':r.page_no,'pageName':r.page_name,
                 'pageRefs':json.loads(r.page_refs_json or '[]'),'bodySha256':r.body_sha256,
                 'scope':'unknown'} for r in rows]

def get_article_content(issue_date:date,url:str,force=False):
    canonical=canonical_url(url)
    with SessionLocal() as db:
        row=db.query(RmrbDailyPoolArticle).filter_by(issue_date=issue_date,source_url=canonical).first()
        if row is None:
            get_metadata(issue_date)
            row=db.query(RmrbDailyPoolArticle).filter_by(issue_date=issue_date,source_url=canonical).first()
        if row is None:raise ValueError('文章不在人民日报当日采集目录中')
        now=utcnow()
        # SQLite DateTime 会丢失 tzinfo；统一按项目约定的北京时间墙上时间比较。
        expires_at = row.expires_at.replace(tzinfo=None) if row.expires_at and row.expires_at.tzinfo else row.expires_at
        comparable_now = now.replace(tzinfo=None) if now.tzinfo else now
        if not force and row.body_text and expires_at and expires_at>comparable_now:
            return {'url':row.source_url,'title':row.title,'pageNo':row.page_no,'pageName':row.page_name,
                    'body':row.body_text,'paragraphs':json.loads(row.paragraphs_json or '[]'),'author':row.author,
                    'bodySha256':row.body_sha256,'cached':True}
        paragraphs,author=_fetch_and_parse(canonical)
        body='\n'.join(paragraphs);digest=hashlib.sha256(body.encode()).hexdigest()
        row.body_text=body;row.paragraphs_json=json.dumps(paragraphs,ensure_ascii=False);row.author=author
        row.body_sha256=digest;row.fetched_at=now;row.expires_at=now+POOL_TTL;row.fetch_error='';db.commit()
        return {'url':row.source_url,'title':row.title,'pageNo':row.page_no,'pageName':row.page_name,
                'body':body,'paragraphs':paragraphs,'author':author,'bodySha256':digest,'cached':False}

def get_full_articles(issue_date:date):
    metadata=get_metadata(issue_date)
    articles=[];failures=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[(item,pool.submit(get_article_content,issue_date,item['url'])) for item in metadata]
        for item,future in futures:
            try:articles.append(future.result())
            except Exception as exc:failures.append({'url':item['url'],'error':str(exc)[:200]})
    return articles,failures,len(metadata)

def get_analysis(issue_date:date,url:str,body_sha256:str=''):
    with SessionLocal() as db:
        row=db.query(RmrbDailyPoolArticle).filter_by(issue_date=issue_date,source_url=canonical_url(url)).first()
        if not row or not row.analysis_json:return None
        if body_sha256 and row.analysis_body_sha256!=body_sha256:return None
        try:
            value=json.loads(row.analysis_json)
            if not isinstance(value,dict):return None
            if value.get('ruleVersion')!=row.analysis_rule_version:return None
            return value
        except (ValueError,TypeError):return None

def save_analysis(issue_date:date,url:str,body_sha256:str,result:dict,rule_version:str):
    with SessionLocal() as db:
        row=db.query(RmrbDailyPoolArticle).filter_by(issue_date=issue_date,source_url=canonical_url(url)).first()
        if row is None:return False
        row.analysis_json=json.dumps(result,ensure_ascii=False,separators=(',',':'))
        row.analysis_body_sha256=body_sha256;row.analysis_rule_version=rule_version
        db.commit();return True

def save_analyses(issue_date:date,entries:list[dict],rule_version:str):
    """批次持久化逐篇结构化候选，减少共享SQLite库的逐条写入。"""
    if not entries:return 0
    urls={canonical_url(item['url']) for item in entries}
    with SessionLocal() as db:
        rows=db.query(RmrbDailyPoolArticle).filter(RmrbDailyPoolArticle.issue_date==issue_date,
            RmrbDailyPoolArticle.source_url.in_(urls)).all()
        by_url={row.source_url:row for row in rows};saved=0
        for item in entries:
            row=by_url.get(canonical_url(item['url']))
            if row is None:continue
            row.analysis_json=json.dumps(item['result'],ensure_ascii=False,separators=(',',':'))
            row.analysis_body_sha256=item['bodySha256'];row.analysis_rule_version=rule_version;saved+=1
        db.commit();return saved

def prune_expired_bodies():
    with SessionLocal() as db:
        now=utcnow()
        rows=db.query(RmrbDailyPoolArticle).filter(RmrbDailyPoolArticle.expires_at.isnot(None),RmrbDailyPoolArticle.expires_at<=now).all()
        for row in rows:
            row.body_text='';row.paragraphs_json='[]';row.author='';row.body_sha256='';row.expires_at=None;row.fetch_error='缓存到期'
            row.analysis_json='{}';row.analysis_body_sha256='';row.analysis_rule_version=''
        # 正文处理池只保留最近 7 天目录元数据，长期文章档案由正式档案模块管理。
        db.query(RmrbDailyPoolArticle).filter(RmrbDailyPoolArticle.issue_date<now.date()-timedelta(days=7)).delete(synchronize_session=False)
        db.query(RmrbDailyPoolIssue).filter(RmrbDailyPoolIssue.discovered_at<now-timedelta(days=365)).delete(synchronize_session=False)
        db.commit();return len(rows)
