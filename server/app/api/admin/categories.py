from app.api.admin._deps import *  # noqa: F401,F403

router = APIRouter()
# ---- 分类管理 ----
@router.get("/categories")
def list_categories_admin(
    _admin=Depends(require_permission("article:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(build_category_tree(db, active_only=False))


@router.post("/categories")
def create_category(
    body: CategoryCreate,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    cat = Category(
        id=gen_id("cat"),
        name=body.name,
        parent_id=body.parent_id,
        sort_order=body.sort_order,
    )
    db.add(cat)
    db.commit()
    return ApiResponse.ok({
        "id": cat.id,
        "name": cat.name,
        "parentId": cat.parent_id,
        "sortOrder": cat.sort_order,
        "children": [],
    })


@router.put("/categories/{category_id}")
def update_category(
    category_id: str,
    body: CategoryUpdate,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    cat = db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "分类不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(cat, k, v)
    db.commit()
    return ApiResponse.ok({
        "id": cat.id,
        "name": cat.name,
        "parentId": cat.parent_id,
        "sortOrder": cat.sort_order,
    })


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    _admin=Depends(require_permission("article:write")),
    db: Session = Depends(get_db),
):
    cat = db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "分类不存在")
    child = db.query(Category).filter(Category.parent_id == category_id).first()
    if child:
        return ApiResponse.fail("请先删除子分类", code=400)
    used = db.query(Article).filter(Article.category_id == category_id).first()
    if used:
        return ApiResponse.fail("分类已被文章使用", code=400)
    db.delete(cat)
    db.commit()
    return ApiResponse.ok(None, message="已删除")


