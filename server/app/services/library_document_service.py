"""私有知识库文档的格式校验、解析与存储。"""
from __future__ import annotations

import hashlib
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from sqlalchemy.orm import Session

from app.models import LibraryDocument
from app.models.base import gen_id
from app.upload_paths import DATA_DIR

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_EXTRACTED_CHARS = 1_000_000
MAX_DOCX_UNPACKED_BYTES = 100 * 1024 * 1024
MAX_PDF_PAGES = 500
PRIVATE_DOCS_DIR = DATA_DIR / "private-docs"
ALLOWED_FORMATS = {"md", "txt", "pdf", "docx"}
FORMAT_CONTENT_TYPES = {
    "md": "text/markdown",
    "txt": "text/plain",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _safe_name(filename: str) -> str:
    normalized = (filename or "").replace("\\", "/")
    name = Path(normalized).name
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip(" .")
    if not name or name in {".", ".."}:
        raise ValueError("文件名无效")
    if len(name) > 512:
        name = name[-512:]
    return name


def _extract_docx(raw: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if sum(item.file_size for item in entries) > MAX_DOCX_UNPACKED_BYTES:
                raise ValueError("DOCX 解压后内容超过限制")
            if "word/document.xml" not in archive.namelist():
                raise ValueError("DOCX 文档结构无效")
            xml = archive.read("word/document.xml")
    except zipfile.BadZipFile as exc:
        raise ValueError("DOCX 文件结构无效") from exc

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise ValueError("DOCX 文档内容无效") from exc
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_pdf(raw: bytes) -> tuple[str, str]:
    if not raw.startswith(b"%PDF-"):
        raise ValueError("PDF 文件头无效")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF 解析组件未安装，请联系管理员") from exc
    try:
        reader = PdfReader(io.BytesIO(raw), strict=False)
        if reader.is_encrypted:
            raise ValueError("暂不支持加密 PDF")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError(f"PDF 页数不能超过 {MAX_PDF_PAGES} 页")
        text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("PDF 解析失败，请确认文件未损坏") from exc
    if not text.strip():
        return "", "needs_ocr"
    return text, "ready"


def _parse_document(file_format: str, raw: bytes) -> tuple[str, str]:
    if file_format in {"md", "txt"}:
        if b"\x00" in raw:
            raise ValueError("文本文件包含无效二进制内容")
        try:
            return raw.decode("utf-8-sig"), "ready"
        except UnicodeDecodeError as exc:
            raise ValueError("文本文件目前只支持 UTF-8 编码") from exc
    if file_format == "docx":
        return _extract_docx(raw), "ready"
    if file_format == "pdf":
        return _extract_pdf(raw)
    raise ValueError("暂不支持该文件格式")


def _serialize(document: LibraryDocument, include_text: bool = False) -> dict:
    result = {
        "id": document.id,
        "fileName": document.file_name,
        "title": document.title,
        "category": document.category,
        "description": document.description,
        "format": document.file_format,
        "contentType": document.content_type,
        "fileSize": document.file_size,
        "sha256": document.sha256,
        "extractionStatus": document.extraction_status,
        "extractionError": document.extraction_error,
        "isPublished": document.is_published,
        "createdAt": document.created_at,
    }
    if include_text:
        result["extractedText"] = document.extracted_text
    return result


def create_document(
    db: Session,
    filename: str,
    raw: bytes,
    *,
    owner_id: str | None = None,
    admin_id: int | None = None,
    title: str = "",
    category: str = "未分类",
    description: str = "",
) -> dict:
    if (owner_id is None) == (admin_id is None):
        raise ValueError("文档必须且只能属于一个学员或管理员上传者")
    if not raw:
        raise ValueError("文件内容为空")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("单个文件不能超过 20 MB")
    safe_name = _safe_name(filename)
    suffix = Path(safe_name).suffix.lower().lstrip(".")
    if suffix not in ALLOWED_FORMATS:
        raise ValueError("仅支持 MD、TXT、PDF、DOCX 文件")

    extracted_text, extraction_status = _parse_document(suffix, raw)
    if len(extracted_text) > MAX_EXTRACTED_CHARS:
        extracted_text = extracted_text[:MAX_EXTRACTED_CHARS]
        extraction_status = "truncated"

    document_id = gen_id("ld")
    owner_key = f"user:{owner_id}" if owner_id is not None else f"admin:{admin_id}"
    owner_dir = hashlib.sha256(owner_key.encode("utf-8")).hexdigest()
    user_dir = PRIVATE_DOCS_DIR / owner_dir
    user_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    user_dir.chmod(0o700)
    storage_path = user_dir / f"{document_id}.{suffix}"
    storage_path.write_bytes(raw)
    storage_path.chmod(0o600)
    document = LibraryDocument(
        id=document_id,
        owner_id=owner_id,
        uploaded_by_admin_id=admin_id,
        file_name=safe_name,
        title=(title or Path(safe_name).stem)[:256],
        category=(category or "未分类")[:64],
        description=description[:2000],
        file_format=suffix,
        content_type=FORMAT_CONTENT_TYPES[suffix],
        file_size=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(),
        storage_path=str(storage_path),
        extracted_text=extracted_text,
        extraction_status=extraction_status,
        is_published=False,
    )
    try:
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise
    return _serialize(document)


def list_documents(db: Session, owner_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    rows = (
        db.query(LibraryDocument)
        .filter(LibraryDocument.owner_id == owner_id)
        .order_by(LibraryDocument.created_at.desc(), LibraryDocument.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_serialize(row) for row in rows]


def get_document(db: Session, owner_id: str, document_id: str) -> dict | None:
    document = (
        db.query(LibraryDocument)
        .filter(LibraryDocument.id == document_id, LibraryDocument.owner_id == owner_id)
        .first()
    )
    return _serialize(document, include_text=True) if document else None


def list_catalog_documents(
    db: Session, query: str = "", category: str = "", limit: int = 50, offset: int = 0
) -> list[dict]:
    from sqlalchemy import or_

    stmt = db.query(LibraryDocument).filter(
        LibraryDocument.owner_id.is_(None), LibraryDocument.is_published.is_(True)
    )
    if category:
        stmt = stmt.filter(LibraryDocument.category == category)
    if query.strip():
        pattern = f"%{query.strip()[:80]}%"
        stmt = stmt.filter(
            or_(
                LibraryDocument.title.ilike(pattern),
                LibraryDocument.description.ilike(pattern),
                LibraryDocument.file_name.ilike(pattern),
            )
        )
    rows = stmt.order_by(LibraryDocument.created_at.desc(), LibraryDocument.id.desc()).offset(offset).limit(limit).all()
    return [_serialize(row) for row in rows]


def get_catalog_document(db: Session, document_id: str) -> dict | None:
    document = (
        db.query(LibraryDocument)
        .filter(
            LibraryDocument.id == document_id,
            LibraryDocument.owner_id.is_(None),
            LibraryDocument.is_published.is_(True),
        )
        .first()
    )
    return _serialize(document, include_text=True) if document else None


def list_admin_documents(db: Session, limit: int = 100, offset: int = 0) -> list[dict]:
    rows = (
        db.query(LibraryDocument)
        .filter(LibraryDocument.uploaded_by_admin_id.is_not(None))
        .order_by(LibraryDocument.created_at.desc(), LibraryDocument.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_serialize(row, include_text=False) for row in rows]


def update_admin_document(db: Session, document_id: str, values: dict) -> dict | None:
    document = (
        db.query(LibraryDocument)
        .filter(LibraryDocument.id == document_id, LibraryDocument.uploaded_by_admin_id.is_not(None))
        .first()
    )
    if not document:
        return None
    for field in ("title", "category", "description", "is_published"):
        if field in values:
            setattr(document, field, values[field])
    db.commit()
    db.refresh(document)
    return _serialize(document)


def delete_admin_document(db: Session, document_id: str) -> bool:
    document = (
        db.query(LibraryDocument)
        .filter(LibraryDocument.id == document_id, LibraryDocument.uploaded_by_admin_id.is_not(None))
        .first()
    )
    if not document:
        return False
    storage_path = Path(document.storage_path)
    db.delete(document)
    db.commit()
    try:
        storage_path.unlink(missing_ok=True)
    except OSError:
        pass
    return True


def delete_document(db: Session, owner_id: str, document_id: str) -> bool:
    document = (
        db.query(LibraryDocument)
        .filter(LibraryDocument.id == document_id, LibraryDocument.owner_id == owner_id)
        .first()
    )
    if not document:
        return False
    storage_path = Path(document.storage_path)
    db.delete(document)
    db.commit()
    try:
        storage_path.unlink(missing_ok=True)
    except OSError:
        # DB metadata is removed; a cleanup job can reclaim any leftover private file.
        pass
    return True
