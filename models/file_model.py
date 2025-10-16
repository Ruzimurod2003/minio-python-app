from typing import Optional
from pydantic import BaseModel


class FileMetadata(BaseModel):
    id: int
    file_name: str
    minio_object_key: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    created_at: str


class FileUploadResponse(BaseModel):
    id: int
    file_name: str
    minio_object_key: str
    message: str
