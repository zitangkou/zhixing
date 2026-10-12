"""人民日报评论文章工作流 API。"""
from datetime import date
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, require_permission
from app.core.response import ApiResponse
from app.database import SessionLocal, get_db
from app.models import AdminUser, RmrbCommentArticle
from app.services.rmrb_comments_service import generate_analysis, list_comment_articles, read_artifact, review_comment, run_daily_comment_analysis, scan_comments

router = APIRouter(tags=["人民日报评论文章"])


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
