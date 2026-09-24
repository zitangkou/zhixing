from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.public._deps import ApiResponse, get_db
from app.services import xingce_quiz_service as xingce

router = APIRouter()


class XingceAnswerBody(BaseModel):
    questionId: str
    answer: str | list[str]


@router.get("/xingce/catalog")
def xingce_catalog(
    year: int | None = Query(None),
    paperType: str | None = Query(None),
    db: Session = Depends(get_db),
):
    paper_type = (paperType or "").strip() or None
    return ApiResponse.ok(xingce.catalog(db, year=year, paper_type=paper_type))


@router.get("/xingce/quiz")
def xingce_quiz(
    module: str = Query(..., min_length=1),
    year: int | None = Query(None),
    paperType: str | None = Query(None),
    count: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    paper_type = (paperType or "").strip() or None
    rows = xingce.pick_questions(db, module=module, year=year, paper_type=paper_type, count=count)
    if not rows:
        return ApiResponse.fail("该模块暂无可练真题", code=404)
    return ApiResponse.ok(rows)


@router.post("/xingce/answer")
def xingce_answer(body: XingceAnswerBody, db: Session = Depends(get_db)):
    result = xingce.grade_answer(db, body.questionId, body.answer)
    if result is None:
        return ApiResponse.fail("题目不存在", code=404)
    return ApiResponse.ok(result)
