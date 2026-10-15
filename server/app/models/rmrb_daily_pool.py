"""人民日报当日共享采集池；文章正文仅作短期处理缓存。"""
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Integer, String, Text, UniqueConstraint
from app.models.base import Base, Mapped, mapped_column, utcnow, gen_id

class RmrbDailyPoolIssue(Base):
    __tablename__='rmrb_daily_pool_issues'
    issue_date: Mapped[date]=mapped_column(Date,primary_key=True)
    status: Mapped[str]=mapped_column(String(24),default='pending',index=True)
    page_count: Mapped[int]=mapped_column(Integer,default=0)
    article_count: Mapped[int]=mapped_column(Integer,default=0)
    failures_json: Mapped[str]=mapped_column(Text,default='[]')
    discovered_at: Mapped[datetime]=mapped_column(DateTime,default=utcnow)

class RmrbDailyPoolArticle(Base):
    __tablename__='rmrb_daily_pool_articles'
    __table_args__=(UniqueConstraint('issue_date','source_url',name='uq_rmrb_pool_issue_url'),)
    id: Mapped[str]=mapped_column(String(32),primary_key=True,default=lambda:gen_id('rpa'))
    issue_date: Mapped[date]=mapped_column(Date,index=True)
    source_url: Mapped[str]=mapped_column(String(1024),index=True)
    title: Mapped[str]=mapped_column(String(512),default='')
    page_no: Mapped[str]=mapped_column(String(8),default='',index=True)
    page_name: Mapped[str]=mapped_column(String(128),default='')
    page_refs_json: Mapped[str]=mapped_column(Text,default='[]')
    body_text: Mapped[str]=mapped_column(Text,default='')
    paragraphs_json: Mapped[str]=mapped_column(Text,default='[]')
    author: Mapped[str]=mapped_column(String(512),default='')
    body_sha256: Mapped[str]=mapped_column(String(64),default='',index=True)
    analysis_json: Mapped[str]=mapped_column(Text,default='{}')
    analysis_body_sha256: Mapped[str]=mapped_column(String(64),default='')
    analysis_rule_version: Mapped[str]=mapped_column(String(32),default='')
    fetched_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    expires_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True,index=True)
    fetch_error: Mapped[str]=mapped_column(String(256),default='')
