# app/campaigns/routes.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from datetime import datetime
from app.campaigns.schemas import (
    CampaignCreate,
    CampaignOut,
    CampaignListItem,
    CampaignSendPayload,
    CampaignScheduleRequest,
    JobStatus,
)
from app.campaigns import services
from app.deps import get_current_user, require_role
from app.campaigns.tasks import process_scheduled_job

# utilities
from app.templates import services as template_services
from app.utils.absolute import to_absolute_urls



router = APIRouter(prefix="/campaigns", tags=["campaigns"])


# ------------------------------------------------
# CREATE CAMPAIGN
# ------------------------------------------------
@router.post("/", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    user=Depends(require_role("marketing")),
):
    data = payload.model_dump()
    data["created_by"] = str(user["_id"])

    doc = await services.create_campaign(data)

    # Trigger background sending if status is Pending (Send Now)
    if doc["status"] == "Pending":
        from app.campaigns.tasks import send_campaign_task
        send_campaign_task.delay(str(doc["_id"]))

    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "subject": doc["subject"],
        "template_id": doc["template_id"],
        "segment": doc["segment"],
        "html_content": doc.get("html_content", ""),
        "status": doc["status"],
        "created_by": doc["created_by"],
        "created_at": doc["created_at"],
        "send_at": doc.get("send_at"),
        "scheduled_at": doc.get("scheduled_at"),
    }


# ------------------------------------------------
# LIST CAMPAIGNS
# ------------------------------------------------
@router.get("/", response_model=List[CampaignListItem])
async def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user=Depends(get_current_user),
):
    docs = await services.list_campaigns(skip=skip, limit=limit)
    out: List[CampaignListItem] = []
    for d in docs:
        out.append(
            {
                "id": d["id"],
                "name": d.get("name", "Untitled Campaign"),
                "subject": d.get("subject", "No Subject"),
                "segment": d.get("segment", "Unknown Segment"),
                "status": d.get("status", "draft"),
                "created_at": d.get("created_at", datetime.utcnow()),
                "send_at": d.get("send_at"),
            }
        )
    return out


# ------------------------------------------------
# LIST DUE (TEAM 2)
# ------------------------------------------------
@router.get("/due", response_model=List[CampaignListItem])
async def get_due_campaigns(user=Depends(require_role("marketing"))):
    docs = await services.list_due_campaigns()
    out: List[CampaignListItem] = []
    for d in docs:
        out.append(
            {
                "id": d["id"],
                "name": d.get("name", "Untitled Campaign"),
                "subject": d.get("subject", "No Subject"),
                "segment": d.get("segment", "Unknown Segment"),
                "status": d.get("status", "draft"),
                "created_at": d.get("created_at", datetime.utcnow()),
                "send_at": d.get("send_at"),
            }
        )
    return out


