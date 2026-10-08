from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.admin._deps import get_db, require_permission
from app.core.response import ApiResponse
from app.services import library_document_service as documents

router = APIRouter()


class LibraryDocumentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    category: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=2000)
    isPublished: bool | None = None


@router.get("/library-documents")
def admin_list_library_documents(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin=Depends(require_permission("knowledge:read")),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(documents.list_admin_documents(db, limit=limit, offset=offset))


@router.post("/library-documents")
async def admin_upload_library_document(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    category: str = Form(default="未分类"),
    description: str = Form(default=""),
    admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    raw = await file.read(documents.MAX_UPLOAD_BYTES + 1)
    if len(raw) > documents.MAX_UPLOAD_BYTES:
        return ApiResponse.fail("单个文件不能超过 20 MB", code=413)
    try:
        result = documents.create_document(
            db,
            filename=file.filename or "",
            raw=raw,
            admin_id=admin.id,
            title=title,
            category=category,
            description=description,
        )
    except ValueError as exc:
        return ApiResponse.fail(str(exc), code=400)
    return ApiResponse.ok(result, message="文档已上传，请确认后发布")


@router.patch("/library-documents/{document_id}")
def admin_update_library_document(
    document_id: str,
    body: LibraryDocumentPatch,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    values = body.model_dump(exclude_unset=True, exclude_none=True)
    result = documents.update_admin_document(db, document_id, values)
    if not result:
        return ApiResponse.fail("文档不存在", code=404)
    return ApiResponse.ok(result)


@router.delete("/library-documents/{document_id}")
def admin_delete_library_document(
    document_id: str,
    _admin=Depends(require_permission("knowledge:write")),
    db: Session = Depends(get_db),
):
    if not documents.delete_admin_document(db, document_id):
        return ApiResponse.fail("文档不存在", code=404)
    return ApiResponse.ok({"id": document_id, "deleted": True})
