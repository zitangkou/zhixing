"""时政学习已发布入口。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.database import get_db
from app.product import ProductContext, get_product_context
from app.services.theory_learning_entry_service import list_public_entries

router = APIRouter(prefix="/learning/entries")


def require_theory_product(product: ProductContext = Depends(get_product_context)) -> None:
    if product.key != "theory":
        raise HTTPException(404, "学习入口不存在")


@router.get("", dependencies=[Depends(require_theory_product)])
def learning_entries(db: Session = Depends(get_db)):
    return ApiResponse.ok(list_public_entries(db))
