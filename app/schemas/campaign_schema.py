from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class CampaignCreate(BaseModel):
    title: str
    subject: str
    sender_name: str
    reply_to: EmailStr
    audience_id: str
    content: str
    schedule_time: Optional[datetime] = None
    status: str = "Draft"

class CampaignOut(CampaignCreate):
    id: str
    created_at: datetime
    created_by: str