# ------------------------------------------------
# GET CAMPAIGN
# ------------------------------------------------
@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: str, user=Depends(get_current_user)):
    doc = await services.get_campaign(campaign_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Campaign not found")
    # Fallback to template content if html_content is empty
    html_content = to_absolute_urls(doc.get("html_content", ""))
    if not html_content and doc.get("template_id"):
        template_doc = await template_services.get_template(doc["template_id"])
        if template_doc:
            html_content = template_doc.get("html", "")

    return {
        "id": doc["id"],
        "name": doc["name"],
        "subject": doc["subject"],
        "template_id": doc["template_id"],
        "segment": doc["segment"],
        "html_content": html_content,
        "status": doc["status"],
        "created_by": doc["created_by"],
        "created_at": doc["created_at"],
        "send_at": doc.get("send_at"),
        "scheduled_at": doc.get("scheduled_at"),
    }


# ------------------------------------------------
# PREVIEW (FALLBACK TO TEMPLATE + ABSOLUTE URLs)
# ------------------------------------------------
@router.get("/{campaign_id}/preview")
async def preview_campaign(campaign_id: str, user=Depends(get_current_user)):
    """
    Return final-rendered HTML for preview.
    If campaign.html_content is empty, fallback to the linked template's html.
    Converts storage URLs to absolute using to_absolute_urls().
    """
    campaign = await services.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Prefer campaign html_content if present, otherwise fetch template html
    html_raw = campaign.get("html_content") or ""
    if not html_raw:
        template_id = campaign.get("template_id")
        if template_id:
            template_doc = await template_services.get_template(template_id)
            if template_doc:
                html_raw = template_doc.get("html", "") or ""

    html_abs = to_absolute_urls(html_raw or "")
    return {"html": html_abs}


# ------------------------------------------------
# JOB STATUS
# ------------------------------------------------
@router.get("/{campaign_id}/status", response_model=JobStatus)
async def get_campaign_status(
    campaign_id: str,
    user=Depends(require_role("marketing")),
):
    job = await services.get_job_status_for_campaign(campaign_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found for this campaign")
    return job


# ------------------------------------------------
# DELETE CAMPAIGN
# ------------------------------------------------
@router.delete("/{campaign_id}", status_code=status.HTTP_200_OK)
async def delete_campaign(campaign_id: str, user=Depends(require_role("marketing"))):
    ok = await services.delete_campaign(campaign_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"ok": True}


# ------------------------------------------------
# SCHEDULE CAMPAIGN (triggers Celery)
# ------------------------------------------------
@router.post("/{campaign_id}/schedule", response_model=CampaignOut)
async def schedule_campaign_endpoint(
    campaign_id: str,
    payload: CampaignScheduleRequest,
    user=Depends(require_role("marketing")),
):
    result = await services.schedule_campaign(campaign_id, payload.send_at)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    print("DEBUG RESULT =", result)
    # Validate correct return format
    if not isinstance(result, (list, tuple)) or len(result) != 2:
        print("❌ Unexpected return from schedule_campaign:", result)
        raise HTTPException(status_code=500, detail="Internal scheduling error")

    campaign, job_id = result


    # 🔹 enqueue Celery task (background processing)
    # 🔹 enqueue Celery task (background processing)
    # Use apply_async with 'eta' so Celery holds the task until send_at
    # 🔹 enqueue Celery task (background processing)
    # Use apply_async with 'eta' so Celery holds the task until send_at
    process_scheduled_job.apply_async(args=[str(job_id)], eta=payload.send_at)

    return {
        "id": campaign["id"],
        "name": campaign["name"],
        "subject": campaign["subject"],
        "template_id": campaign["template_id"],
        "segment": campaign["segment"],
        "html_content": campaign.get("html_content", ""),
        "status": campaign["status"],
        "created_by": campaign["created_by"],
        "created_at": campaign["created_at"],
        "send_at": campaign.get("send_at"),
        "scheduled_at": campaign.get("scheduled_at"),
    }

# ------------------------------------------------
# PREPARE SEND PAYLOAD (TEAM 2)
# ------------------------------------------------
@router.post("/{campaign_id}/prepare-send", response_model=CampaignSendPayload)
async def prepare_send(
    campaign_id: str,
    user=Depends(require_role("marketing")),
):
    """
    Backend Team 2 pulls the rendered (final) HTML for sending.
    """
    try:
        return await services.build_send_payload(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
# ------------------------------------------------
# TEST EMAIL
# ------------------------------------------------
class TestEmailRequest(BaseModel):
    email: EmailStr
    subject: str
    html_content: str

@router.post("/test-email", status_code=status.HTTP_200_OK)
async def send_test_email(
    payload: TestEmailRequest,
    user=Depends(require_role("marketing")),
):
    from app.services.send_bulk_service import BulkEmailService
    from app.config import settings

    from_email = settings.SENDER_EMAIL
    if not from_email:
        raise HTTPException(status_code=500, detail="SENDER_EMAIL not configured")

    service = BulkEmailService(
        sendgrid_api_key=settings.SENDGRID_API_KEY,
        email_logs_collection=None
    )

    # Construct a single-recipient payload
    send_payload = {
        "campaign_id": "TEST",
        "campaign_name": "Test Email",
        "subject": payload.subject,
        "segment": "Test",
        "messages": [{
            "email": payload.email,
            "name": "Test User",
            "subject": payload.subject,
            "html": payload.html_content,
            "unsubscribe_link": "#"
        }],
        "total_recipients": 1,
        "from_email": from_email,
        "reply_to": from_email,
    }

    try:
        result = await service.send_bulk(send_payload)
        await service.close()
        return {"ok": True, "result": result}
    except Exception as e:
        await service.close()
        raise HTTPException(status_code=500, detail=str(e))
