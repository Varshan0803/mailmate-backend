# app/campaigns/tasks.py

from datetime import datetime, timezone
from bson import ObjectId
import asyncio
import os

from app.worker import celery_app
from app.campaigns.services import JOBS
from app.services.send_bulk_service import BulkEmailService
from app.config import settings


@celery_app.task(name="campaigns.process_scheduled_job")
def process_scheduled_job(job_id: str):
    """
    Celery entrypoint (sync) → calls async job runner
    """
    print(f"[Celery] Started scheduled job: {job_id}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_job_async(job_id))
    loop.close()


async def run_job_async(job_id: str):
    """
    Async logic:
    - load job
    - wait until scheduled time
    - send emails using SendGrid bulk service
    - mark status: done
    """

    # 1️⃣ Validate ObjectId
    try:
        oid = ObjectId(job_id)
    except:
        print("[Celery] ❌ Invalid ObjectId:", job_id)
        return

    # 2️⃣ Load job from DB
    # 2️⃣ Load job from DB
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.config import settings
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_default_database()
    JOBS = db["scheduled_jobs"]

    job = await JOBS.find_one({"_id": oid})

    if not job:
        print(f"[Celery] ❌ Job not found: {job_id}")
        return

    run_at = job["run_at"]
    now = datetime.now(timezone.utc)

    # 🔧 FIX: MongoDB returns naive datetime → convert to UTC aware
    if run_at.tzinfo is None:
        run_at = run_at.replace(tzinfo=timezone.utc)

    print(f"[Celery] Job run_at={run_at}, now={now}")

    # 3️⃣ Wait until scheduled time
    # NOTE: We used to sleep here, but now we use Celery's 'eta' feature.
    # However, if the worker picks it up slightly early (clock skew), we can do a small check.
    if run_at > now:
        delta = (run_at - now).total_seconds()
        if delta > 0:
            print(f"[Celery] ⏳ Task started early. Waiting {delta:.2f}s...")
            await asyncio.sleep(delta)

    # 4️⃣ Sender address
    from app.config import settings
    from_email = settings.SENDER_EMAIL
    if not from_email:
        print("[Celery] ❌ ERROR: No SENDER_EMAIL configured.")
        return
    
    print(f"Attempting to send email FROM {from_email}...")
    
    # Extract reply_to from job if available
    reply_to = job.get("reply_to")

    # 5️⃣ Extract subject from first payload item
    first_msg = job["payload"][0] if job["payload"] else {}
    subject = first_msg.get("subject", "")

    # 6️⃣ Prepare full bulk payload for BulkEmailService
    payload = {
        "campaign_id": job["campaign_id"],
        "campaign_name": job.get("campaign_name", ""),
        "subject": subject,
        "segment": job.get("segment", ""),
        "messages": job["payload"],
        "total_recipients": len(job["payload"]),
        "from_email": from_email,
        "reply_to": reply_to,
    }

    # 7️⃣ Send via SendGrid bulk service
    service = BulkEmailService(
        sendgrid_api_key=settings.SENDGRID_API_KEY,
        email_logs_collection=None  # use default email_logs collection
    )

    print(f"[Celery] 🚀 Sending emails for job {job_id} ...")

    result = await service.send_bulk(payload)
    await service.close()

    # 8️⃣ Mark job completed
    await JOBS.update_one(
        {"_id": oid},
        {"$set": {"status": "done", "result": result}}
    )

    print(f"[Celery] ✅ Job completed: {job_id}")


@celery_app.task(name="campaigns.send_campaign_task")
def send_campaign_task(campaign_id: str):
    """
    Send a campaign immediately.
    """
    print(f"[Celery] Starting send_campaign_task for: {campaign_id}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_send_campaign_async(campaign_id))
    loop.close()

async def run_send_campaign_async(campaign_id: str):
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.config import settings
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_default_database()
    campaigns = db["campaigns"]
    contacts = db["contacts"]
    
    try:
        oid = ObjectId(campaign_id)
    except:
        print(f"[Celery] ❌ Invalid Campaign ID: {campaign_id}")
        return

    # 1. Fetch campaign
    campaign = await campaigns.find_one({"_id": oid})
    if not campaign:
        print(f"[Celery] ❌ Campaign not found: {campaign_id}")
        return

    # 2. Fetch contacts
    # Logic: if segment is "All Contacts", fetch all. 
    # If it's a segment name, filter by segment.
    segment = campaign.get("segment", "All Contacts")
    query = {"unsubscribed": {"$ne": True}}
    
    if segment != "All Contacts":
        query["segment"] = segment
        
    contact_list = await contacts.find(query).to_list(length=None)
    
    if not contact_list:
        print(f"[Celery] ⚠️ No contacts found for segment: {segment}")
        await campaigns.update_one({"_id": oid}, {"$set": {"status": "Failed", "error": "No contacts found"}})
        return

    print(f"[Celery] Found {len(contact_list)} contacts for campaign '{campaign.get('title')}'")

    # 3. Prepare payload
    # Override sender with env var
    from app.config import settings
    from_email = settings.SENDER_EMAIL
    if not from_email:
        print("[Celery] ❌ ERROR: No SENDER_EMAIL configured.")
        return

    print(f"Attempting to send email FROM {from_email}...")
    
    # Extract reply_to from campaign if available
    reply_to = campaign.get("reply_to")

    messages = []
    html_content = campaign.get("html_content", "")
    subject = campaign.get("subject", "")
    
    for c in contact_list:
        # Simple personalization
        # In a real app, use a template engine like Jinja2
        personal_html = html_content.replace("{{name}}", c.get("name", "Friend"))
        
        # Add unsubscribe link
        unsubscribe_link = f"{getattr(settings, 'BACKEND_PUBLIC_URL', 'http://localhost:8000')}/unsubscribe/{str(c['_id'])}"
        personal_html += f"<br><br><a href='{unsubscribe_link}'>Unsubscribe</a>"

        messages.append({
            "email": c.get("email"),
            "name": c.get("name"),
            "subject": subject,
            "html": personal_html,
            "unsubscribe_link": unsubscribe_link
        })

    payload = {
        "campaign_id": str(campaign["_id"]),
        "campaign_name": campaign.get("title"),
        "subject": subject,
        "segment": segment,
        "messages": messages,
        "total_recipients": len(messages),
        "from_email": from_email,
        "reply_to": reply_to,
    }

    # 4. Send emails
    service = BulkEmailService(
        sendgrid_api_key=settings.SENDGRID_API_KEY,
        email_logs_collection=None 
    )

    print(f"[Celery] 🚀 Sending {len(messages)} emails...")
    result = await service.send_bulk(payload)
    await service.close()

    # 5. Update status
    new_status = "Sent" if result.get("sent", 0) > 0 else "Failed"
    await campaigns.update_one(
        {"_id": oid},
        {"$set": {"status": new_status, "result": result, "sent_at": datetime.utcnow()}}
    )
    
    print(f"[Celery] ✅ Campaign sent. Status: {new_status}")
