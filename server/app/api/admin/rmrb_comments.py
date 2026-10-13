"""人民日报评论文章工作流 API。"""
from datetime import date
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, require_permission
from app.core.response import ApiResponse
from app.database import SessionLocal, get_db
from app.models import AdminUser, RmrbCommentArticle
from app.services.rmrb_comments_service import generate_analysis, list_comment_articles, list_peopleapp_opinion_articles, read_artifact, review_comment, run_daily_comment_analysis, scan_comments
from app.services.rmrb_archive_service import collect_peopleapp_opinion_recent, process_peopleapp_opinion_materials
from app.services.rmrb_comment_quotes_service import collect_ai_quotes, create_manual_quote, delete_quote, list_quotes, review_comment_article, review_quote, update_manual_quote
from app.services.rmrb_quote_ops_service import create_package, generate_copy, get_package, list_ops_quotes, list_packages, list_quote_library, mark_published, update_package

router = APIRouter(tags=["人民日报评论文章"])


@router.get("/rmrb-quotes/operations/pool")
def admin_list_rmrb_quote_ops_pool(q: str = "", topic: str = "", used: str = "unused",
                                  _admin=Depends(require_permission("rmrb:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(list_ops_quotes(db, q=q, topic=topic, used=used))


@router.get("/rmrb-quotes/library")
def admin_list_rmrb_quote_library(q: str = "", topic: str = "", used: str = "all",
                                  page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                                  _admin=Depends(require_permission("rmrb:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(list_quote_library(db, q=q, topic=topic, used=used, page=page, page_size=page_size))


@router.get("/rmrb-quotes/operations/packages")
def admin_list_rmrb_quote_ops_packages(issue_date: date | None = None,
                                       _admin=Depends(require_permission("rmrb:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(list_packages(db, issue_date=issue_date))


@router.get("/rmrb-quotes/operations/packages/{package_id}")
def admin_get_rmrb_quote_ops_package(package_id: str,
                                     _admin=Depends(require_permission("rmrb:read")), db: Session = Depends(get_db)):
    result = get_package(db, package_id)
    return ApiResponse.ok(result) if result else ApiResponse.fail("运营内容包不存在", code=404)


@router.post("/rmrb-quotes/operations/packages")
def admin_create_rmrb_quote_ops_package(body: dict, admin: AdminUser = Depends(get_current_admin),
                                        _perm=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    try:
        return ApiResponse.ok(create_package(db, body, admin.username), message="已建立当日运营内容草稿")
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)


@router.put("/rmrb-quotes/operations/packages/{package_id}")
def admin_update_rmrb_quote_ops_package(package_id: str, body: dict,
                                       _perm=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    try:
        result = update_package(db, package_id, body)
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(result) if result else ApiResponse.fail("运营内容包不存在", code=404)


@router.post("/rmrb-quotes/operations/packages/{package_id}/generate")
def admin_generate_rmrb_quote_ops_package(package_id: str,
                                         _perm=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    try:
        result = generate_copy(db, package_id)
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(result) if result else ApiResponse.fail("运营内容包不存在", code=404)


@router.post("/rmrb-quotes/operations/packages/{package_id}/publish")
def admin_mark_rmrb_quote_ops_published(package_id: str, body: dict,
                                       _perm=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    try:
        result = mark_published(db, package_id, str(body.get("channel") or ""))
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(result) if result else ApiResponse.fail("运营内容包不存在", code=404)


@router.get("/rmrb-comments/peopleapp-opinion")
def admin_list_peopleapp_opinion(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                                 _admin=Depends(require_permission("rmrb:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(list_peopleapp_opinion_articles(db, page=page, page_size=page_size))


@router.post("/rmrb-comments/peopleapp-opinion/collect")
def admin_collect_peopleapp_opinion(background_tasks: BackgroundTasks, _admin=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    try:
        result = collect_peopleapp_opinion_recent(db)
        background_tasks.add_task(process_peopleapp_opinion_materials, result["issueDates"])
        return ApiResponse.ok(result, message="文章元数据已采集；原文整理和三刀分析已提交后台处理")
    except Exception as exc:
        db.rollback()
        return ApiResponse.fail(f"客户端评论采集失败：{str(exc)[:300]}", code=502)


@router.put("/rmrb-comments/peopleapp-opinion/{record_id}/article-review")
def admin_review_peopleapp_opinion_article(record_id: str, body: dict, admin: AdminUser = Depends(get_current_admin),
                                           _perm=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    try:
        result = review_comment_article(db, record_id, str(body.get("decision") or ""),
                                        str(body.get("note") or ""), admin.username)
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(result) if result else ApiResponse.fail("评论文章记录不存在", code=404)


@router.get("/rmrb-comments/{record_id}/quotes")
def admin_list_rmrb_comment_quotes(record_id: str, _admin=Depends(require_permission("rmrb:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(list_quotes(db, record_id))


@router.post("/rmrb-comments/{record_id}/quotes/collect-ai")
def admin_collect_rmrb_comment_quotes(record_id: str, _admin=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    try:
        return ApiResponse.ok(collect_ai_quotes(db, record_id), message="金句候选已采集；请逐条核对原文并审核")
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
    except Exception as exc:
        db.rollback()
        return ApiResponse.fail(f"AI 金句提取失败：{str(exc)[:300]}", code=502)


@router.post("/rmrb-comments/{record_id}/quotes")
def admin_create_rmrb_comment_quote(record_id: str, body: dict,
                                    _admin=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    try:
        return ApiResponse.ok(create_manual_quote(db, record_id, body), message="人工金句已保存，等待审核")
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)


@router.put("/rmrb-comments/quotes/{quote_id}")
def admin_update_rmrb_comment_quote(quote_id: str, body: dict,
                                    _admin=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    try:
        result = update_manual_quote(db, quote_id, body)
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(result) if result else ApiResponse.fail("金句不存在", code=404)


@router.delete("/rmrb-comments/quotes/{quote_id}")
def admin_delete_rmrb_comment_quote(quote_id: str, _admin=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    return ApiResponse.ok({"deleted": True}) if delete_quote(db, quote_id) else ApiResponse.fail("金句不存在", code=404)


@router.put("/rmrb-comments/quotes/{quote_id}/review")
def admin_review_rmrb_comment_quote(quote_id: str, body: dict, admin: AdminUser = Depends(get_current_admin),
                                   _perm=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    try:
        result = review_quote(db, quote_id, str(body.get("decision") or ""), str(body.get("note") or ""), admin.username)
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(result) if result else ApiResponse.fail("金句不存在", code=404)


def _generate_worker(record_id: str):
    db = SessionLocal()
    try:
        generate_analysis(db, record_id)
    finally:
        db.close()


@router.get("/rmrb-comments")
def admin_list_rmrb_comments(issue_date: date | None = None, q: str = "", status: str = "",
                             _admin=Depends(require_permission("rmrb:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(list_comment_articles(db, issue_date=issue_date, q=q, status=status))


@router.post("/rmrb-comments/scan")
def admin_scan_rmrb_comments(issue_date: date, background_tasks: BackgroundTasks,
                             _admin=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    result = scan_comments(db, issue_date)
    background_tasks.add_task(run_daily_comment_analysis, issue_date)
    return ApiResponse.ok(result, message="评论文章扫描完成；已提交 AI 草稿生成（需启用服务端 LLM）")


@router.post("/rmrb-comments/{record_id}/analyze")
def admin_analyze_rmrb_comment(record_id: str, background_tasks: BackgroundTasks,
                               _admin=Depends(require_permission("rmrb:write")), db: Session = Depends(get_db)):
    row = db.query(RmrbCommentArticle).filter_by(id=record_id).first()
    if not row:
        return ApiResponse.fail("评论文章记录不存在", code=404)
    if row.analysis_status == "processing":
        return ApiResponse.fail("该文章正在生成分析稿", code=409)
    row.analysis_status = "processing"
    row.workflow_status = "analysis_processing"
    db.commit()
    background_tasks.add_task(_generate_worker, record_id)
    return ApiResponse.ok({"id": record_id, "analysisStatus": "processing"}, message="三刀解剖草稿已提交生成")


@router.put("/rmrb-comments/{record_id}/review")
def admin_review_rmrb_comment(record_id: str, body: dict,
                              admin: AdminUser = Depends(get_current_admin), _perm=Depends(require_permission("rmrb:write")),
                              db: Session = Depends(get_db)):
    try:
        result = review_comment(db, record_id, str(body.get("decision", "")), str(body.get("note", "")),
                               body.get("markdown"), admin.username)
    except ValueError as exc:
        db.rollback()
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(result) if result else ApiResponse.fail("评论文章记录不存在", code=404)


@router.get("/rmrb-comments/{record_id}/artifact")
def admin_read_rmrb_comment_artifact(record_id: str, kind: str = Query(pattern="^(original_md|original_html|analysis_md|analysis_html)$"),
                                    _admin=Depends(require_permission("rmrb:read")), db: Session = Depends(get_db)):
    row = db.query(RmrbCommentArticle).filter_by(id=record_id).first()
    if not row:
        return ApiResponse.fail("评论文章记录不存在", code=404)
    key = {"original_md": row.original_md_key, "original_html": row.original_html_key,
           "analysis_md": row.analysis_md_key, "analysis_html": row.analysis_html_key}[kind]
    if not key:
        return ApiResponse.fail("该物料尚未生成", code=404)
    try:
        content = read_artifact(key)
    except (OSError, ValueError) as exc:
        return ApiResponse.fail(f"读取物料失败：{exc}", code=404)
    if kind.endswith("html"):
        return HTMLResponse(content)
    return PlainTextResponse(content, media_type="text/markdown; charset=utf-8")
