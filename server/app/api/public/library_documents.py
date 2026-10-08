from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_app_user
from app.core.response import ApiResponse
from app.database import get_db
from app.models import AppUser
from app.schemas import LibraryDocumentDetailOut, LibraryDocumentOut
from app.services import library_document_service as documents

router = APIRouter()


@router.post("/library/documents")
async def upload_library_document(
    file: UploadFile = File(...),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    raw = await file.read(documents.MAX_UPLOAD_BYTES + 1)
    if len(raw) > documents.MAX_UPLOAD_BYTES:
        return ApiResponse.fail("单个文件不能超过 20 MB", code=413)
    try:
        result = documents.create_document(db, owner_id=user.id, filename=file.filename or "", raw=raw)
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(LibraryDocumentOut.model_validate(result), message="文档已上传并解析")


@router.get("/library/documents")
def list_library_documents(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    rows = documents.list_documents(db, user.id, limit=limit, offset=offset)
    return ApiResponse.ok([LibraryDocumentOut.model_validate(row) for row in rows])


@router.get("/library/catalog")
def list_library_catalog(
    q: str = Query(default="", max_length=80),
    category: str = Query(default="", max_length=64),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    del user  # Authentication is required; only published entries are exposed by the service.
    rows = documents.list_catalog_documents(db, q, category, limit=limit, offset=offset)
    return ApiResponse.ok([LibraryDocumentOut.model_validate(row) for row in rows])


@router.get("/library/catalog/{document_id}")
def get_library_catalog_document(
    document_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    del user
    document = documents.get_catalog_document(db, document_id)
    if not document:
        return ApiResponse.fail("文档不存在或尚未发布", code=404)
    return ApiResponse.ok(LibraryDocumentDetailOut.model_validate(document))


@router.get("/library/documents/{document_id}")
def get_library_document(
    document_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    document = documents.get_document(db, user.id, document_id)
    if not document:
        return ApiResponse.fail("文档不存在", code=404)
    return ApiResponse.ok(LibraryDocumentDetailOut.model_validate(document))


@router.delete("/library/documents/{document_id}")
def delete_library_document(
    document_id: str,
    user: AppUser = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if not documents.delete_document(db, user.id, document_id):
        return ApiResponse.fail("文档不存在", code=404)
    return ApiResponse.ok({"id": document_id, "deleted": True})
