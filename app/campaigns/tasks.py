# app/campaigns/tasks.py

import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# CRITICAL: Import from the new worker file we created
from app.worker import celery_app
from app.utils.config import settings
from app.services.send_bulk_service import BulkEmailService

# ---------------------------------------------------------------------------
# Task 1: Process Scheduled Jobs
# ---------------------------------------------------------------------------

@celery_app.task(name="campaigns.process_scheduled_job")
def process_scheduled_job(job_id: str):
    """
    Celery entrypoint (sync) -> calls async job runner
    """
    print(f"[Celery] Started scheduled job: {job_id}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_job_async(job_id))
    finally:
        loop.close()


async def run_job_async(job_id: str):
    """
    Async logic: Load job, wait for time, send emails, update status.
    """
    # 1. Validate ObjectId
    try:
        oid = ObjectId(job_id)
    except Exception:
        print("[Celery] ❌ Invalid ObjectId:", job_id)
        return

    # 2. Database Connection (Specific to this event loop)
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_default_database()
    JOBS = db["scheduled_jobs"]

    try:
        job = await JOBS.find_one({"_id": oid})

        if not job:
            print(f"[Celery] ❌ Job not found: {job_id}")
            return

        run_at = job["run_at"]
        now = datetime.now(timezone.utc)

        # Fix timezone naive/aware issues
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=timezone.utc)

        print(f"[Celery] Job run_at={run_at}, now={now}")

        # 3. Wait if slightly early (Clock skew protection)
        if run_at > now:
            delta = (run_at - now).total_seconds()
            if delta > 0:
                print(f"[Celery] ⏳ Task started early. Waiting {delta:.2f}s...")
                await asyncio.sleep(delta)

        # 4. Prepare Sender
        from_email = settings.SENDER_EMAIL
        if not from_email:
            print("[Celery] ❌ ERROR: No SENDER_EMAIL configured.")
            return

        print(f"Attempting to send email FROM {from_email}...")

        # 5. Prepare Payload
        first_msg = job["payload"][0] if job["payload"] else {}
        subject = first_msg.get("subject", "")
        reply_to = job.get("reply_to")

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

        # 6. Send via SendGrid
        service = BulkEmailService(
            sendgrid_api_key=settings.SENDGRID_API_KEY,
            email_logs_collection=None
        )

        print(f"[Celery] 🚀 Sending emails for job {job_id} ...")
        result = await service.send_bulk(payload)
        await service.close()

        # 7. Update Job Status
        await JOBS.update_one(
            {"_id": oid},
            {"$set": {"status": "done", "result": result}}
        )

        print(f"[Celery] ✅ Job completed: {job_id}")

    finally:
        client.close()


# ---------------------------------------------------------------------------
# Task 2: Send Immediate Campaign
# ---------------------------------------------------------------------------

@celery_app.task(name="campaigns.send_campaign_task")
def send_campaign_task(campaign_id: str):
    """
    Send a campaign immediately.
    """
    print(f"[Celery] Starting send_campaign_task for: {campaign_id}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_send_campaign_async(campaign_id))
    finally:
        loop.close()


async def run_send_campaign_async(campaign_id: str):
    # Database Connection (Specific to this event loop)
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_default_database()
    campaigns = db["campaigns"]
    contacts = db["contacts"]
    
    try:
        try:
            oid = ObjectId(campaign_id)
        except Exception:
            print(f"[Celery] ❌ Invalid Campaign ID: {campaign_id}")
            return

        # 1. Fetch Campaign
        campaign = await campaigns.find_one({"_id": oid})
        if not campaign:
            print(f"[Celery] ❌ Campaign not found: {campaign_id}")
            return

        # 2. Fetch Contacts
        segment = campaign.get("segment", "All Contacts")
        query = {"unsubscribed": {"$ne": True}}
        
        if segment != "All Contacts":
            query["segment"] = segment
            
        contact_list = await contacts.find(query).to_list(length=None)
        
        if not contact_list:
            print(f"[Celery] ⚠️ No contacts found for segment: {segment}")
            await campaigns.update_one(
                {"_id": oid}, 
                {"$set": {"status": "Failed", "error": "No contacts found"}}
            )
            return

        print(f"[Celery] Found {len(contact_list)} contacts for campaign '{campaign.get('title')}'")

        # 3. Prepare Payload
        from_email = settings.SENDER_EMAIL
        if not from_email:
            print("[Celery] ❌ ERROR: No SENDER_EMAIL configured.")
            return

        messages = []
        html_content = campaign.get("html_content", "")
        subject = campaign.get("subject", "")
        reply_to = campaign.get("reply_to")
        
        # Base URL for unsubscribe links
        backend_url = getattr(settings, 'BACKEND_PUBLIC_URL', 'http://localhost:8000')

        for c in contact_list:
            # Personalization
            personal_html = html_content.replace("{{name}}", c.get("name", "Friend"))
            
            # Unsubscribe Link
            unsubscribe_link = f"{backend_url}/unsubscribe/{str(c['_id'])}"
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

        # 4. Send Emails
        service = BulkEmailService(
            sendgrid_api_key=settings.SENDGRID_API_KEY,
            email_logs_collection=None 
        )

        print(f"[Celery] 🚀 Sending {len(messages)} emails...")
        result = await service.send_bulk(payload)
        await service.close()

        # 5. Update Status
        new_status = "Sent" if result.get("sent", 0) > 0 else "Failed"
        await campaigns.update_one(
            {"_id": oid},
            {"$set": {
                "status": new_status, 
                "result": result, 
                "sent_at": datetime.now(timezone.utc)
            }}
        )
        
        print(f"[Celery] ✅ Campaign sent. Status: {new_status}")

    finally:
        client.close()