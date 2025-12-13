# app/storage/schemas.py
from pydantic import BaseModel
from typing import List, Optional

class UploadResponse(BaseModel):
    filename: str
    url: str
    size: int

class BatchUploadResult(BaseModel):
    success: bool
    url: Optional[str] = None
    filename: Optional[str] = None
    original_filename: str
    size: Optional[int] = None
    error: Optional[str] = None

class BatchUploadResponse(BaseModel):
    results: List[BatchUploadResult]
