"""Anonymous practice endpoints, deliberately without user-data mutations."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.response import ApiResponse
from app.product import ProductContext, get_product_context
from app.services.article_learning_service import get_learning_bundle, check_learning_answer

router = APIRouter(prefix="/learning/articles")


class LearningAnswer(BaseModel):
    revision: str = Field(min_length=64, max_length=64)
    questionId: str = Field(min_length=1, max_length=64)
    answer: str | list[str] = Field(max_length=10000)


def require_theory_product(product: ProductContext = Depends(get_product_context)) -> None:
    if product.key != "theory":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="学习内容不存在")


@router.get("/{article_id}", dependencies=[Depends(require_theory_product)])
def learning_bundle(article_id: str, db: Session = Depends(get_db)):
    return ApiResponse.ok(get_learning_bundle(db, article_id))


@router.post("/{article_id}/check", dependencies=[Depends(require_theory_product)])
def learning_check(article_id: str, body: LearningAnswer, db: Session = Depends(get_db)):
    return ApiResponse.ok(check_learning_answer(
        db, article_id, body.revision, body.questionId, body.answer,
    ))
