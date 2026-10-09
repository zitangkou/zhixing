"""Admin CRUD for reusable AI image style configurations."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.schemas.image_style import ImageStyleConfigOut, ImageStyleMarkdownImportBody, ImageStylePreset
from app.services.image_style_service import (
    get_image_style_config,
    image_style_conflict,
    parse_image_style_markdown,
    save_image_style_config,
)

router = APIRouter()


@router.get("/image-styles")
def admin_list_image_styles(_admin=Depends(require_permission("setting:read")), db: Session = Depends(get_db)):
    return ApiResponse.ok(ImageStyleConfigOut(**get_image_style_config(db)).model_dump())


@router.post("/image-styles")
def admin_create_image_style(
    body: ImageStylePreset,
    _admin=Depends(require_permission("setting:write")),
    db: Session = Depends(get_db),
):
    items = get_image_style_config(db)["items"]
    if any(item["id"] == body.id or item["slug"] == body.slug for item in items):
        return ApiResponse.fail("风格 ID 或标识已存在", code=409)
    items.append(body.model_dump())
    return ApiResponse.ok(ImageStyleConfigOut(**save_image_style_config(db, items)).model_dump())


@router.put("/image-styles/{style_id}")
def admin_update_image_style(
    style_id: str,
    body: ImageStylePreset,
    _admin=Depends(require_permission("setting:write")),
    db: Session = Depends(get_db),
):
    if body.id != style_id:
        return ApiResponse.fail("风格 ID 不可在编辑时修改", code=400)
    items = get_image_style_config(db)["items"]
    if not any(item["id"] == style_id for item in items):
        return ApiResponse.fail("风格不存在", code=404)
    if any(item["id"] != style_id and item["slug"] == body.slug for item in items):
        return ApiResponse.fail("风格标识已存在", code=409)
    items = [body.model_dump() if item["id"] == style_id else item for item in items]
    return ApiResponse.ok(ImageStyleConfigOut(**save_image_style_config(db, items)).model_dump())


@router.delete("/image-styles/{style_id}")
def admin_delete_image_style(
    style_id: str,
    _admin=Depends(require_permission("setting:write")),
    db: Session = Depends(get_db),
):
    items = get_image_style_config(db)["items"]
    remaining = [item for item in items if item["id"] != style_id]
    if len(remaining) == len(items):
        return ApiResponse.fail("风格不存在", code=404)
    return ApiResponse.ok(ImageStyleConfigOut(**save_image_style_config(db, remaining)).model_dump(), message="已删除")


@router.post("/image-styles/import/preview")
def admin_preview_image_style_import(
    body: ImageStyleMarkdownImportBody,
    _admin=Depends(require_permission("setting:write")),
    db: Session = Depends(get_db),
):
    try:
        style = parse_image_style_markdown(body.markdown)
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)
    conflict = image_style_conflict(get_image_style_config(db)["items"], style)
    return ApiResponse.ok({"style": style, "canImport": not conflict, "conflict": conflict})


@router.post("/image-styles/import")
def admin_import_image_style(
    body: ImageStyleMarkdownImportBody,
    _admin=Depends(require_permission("setting:write")),
    db: Session = Depends(get_db),
):
    try:
        style = parse_image_style_markdown(body.markdown)
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)
    items = get_image_style_config(db)["items"]
    conflict = image_style_conflict(items, style)
    if conflict:
        return ApiResponse.fail(conflict, code=409)
    items.append(style)
    config = save_image_style_config(db, items)
    return ApiResponse.ok({"style": style, "config": config}, message="风格已导入")
