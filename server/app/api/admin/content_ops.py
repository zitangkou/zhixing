from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_permission
from app.core.response import ApiResponse
from app.database import get_db
from app.models import ContentOperationTemplate, ContentPublishPackage
from app.schemas import ContentPackageGenerateFromArticle, ContentPublishPackageCreate, ContentPublishPackageUpdate, ContentPublishStatusBody
from app.services.content_ops_service import (
    content_ops_overview,
    content_reference_library,
    content_review_config,
    create_package,
    export_package,
    generate_package_from_article,
    get_package_preflight,
    list_publishable_targets,
    package_out,
    template_out,
    transition_package,
    update_package,
)

router = APIRouter()


@router.get("/content-ops/review-config")
def review_config(_admin=Depends(require_permission("content_ops:read"))):
    return ApiResponse.ok(content_review_config())


@router.get("/content-ops/reference-library")
def reference_library(_admin=Depends(require_permission("content_ops:read"))):
    try: return ApiResponse.ok(content_reference_library())
    except ValueError as exc: return ApiResponse.fail(str(exc), code=500)


@router.get("/content-ops/overview")
def overview(days: int = 7, _admin=Depends(require_permission("content_ops:read")), db: Session = Depends(get_db)):
    safe_days = min(max(days, 1), 31)
    return ApiResponse.ok(content_ops_overview(db, safe_days))


@router.get("/content-ops/templates")
def templates(productKey: str | None = None, _admin=Depends(require_permission("content_ops:read")), db: Session = Depends(get_db)):
    query = db.query(ContentOperationTemplate).filter(ContentOperationTemplate.status == "enabled")
    if productKey:
        query = query.filter(ContentOperationTemplate.product_key.in_([productKey, "general"]))
    rows = query.order_by(ContentOperationTemplate.sort_order, ContentOperationTemplate.created_at).all()
    return ApiResponse.ok([template_out(row) for row in rows])


@router.get("/content-ops/entry-targets")
def entry_targets(productKey: str, _admin=Depends(require_permission("content_ops:read")), db: Session = Depends(get_db)):
    try: return ApiResponse.ok(list_publishable_targets(db, productKey))
    except ValueError as exc: return ApiResponse.fail(str(exc), code=400)


@router.get("/content-ops/packages")
def packages(status: str | None = None, productKey: str | None = None, _admin=Depends(require_permission("content_ops:read")), db: Session = Depends(get_db)):
    query = db.query(ContentPublishPackage)
    if status: query = query.filter(ContentPublishPackage.status == status)
    if productKey: query = query.filter(ContentPublishPackage.product_key == productKey)
    rows = query.order_by(ContentPublishPackage.created_at.desc()).limit(200).all()
    return ApiResponse.ok([package_out(row) for row in rows])


@router.post("/content-ops/packages")
def package_create(body: ContentPublishPackageCreate, _admin=Depends(require_permission("content_ops:write")), db: Session = Depends(get_db)):
    try: return ApiResponse.ok(create_package(db, body))
    except ValueError as exc: return ApiResponse.fail(str(exc), code=400)


@router.post("/content-ops/packages/generate-from-article")
def package_generate_from_article(body: ContentPackageGenerateFromArticle, _admin=Depends(require_permission("content_ops:write")), db: Session = Depends(get_db)):
    try: return ApiResponse.ok(generate_package_from_article(db, body))
    except ValueError as exc: return ApiResponse.fail(str(exc), code=400)


@router.post("/content-ops/packages/{package_id}/status")
def package_status(package_id: str, body: ContentPublishStatusBody, _admin=Depends(require_permission("content_ops:write")), db: Session = Depends(get_db)):
    try: return ApiResponse.ok(transition_package(db, package_id, body.status, body.reviewNote, body.checklist, _admin))
    except ValueError as exc: return ApiResponse.fail(str(exc), code=400)


@router.put("/content-ops/packages/{package_id}")
def package_update(package_id: str, body: ContentPublishPackageUpdate, _admin=Depends(require_permission("content_ops:write")), db: Session = Depends(get_db)):
    try: return ApiResponse.ok(update_package(db, package_id, body))
    except ValueError as exc: return ApiResponse.fail(str(exc), code=400)


@router.get("/content-ops/packages/{package_id}/export")
def package_export(package_id: str, _admin=Depends(require_permission("content_ops:read")), db: Session = Depends(get_db)):
    try: return ApiResponse.ok(export_package(db, package_id))
    except ValueError as exc: return ApiResponse.fail(str(exc), code=400)


@router.get("/content-ops/packages/{package_id}/preflight")
def package_preflight(package_id: str, _admin=Depends(require_permission("content_ops:read")), db: Session = Depends(get_db)):
    try: return ApiResponse.ok(get_package_preflight(db, package_id))
    except ValueError as exc: return ApiResponse.fail(str(exc), code=400)
