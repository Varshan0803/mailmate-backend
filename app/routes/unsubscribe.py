# app/routes/unsubscribe.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from bson import ObjectId

from app.db.client import campaigns, contacts, templates, email_logs, scheduled_jobs
router = APIRouter()

@router.get("/unsubscribe/{contact_id}", response_class=HTMLResponse)
async def unsubscribe(contact_id: str):
    try:
        oid = ObjectId(contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid unsubscribe link")

    result = await contacts.update_one(
        {"_id": oid},
        {"$set": {"unsubscribed": True}}
    )

    # optional: remove already-scheduled jobs for this contact
    await scheduled_jobs.delete_many({"contact_id": oid})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")

    # simple confirmation page
    return """
    <html>
      <body style="font-family: Arial; text-align:center; padding-top:50px;">
        <h2>You have been unsubscribed.</h2>
        <p>You will no longer receive emails from this campaign.</p>
      </body>
    </html>
    """
@router.get("/campaigns/{campaign_id}/unsubscribed-count")
async def unsubscribed_count_for_campaign(campaign_id: str):
    try:
        cid = ObjectId(campaign_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid campaign id")

    # 1) Find the campaign
    campaign = await campaigns.find_one({"_id": cid})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    segment = campaign.get("segment")
    if not segment:
        raise HTTPException(
            status_code=400,
            detail="Campaign does not have a segment field"
        )

    # 2) Count unsubscribed contacts in that segment
    count = await contacts.count_documents({
        "segment": segment,
        "unsubscribed": True
    })

    return {
        "campaign_id": str(campaign_id),
        "segment": segment,
        "unsubscribed_count": count,
    }