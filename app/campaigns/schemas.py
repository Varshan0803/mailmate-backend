# app/campaigns/schemas.py
from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, EmailStr


class CampaignCreate(BaseModel):
    name: str
    subject: str
    template_id: Optional[str] = None
    segment: str
    html_content: Optional[str] = None
    sender_name: Optional[str] = None
    reply_to: Optional[str] = None
    status: Optional[str] = "draft"
    send_at: Optional[datetime] = None


class CampaignOut(BaseModel):
    id: str
    name: str
    subject: str
    template_id: Optional[str] = None
    segment: str
    html_content: Optional[str] = ""
    status: str
    created_by: str
    created_at: datetime
    send_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None


class CampaignListItem(BaseModel):
    id: str
    name: str
    subject: str
    segment: str
    status: str
    created_at: datetime
    send_at: Optional[datetime] = None


class CampaignScheduleRequest(BaseModel):
    send_at: datetime


class CampaignSendContact(BaseModel):
    email: EmailStr
    name: str
    subject: str
    html: str
    unsubscribe_link: str


class CampaignSendPayload(BaseModel):
    campaign_id: str
    campaign_name: str
    subject: str
    segment: str
    total_recipients: int
    messages: List[CampaignSendContact]


class JobStatus(BaseModel):
    campaign_id: str
    status: str
    run_at: datetime
    total_recipients: int
    task_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
