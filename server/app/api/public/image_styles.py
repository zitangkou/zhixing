"""Published image style presets for products such as AI 百宝箱."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.database import get_db
from app.product import ProductContext, get_product_context
from app.services.image_style_service import list_public_image_styles

router = APIRouter()


@router.get("/image-styles")
def public_image_styles(
    product: ProductContext = Depends(get_product_context),
    db: Session = Depends(get_db),
):
    items = list_public_image_styles(db, product.key)
    public_items = [
        {
            "id": item["id"],
            "slug": item["slug"],
            "name": item["name"],
            "category": item["category"],
            "description": item["description"],
            "version": item["version"],
            "sortOrder": item["sortOrder"],
        }
        for item in items
    ]
    return ApiResponse.ok({"productKey": product.key, "items": public_items})
