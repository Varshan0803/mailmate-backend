from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from bson import ObjectId
import datetime

class UserInDB(BaseModel):
    id: Optional[str] = None
    name: str
    email: EmailStr
    password_hash: str
    role: str = "marketing"
    created_at: datetime.datetime = datetime.datetime.utcnow()
