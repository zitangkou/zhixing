"""时评仅收人民日报（署名/原文链接判定）、原文日期回填、政治理论分类幂等补齐。"""

from __future__ import annotations

import os
from pathlib import Path

_DB = Path(__file__).resolve().parent / "_rmrb_source.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SECRET_KEY"] = "rmrb-source-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin123"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.main import app  # noqa: E402
from app.models import Base, Category  # noqa: E402
from app.services.article_import import (  # noqa: E402
    display_html_source_rejection,
    parse_rmrb_source_html,
    rmrb_source_rejection,
    source_from_url,
)
from app.services.category_service import (  # noqa: E402
    THEORY_CHILDREN,
    ensure_theory_categories,
    seed_default_categories,
)


def _source_html(title: str, byline: str, href: str, *, footer: str = "") -> str:
    """精简版运营「原文」HTML：页头套话 + h1 + 署名行 + 正文 + 底部来源卡。"""
    return f"""<section>
  <div>人民时评 · 精读系列</div>
  <div>人民日报评论文章 · 申论素材拆解</div>
  <a href="{href}">📄 查看人民日报原文</a>
  <h1>《{title}》</h1>
  <p>{byline}</p>
  <p>第一段正文，讨论基层治理中的具体问题，字数足够作为摘要。</p>
  <p>第二段正文，继续展开论证。</p>
  <div><b>📄 原文出处：</b>{footer or byline.lstrip("— ")}<br>
  版权归人民日报及原作者所有。<a href="{href}">点击查看人民日报原文</a></div>
</section>"""


JJRB_HTML = _source_html(
    "“吹哨”有奖更要“护哨”有方",
    "—— 经济日报（中工网转载）2026-09-24",
    "https://www.workercn.cn/c/2026-09-24/8902305.shtml",
)
RMRB_HTML = _source_html(
    "“发得出”更要“用得好”",
    "—— 人民日报 2026-09-24 第07版 评论 | 栏目:人民时评",
    "http://paper.people.com.cn/rmrb/pc/content/202609/24/content_30182857.html",
)
RMRB_OLD_HTML = _source_html(
    "历史回填示例",
    "—— 人民日报 2026-08-07 第05版 评论 | 栏目:人民时评",
    "http://paper.people.com.cn/rmrb/pc/content/202608/07/content_1.html",
)


def _ok(res):
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("code") == 0, body
    return body.get("data")


def _fail_message(res) -> str:
    body = res.json()
    assert body.get("code") != 0, body
    return body.get("message") or ""


# ---------- 纯函数 ----------


def test_byline_wins_over_header_boilerplate():
    parsed, _ = parse_rmrb_source_html(JJRB_HTML)
    assert parsed["source"] == "经济日报"
    assert parsed["publish_date"] == "2026-09-24"
    reason = rmrb_source_rejection(parsed["source"], parsed["source_url"])
    assert reason == "该文来源为《经济日报》，时评模块仅接收人民日报文章"


def test_rmrb_byline_passes_with_original_date():
    parsed, _ = parse_rmrb_source_html(RMRB_HTML)
    assert parsed["source"] == "人民日报"
    assert parsed["publish_date"] == "2026-09-24"
    assert rmrb_source_rejection(parsed["source"], parsed["source_url"]) is None


def test_header_boilerplate_alone_is_not_a_source():
    html = """<section><div>人民时评 · 精读系列</div><div>人民日报评论文章 · 申论素材拆解</div>
    <h1>无署名文章</h1><p>正文第一段。</p><p>正文第二段。</p></section>"""
    parsed, _ = parse_rmrb_source_html(html)
    assert parsed["source"] == ""


def test_url_domain_fallback():
    assert source_from_url("http://paper.people.com.cn/rmrb/x.html") == "人民日报"
    assert source_from_url("https://opinion.people.com.cn/n1/x.html") == "人民日报"
    assert source_from_url("https://www.ce.cn/xwzx/x.shtml") == "经济日报"
    assert source_from_url("https://www.workercn.cn/c/x.shtml") != "人民日报"
    assert source_from_url("https://example.com/x") == ""
    # 无署名时按链接判定；「人民时评」只是栏目名，不能掩盖外站链接
    assert rmrb_source_rejection("", "https://www.gmw.cn/x.html")
    assert rmrb_source_rejection("人民时评", "https://www.ce.cn/x.shtml")
    assert rmrb_source_rejection("", "http://paper.people.com.cn/x.html") is None
    assert rmrb_source_rejection("", "https://example.com/x") is None
    assert rmrb_source_rejection("人民时评", "") is None
    # 无署名但正文无链接的 HTML 也按链接兜底
    html = """<section><h1>只有链接</h1><p>正文。</p><p>正文二。</p>
    <a href="https://www.ce.cn/xwzx/x.shtml">原文</a></section>"""
    parsed, _ = parse_rmrb_source_html(html)
    assert parsed["source"] == "经济日报"


def test_display_html_rejection():
    bad = '<div><p>解剖</p><a href="https://www.workercn.cn/c/1.shtml">📄 点击查看原文（经济日报）</a></div>'
    good = '<div><p>解剖</p><a href="http://paper.people.com.cn/rmrb/1.html">📄 点击查看原文（人民日报）</a></div>'
    assert display_html_source_rejection(bad) == "该文来源为《经济日报》，时评模块仅接收人民日报文章"
    assert display_html_source_rejection(good) is None
    assert display_html_source_rejection("<div><p>无链接</p></div>") is None


