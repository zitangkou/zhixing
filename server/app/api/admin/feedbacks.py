"""学员反馈管理：查看与处理（采纳可加分 / 驳回）。

反馈由学员端 `POST /api/feedback` 落库，本模块只负责读取与人工处置；
加分一律在此显式触发，接口本身不再随机判定采纳。
"""

from app.api.admin._deps import *  # noqa: F401,F403

from app.models import Feedback
from app.models.base import utcnow
from app.schemas import FeedbackHandleBody, FeedbackOut
from app.services.user_service import add_points_log

router = APIRouter()


def _out(db: Session, row: Feedback) -> dict:
    account = db.get(AppUser, row.user_id)
    return FeedbackOut(
        id=row.id,
        userId=row.user_id,
        username=(account.username or account.nickname) if account else "",
        productKey=row.product_key,
        content=row.content,
        status=row.status,
        note=row.note,
        createdAt=row.created_at,
        handledAt=row.handled_at,
    ).model_dump()


@router.get("/feedbacks")
def list_feedbacks(
    status: str | None = Query(default=None),
    productKey: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    _admin=Depends(require_permission("feedback:read")),
    db: Session = Depends(get_db),
):
    query = db.query(Feedback)
    if status:
        query = query.filter(Feedback.status == status)
    if productKey:
        query = query.filter(Feedback.product_key == productKey)
    total = query.count()
    rows = query.order_by(Feedback.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return ApiResponse.ok({"items": [_out(db, r) for r in rows], "total": total, "page": page, "size": size})


@router.post("/feedbacks/{feedback_id}/handle")
def handle_feedback(
    feedback_id: str,
    body: FeedbackHandleBody,
    _admin=Depends(require_permission("feedback:write")),
    db: Session = Depends(get_db),
):
    row = db.get(Feedback, feedback_id)
    if not row:
        raise HTTPException(404, "反馈不存在")
    if row.status != "new":
        raise HTTPException(400, "该反馈已处理")

    row.status = body.action
    row.note = body.note
    row.handled_at = utcnow()

    if body.action == "adopted" and body.points > 0:
        user = db.get(AppUser, row.user_id)
        if user:
            add_points_log(db, user, body.points, "反馈", f"纠错反馈被采纳：{row.content[:30]}")

    db.commit()
    db.refresh(row)
    return ApiResponse.ok(_out(db, row))
