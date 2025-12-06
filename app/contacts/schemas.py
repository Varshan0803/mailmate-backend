# app/contacts/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class ContactCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    segment: str = Field(..., min_length=1)

class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    segment: Optional[str] = None
    unsubscribed: Optional[bool] = None

class ContactOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    segment: Optional[str] = None
    unsubscribed: bool = False
    created_at: datetime
