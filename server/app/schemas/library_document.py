from datetime import datetime

from pydantic import BaseModel


class LibraryDocumentOut(BaseModel):
    id: str
    fileName: str
    title: str
    category: str
    description: str
    format: str
    contentType: str
    fileSize: int
    sha256: str
    extractionStatus: str
    extractionError: str
    isPublished: bool
    createdAt: datetime


class LibraryDocumentDetailOut(LibraryDocumentOut):
    extractedText: str
