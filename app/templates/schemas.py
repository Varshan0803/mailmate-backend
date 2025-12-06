# app/templates/schemas.py
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1)
    html: str
    images: Optional[List[str]] = []

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    html: Optional[str] = None
    images: Optional[List[str]] = None

class TemplateOut(BaseModel):
    id: str
    name: str
    html: str
    images: List[str] = []
    created_by: str
    created_at: datetime
