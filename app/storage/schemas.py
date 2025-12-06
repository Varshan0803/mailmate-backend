# app/storage/schemas.py
from pydantic import BaseModel

class UploadResponse(BaseModel):
    filename: str
    url: str
    size: int
