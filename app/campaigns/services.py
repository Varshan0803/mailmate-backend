# app/campaigns/services.py
from typing import List, Optional, Dict, Any
from datetime import datetime

from bson import ObjectId

from app.db.client import db
from app.utils.absolute import to_absolute_urls, BACKEND_PUBLIC_URL

# Mongo collections
CAMPAIGNS = db.get_collection("campaigns")
CONTACTS = db.get_collection("contacts")
TEMPLATES = db.get_collection("templates")
JOBS = db.get_collection("scheduled_jobs")


# -------------------------
# Basic CRUD for campaigns
# -------------------------

async def create_campaign(data: Dict[str, Any]) -> Dict:
    data["status"] = data.get("status", "draft")
    data["created_at"] = data.get("created_at", datetime.utcnow())
    res = await CAMPAIGNS.insert_one(data)
    data["_id"] = res.inserted_id
    return data


async def get_campaign(campaign_id: str) -> Optional[Dict]:
    doc = await CAMPAIGNS.find_one({"_id": ObjectId(campaign_id)})
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    return doc


async def list_campaigns(skip: int = 0, limit: int = 50) -> List[Dict]:
    cursor = CAMPAIGNS.find().skip(skip).limit(limit).sort("created_at", -1)
    out: List[Dict[str, Any]] = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        out.append(doc)
    return out


