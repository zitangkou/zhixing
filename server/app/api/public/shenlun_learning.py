"""申论学习公共示范接口。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.database import get_db
from app.product import ProductContext, get_product_context
from app.services.shenlun_learning_service import get_learning_article, list_learning_articles

router = APIRouter(prefix="/shenlun/learning")


def require_shenlun_product(product: ProductContext = Depends(get_product_context)) -> None:
    if product.key != "shenlun":
        raise HTTPException(status_code=404, detail="学习内容不存在")


@router.get("/articles", dependencies=[Depends(require_shenlun_product)])
def learning_articles(db: Session = Depends(get_db)):
    return ApiResponse.ok(list_learning_articles(db))


@router.get("/articles/{article_id}", dependencies=[Depends(require_shenlun_product)])
def learning_article(article_id: str, db: Session = Depends(get_db)):
    return ApiResponse.ok(get_learning_article(db, article_id))
