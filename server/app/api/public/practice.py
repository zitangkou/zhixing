"""Q7 资料分析最小学习闭环 — 公开 API（/api/practice/）

无需 admin JWT，原型阶段供管理后台原型页与学员端联调。
"""
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.database import get_db
from app.services import practice_service

router = APIRouter(prefix="/practice")


# ── Schemas ────────────────────────────────────────────
class AnswerItem(BaseModel):
    question_id: str
    user_answer: str


class SubmitBody(BaseModel):
    answers: list[AnswerItem]


# ── Routes ─────────────────────────────────────────────
@router.get("/skills")
def list_skills():
    """列出 6 种资料分析技能。"""
    return ApiResponse.ok(practice_service.list_skills())


@router.get("/daily")
def get_daily(
    skill: str = Query(..., description="技能: base_period/growth_rate/proportion/average/multiple/mixed_growth"),
    date: str = Query(..., description="日期 YYYY-MM-DD"),
):
    """获取今日练习包：方法示例 + 渐进训练 + 材料题组。"""
    try:
        package = practice_service.generate_daily_package(skill, date)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=400)
    return ApiResponse.ok(package)


@router.post("/{daily_id}/submit")
def submit(
    daily_id: str,
    body: SubmitBody,
    db: Session = Depends(get_db),
    x_user_id: str = Header(default="anonymous", alias="X-User-Id"),
):
    """提交答案，返回逐题对错判定与错因映射。作答持久化到 practice_answers。"""
    try:
        result = practice_service.submit_answers(
            daily_id,
            [{"question_id": a.question_id, "user_answer": a.user_answer} for a in body.answers],
            db=db,
            user_id=x_user_id,
            source="real",
        )
    except ValueError as e:
        return ApiResponse.fail(str(e), code=404)
    return ApiResponse.ok(result)


@router.get("/{daily_id}/review")
def review(daily_id: str):
    """获取错因复习卡：错误路径汇总 + 错题列表。"""
    try:
        result = practice_service.get_review_card(daily_id)
    except ValueError as e:
        return ApiResponse.fail(str(e), code=404)
    return ApiResponse.ok(result)
