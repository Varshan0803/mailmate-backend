from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class Campaign(BaseModel):
    title: str
    subject: str
    sender_name: str
    reply_to: EmailStr
    audience_id: str
    content: str
    schedule_time: Optional[datetime] = None
    status: str = "Draft"  # Draft, Pending, Sent, Failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # User ID
