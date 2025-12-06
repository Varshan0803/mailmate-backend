# app/routes/send_bulk.py
from fastapi import APIRouter, HTTPException
from bson import ObjectId

from app.db.client import campaigns, contacts, templates, email_logs
from app.services.send_bulk_service import BulkEmailService
from app.config import settings

router = APIRouter()


@router.post("/send-bulk/{campaign_id}")
async def send_bulk(campaign_id: str):
    # 1. Fetch campaign
    campaign = await campaigns.find_one({"_id": ObjectId(campaign_id)})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    segment = campaign.get("segment")
    template_id = campaign.get("template_id")
    subject = campaign.get("subject")
    campaign_name = campaign.get("name")

    # 2. Fetch template
    template = await templates.find_one({"_id": ObjectId(template_id)})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    html_template = template.get("html", "")

    # 3. Fetch contacts for the segment (exclude unsubscribed)
    contacts_cursor = contacts.find({"segment": segment, "unsubscribed": {"$ne": True}})
    contact_list = await contacts_cursor.to_list(length=None)

    if not contact_list:
        return {"message": f"No contacts found for segment '{segment}'", "total_recipients": 0}

    # 4. Prepare messages list (personalize)
    messages = []
    for c in contact_list:
        # build unsubscribe link — keep consistent with your app domain
        unsubscribe_link = f"{getattr(settings, 'BACKEND_PUBLIC_URL', 'http://localhost:8000')}/unsubscribe/{str(c['_id'])}"
        html = html_template.replace("{{name}}", c.get("name", "")).replace("{{unsubscribe_link}}", unsubscribe_link)

        messages.append({
            "email": c.get("email"),
            "name": c.get("name"),
            "subject": subject,
            "html": html,
            "unsubscribe_link": unsubscribe_link
        })

    campaign_payload = {
        "campaign_id": str(campaign["_id"]),
        "campaign_name": campaign_name,
        "subject": subject,
        "segment": segment,
        "total_recipients": len(messages),
        "messages": messages,
        "from_email": getattr(settings, "SENDER_EMAIL", None)
    }

    # 5. Instantiate bulk service and call send_bulk
    service = BulkEmailService(
        sendgrid_api_key=getattr(settings, "SENDGRID_API_KEY", None),
        mongo_client=None,
        email_logs_collection=email_logs,
        batch_size=50,
        concurrency=8,
        rate_limit_per_sec=10
    )

    result = await service.send_bulk(campaign_payload)
    await service.close()

    return {"message": "Bulk send started/completed", "result": result}