# ---------- 分类 ----------


def _mem_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_seed_empty_table_has_all_theory_children():
    db = _mem_session()
    seed_default_categories(db)
    db.commit()
    root = db.query(Category).filter(Category.name == "政治理论", Category.parent_id.is_(None)).one()
    children = db.query(Category).filter(Category.parent_id == root.id).order_by(Category.sort_order).all()
    assert [c.name for c in children] == list(THEORY_CHILDREN)
    assert ensure_theory_categories(db) == []
    db.close()


def test_ensure_missing_is_idempotent_on_existing_table():
    db = _mem_session()
    root = Category(id="cat_root", name="政治理论", sort_order=1)
    db.add(root)
    db.add(Category(id="cat_a", name="时政要闻", parent_id="cat_root", sort_order=1))
    db.add(Category(id="cat_b", name="思想理论", parent_id="cat_root", sort_order=2))
    db.add(Category(id="cat_c", name="政策法规", parent_id="cat_root", sort_order=3))
    # 已停用的也算存在，不重复创建
    db.add(Category(id="cat_d", name="生态文明", parent_id="cat_root", sort_order=9, is_active=False))
    db.add(Category(id="cat_h", name="党史学习", sort_order=2))
    db.commit()

    added = ensure_theory_categories(db)
    db.commit()
    assert added == ["大国外交", "经济发展", "民生保障", "科技自立自强"]
    names = [c.name for c in db.query(Category).filter(Category.parent_id == "cat_root").order_by(Category.sort_order)]
    assert names[:3] == ["时政要闻", "思想理论", "政策法规"]
    assert names.count("生态文明") == 1
    orders = [c.sort_order for c in db.query(Category).filter(Category.parent_id == "cat_root")]
    assert len(orders) == len(set(orders))

    # 第二次（再次启动）不再新增
    seed_default_categories(db)
    db.commit()
    assert ensure_theory_categories(db) == []
    assert db.query(Category).count() == 1 + 8 + 1
    db.close()


# ---------- 接口 ----------


def test_admin_rmrb_import_rejects_non_rmrb_and_keeps_original_date():
    with TestClient(app) as client:
        login = client.post("/admin/auth/login", json={"username": "admin", "password": "admin123"})
        headers = {"Authorization": f"Bearer {_ok(login)['access_token']}"}

        # 预览即拦截
        msg = _fail_message(client.post("/admin/rmrb/preview-html", json={"html": JJRB_HTML}, headers=headers))
        assert "经济日报" in msg and "仅接收人民日报" in msg
        preview = _ok(client.post("/admin/rmrb/preview-html", json={"html": RMRB_HTML}, headers=headers))
        assert preview["source"] == "人民日报"
        assert preview["publishDate"] == "2026-09-24"

        # 直接新建也拦截（默认 source=人民时评 不能掩盖署名）
        msg = _fail_message(client.post(
            "/admin/rmrb/article",
            json={"contentHtml": JJRB_HTML, "source": "人民时评", "isPublished": True},
            headers=headers,
        ))
        assert msg == "该文来源为《经济日报》，时评模块仅接收人民日报文章"

        # 不预览直接导入历史文章：用原文日期而不是今天
        created = _ok(client.post(
            "/admin/rmrb/article",
            json={"contentHtml": RMRB_OLD_HTML, "isPublished": True},
            headers=headers,
        ))
        assert created["source"] == "人民日报"
        assert created["publishDate"] == "2026-08-07"

        # 手填日期仍优先
        manual = _ok(client.post(
            "/admin/rmrb/article",
            json={"contentHtml": RMRB_HTML, "publishDate": "2026-09-30", "isPublished": False},
            headers=headers,
        ))
        assert manual["publishDate"] == "2026-09-30"

        # 编辑时换成外站原文也拦截
        msg = _fail_message(client.put(
            f"/admin/rmrb/article/{manual['id']}",
            json={"contentHtml": JJRB_HTML},
            headers=headers,
        ))
        assert "经济日报" in msg
        msg = _fail_message(client.put(
            f"/admin/rmrb/article/{manual['id']}",
            json={"source": "光明日报"},
            headers=headers,
        ))
        assert msg == "该文来源为《光明日报》，时评模块仅接收人民日报文章"
        msg = _fail_message(client.put(
            f"/admin/rmrb/article/{manual['id']}",
            json={"source": "人民时评", "sourceUrl": "https://www.ce.cn/xwzx/x.shtml"},
            headers=headers,
        ))
        assert "仅接收人民日报" in msg
        # 与来源无关的编辑不受影响
        _ok(client.put(f"/admin/rmrb/article/{manual['id']}", json={"isPublished": True}, headers=headers))

        # 三刀解析：人民日报文章可挂，外站「查看原文」拦截
        bad_display = (
            '<section><p>三刀解剖</p>'
            '<a href="https://www.workercn.cn/c/1.shtml">📄 点击查看原文（经济日报）</a></section>'
        )
        good_display = (
            '<section><p>三刀解剖</p>'
            '<a href="http://paper.people.com.cn/rmrb/1.html">📄 点击查看原文（人民日报）</a></section>'
        )
        msg = _fail_message(client.post(
            "/admin/rmrb/import-three-knife",
            json={"articleId": created["id"], "displayHtml": bad_display},
            headers=headers,
        ))
        assert "经济日报" in msg
        _ok(client.post(
            "/admin/rmrb/import-three-knife",
            json={"articleId": created["id"], "displayHtml": good_display},
            headers=headers,
        ))
