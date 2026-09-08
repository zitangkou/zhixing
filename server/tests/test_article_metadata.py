from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Category, gen_id
from app.services.article_metadata import (
    infer_article_metadata,
    merge_article_fields,
    split_title_and_content,
)


def _session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    from app.database import Base

    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    theory = Category(id=gen_id("cat"), name="政治理论", sort_order=1)
    db.add(theory)
    db.flush()
    db.add(Category(id=gen_id("cat"), name="思想理论", parent_id=theory.id, sort_order=1))
    db.add(Category(id=gen_id("cat"), name="时政要闻", parent_id=theory.id, sort_order=2))
    db.commit()
    return db


def test_split_title_from_first_line():
    title, body = split_title_and_content("推动高质量发展\n\n这是正文第一段。")
    assert title == "推动高质量发展"
    assert "正文" in body


def test_infer_people_daily_article():
    db = _session()
    text = """【评论】深刻把握新质生产力内涵
http://politics.people.com.cn/n1/2026/0101/c1001-40123456.html

2026年1月1日，人民日报发表评论。新质生产力是高质量发展的内在要求。两个确立是根本保证。"""
    meta = infer_article_metadata(db, content=text)
    assert meta["title"] == "深刻把握新质生产力内涵"
    assert meta["source"] == "人民日报"
    assert "people.com.cn" in meta["source_url"]
    assert meta["publish_date"] == "2026-01-01"
    assert "新质生产力" in meta["summary"] or "新质生产力" in meta["tags"]
    assert "政治理论" in meta["tags"]
    assert meta["importance"] >= 4
    db.close()


def test_merge_fills_empty_fields():
    db = _session()
    content = "推动中国式现代化\n\n中国式现代化是强国建设的关键路径。"
    merged = merge_article_fields(
        db,
        title="",
        source="手动录入",
        source_url="",
        publish_date="",
        summary="",
        content=content,
        tags=[],
        category_id=None,
        importance=3,
    )
    assert merged["title"] == "推动中国式现代化"
    assert merged["source"] in ("手动录入", "人民日报")
    assert merged["summary"]
    assert merged["tags"]
    db.close()