async def update_campaign(campaign_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
    await CAMPAIGNS.update_one(
        {"_id": ObjectId(campaign_id)},
        {"$set": updates},
    )
    return await get_campaign(campaign_id)


async def delete_campaign(campaign_id: str) -> bool:
    res = await CAMPAIGNS.delete_one({"_id": ObjectId(campaign_id)})
    return res.deleted_count == 1


# -------------------------
# Scheduled Job helpers
# -------------------------

async def create_scheduled_job(
    campaign_id: str,
    run_at: datetime,
    payload: List[Dict[str, Any]],
    status: str = "pending",
    task_id: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
) -> Dict:
    """
    Create a scheduled job document for a campaign.

    Fields:
      - campaign_id: the campaign this job belongs to
      - run_at: when this job is supposed to be executed
      - status: pending | processing | done | error
      - task_id: reserved for background system id (optional)
      - payload: list of messages (one per contact)
      - result: optional summary (used later by Team 2)
    """
    doc: Dict[str, Any] = {
        "campaign_id": campaign_id,
        "run_at": run_at,
        "status": status,
        "task_id": task_id,
        "payload": payload,
        "result": result,
        "created_at": datetime.utcnow(),
    }
    res = await JOBS.insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def get_job_by_campaign_id(campaign_id: str) -> Optional[Dict]:
    """
    Fetch a single scheduled job for a given campaign_id.
    Assumes one job per campaign for now.
    """
    doc = await JOBS.find_one({"campaign_id": campaign_id})
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    return doc


async def get_job_status_for_campaign(campaign_id: str) -> Optional[Dict]:
    """
    Return a summarized view of the job status for a campaign:
      - status
      - run_at
      - total_recipients (len(payload))
      - task_id
      - result
      - created_at
    """
    job = await JOBS.find_one({"campaign_id": campaign_id})
    if not job:
        return None

    total_recipients = len(job.get("payload", []))

    return {
        "campaign_id": job["campaign_id"],
        "status": job.get("status", "pending"),
        "run_at": job["run_at"],
        "total_recipients": total_recipients,
        "task_id": job.get("task_id"),
        "result": job.get("result"),
        "created_at": job["created_at"],
    }


# -------------------------
# Scheduling & Due campaigns
# -------------------------
print(">>> USING CORRECT schedule_campaign FUNCTION <<<")

async def schedule_campaign(campaign_id: str, send_at: datetime):
    """
    Mark campaign as scheduled and create a scheduled_job with the full payload.

    - Updates campaign: status, send_at, scheduled_at
    - Builds payload for ALL contacts in the segment
    - Stores payload into scheduled_jobs collection
    - Returns (campaign_dict, job_id) for Celery
    """
    campaign = await get_campaign(campaign_id)
    if not campaign:
        return None

    now = datetime.utcnow()

    # Update campaign fields
    await CAMPAIGNS.update_one(
        {"_id": ObjectId(campaign_id)},
        {"$set": {"status": "scheduled", "send_at": send_at, "scheduled_at": now}},
    )

    campaign["status"] = "scheduled"
    campaign["send_at"] = send_at
    campaign["scheduled_at"] = now

    # Ensure we have HTML content for the campaign
    html_content = campaign.get("html_content")
    if not html_content:
        template_doc = await TEMPLATES.find_one({"_id": ObjectId(campaign["template_id"])})
        if template_doc:
            html_content = template_doc.get("html", "")
        else:
            html_content = ""
        campaign["html_content"] = html_content

    subject = campaign["subject"]
    segment = campaign["segment"]

    # Fetch contacts for this segment (bulk-safe)
    cursor = CONTACTS.find({"segment": segment, "unsubscribed": False})

    payload: List[Dict[str, Any]] = []

    async for c in cursor:
        contact_name = c.get("name") or "Customer"
        email = c["email"]
        contact_id = str(c["_id"])

        # unsubscribe link format per leader spec — make absolute
        unsubscribe_link = f"{BACKEND_PUBLIC_URL.rstrip('/')}/unsubscribe/{contact_id}"

        # personalize HTML and ensure absolute image URLs
        final_html = (
            html_content
            .replace("{{name}}", contact_name)
            .replace("{{unsubscribe_link}}", unsubscribe_link)
        )
        final_html = to_absolute_urls(final_html)

        payload.append(
            {
                "email": email,              # <-- FIXED
                "name": contact_name,
                "subject": subject,
                "html": final_html,
                "unsubscribe_link": unsubscribe_link,
                "contact_id": contact_id,
            }
        )


    # Create job document in scheduled_jobs
    job_doc = await create_scheduled_job(
        campaign_id=campaign["id"],
        run_at=send_at,
        payload=payload,
        status="pending",
    )

    job_id = job_doc["_id"]

    # Return both to the router so it can trigger Celery
    return campaign, job_id



async def list_due_campaigns(now: Optional[datetime] = None) -> List[Dict]:
    """
    Return campaigns whose send_at time has passed and status == scheduled.
    This can be used by Team 2 / workers to know which campaigns should fire now.
    """
    if now is None:
        now = datetime.utcnow()

    cursor = CAMPAIGNS.find(
        {
            "status": "scheduled",
            "send_at": {"$lte": now},
        }
    ).sort("send_at", 1)

    out: List[Dict[str, Any]] = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        out.append(doc)
    return out


# -------------------------
# Build bulk send payload (for Team 2 via API)
# -------------------------

async def build_send_payload(campaign_id: str) -> Dict:
    """
    Prepare bulk email payload for Team 2 (for /prepare-send endpoint).

    - Fetch campaign
    - Ensure html_content present
    - Find all contacts with matching segment & unsubscribed=False
    - For each contact:
        - Replace {{name}}
        - Generate unsubscribe_link
        - Produce final html
    """

    campaign = await get_campaign(campaign_id)
    if not campaign:
        raise ValueError("Campaign not found")

    # Ensure html_content exists
    if not campaign.get("html_content"):
        template_doc = await TEMPLATES.find_one({"_id": ObjectId(campaign["template_id"])})
        if not template_doc:
            raise ValueError("Template not found")
        campaign["html_content"] = template_doc.get("html", "")

    base_html = campaign["html_content"]
    subject = campaign["subject"]
    segment = campaign["segment"]

    # Find contacts in this segment who are not unsubscribed
    cursor = CONTACTS.find({"segment": segment, "unsubscribed": False})

    messages: List[Dict[str, Any]] = []
    async for c in cursor:
        contact_name = c.get("name") or "Customer"
        email = c["email"]
        contact_id = str(c["_id"])

        unsubscribe_link = f"{BACKEND_PUBLIC_URL.rstrip('/')}/unsubscribe/{contact_id}"

        final_html = (
            base_html
            .replace("{{name}}", contact_name)
            .replace("{{unsubscribe_link}}", unsubscribe_link)
        )
        final_html = to_absolute_urls(final_html)

        messages.append(
            {
                "email": email,
                "name": contact_name,
                "subject": subject,
                "html": final_html,
                "unsubscribe_link": unsubscribe_link,
            }
        )

    return {
        "campaign_id": campaign["id"],
        "campaign_name": campaign["name"],
        "subject": subject,
        "segment": segment,
        "total_recipients": len(messages),
        "messages": messages,
    }
