# app/services/send_bulk_service.py
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from app.services.sendgrid_client import SendGridClient
from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 50
DEFAULT_CONCURRENCY = 8
DEFAULT_RATE_LIMIT_PER_SEC = 10


class BulkEmailService:
    def __init__(
        self,
        sendgrid_api_key: Optional[str] = None,
        mongo_client: Optional[AsyncIOMotorClient] = None,
        email_logs_collection: Optional[AsyncIOMotorCollection] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        concurrency: int = DEFAULT_CONCURRENCY,
        rate_limit_per_sec: int = DEFAULT_RATE_LIMIT_PER_SEC,
    ):
        self.sg_key = sendgrid_api_key or getattr(settings, "SENDGRID_API_KEY")
        self.sg_client = SendGridClient(self.sg_key)
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.rate_limit_per_sec = rate_limit_per_sec

        # If caller passed the collection explicitly use it, else derive from mongo_client/settings
        if email_logs_collection is not None:
            self.email_logs = email_logs_collection
        else:
            if not mongo_client:
                mongo_client = AsyncIOMotorClient(getattr(settings, "MONGO_URI"))
            self.email_logs = mongo_client.get_default_database().get_collection("email_logs")

        self._semaphore = asyncio.Semaphore(self.concurrency)
        self._per_message_delay = 1.0 / max(1, self.rate_limit_per_sec)

    async def _save_initial_log(self, record: Dict[str, Any]) -> None:
        try:
            await self.email_logs.insert_one(record)
        except Exception:
            logger.exception("Failed to insert email log into DB: %s", record)

    def _build_sendgrid_payload(self, from_email: str, to_email: str, subject: str, html: str, campaign_id: str, reply_to: Optional[str] = None) -> Dict:
        from sendgrid.helpers.mail import (
            Mail, Email, To, Content, TrackingSettings, ClickTracking, 
            OpenTracking, CustomArg, Category
        )

        # 1. Create Mail object
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html)  # Force HTML content
        )

        # 2. Add Reply-To if exists
        if reply_to:
            message.reply_to = Email(reply_to)

        # 3. Add Custom Args & Categories
        message.add_category(Category(campaign_id))
        message.add_custom_arg(CustomArg("campaign_id", campaign_id))

        # 4. Explicitly Enable Tracking
        tracking_settings = TrackingSettings()
        
        # Click Tracking
        tracking_settings.click_tracking = ClickTracking(enable=True, enable_text=True)
        
        # Open Tracking
        tracking_settings.open_tracking = OpenTracking(enable=True)
        
        message.tracking_settings = tracking_settings

        return message.get()

    async def _send_one(self, from_email: str, message: Dict[str, Any], campaign_id: str, reply_to: Optional[str] = None) -> Dict[str, Any]:
        to_email = message["email"]
        subject = message.get("subject") or ""
        html = message.get("html") or ""

        payload = self._build_sendgrid_payload(from_email=from_email, to_email=to_email, subject=subject, html=html, campaign_id=campaign_id, reply_to=reply_to)

        async with self._semaphore:
            await asyncio.sleep(self._per_message_delay)

            attempt_meta = await self.sg_client.send(payload)

            # Log each underlying attempt detail
            for det in attempt_meta.get("attempt_details", []):
                logger.info(
                    "Delivery attempt for %s (campaign=%s) attempt=%s status=%s error=%s",
                    to_email,
                    campaign_id,
                    det.get("attempt"),
                    det.get("status"),
                    det.get("error")
                )

            status_text = "sent" if attempt_meta.get("success") else "failed"
            log_doc = {
                "campaign_id": campaign_id,
                "email": to_email,
                "name": message.get("name"),
                "subject": subject,
                "status": status_text,   # initial status: accepted by sendgrid => 'sent'
                "sendgrid_status": attempt_meta.get("status_code"),
                "sendgrid_body": attempt_meta.get("body"),
                "attempts": attempt_meta.get("attempts"),
                "attempt_details": attempt_meta.get("attempt_details"),
                "error": attempt_meta.get("error"),
                "open_count": 0,
                "click_count": 0,
                "open_events": [],
                "click_events": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            await self._save_initial_log(log_doc)

            if attempt_meta.get("success"):
                logger.info("Email accepted by SendGrid: %s (campaign=%s)", to_email, campaign_id)
            else:
                logger.error("Email failed to send: %s (campaign=%s) error=%s", to_email, campaign_id, attempt_meta.get("error"))

            return {"email": to_email, "success": attempt_meta.get("success", False), "meta": attempt_meta}

    async def send_bulk(self, campaign_payload: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = campaign_payload["campaign_id"]
        messages: List[Dict[str, Any]] = campaign_payload.get("messages", [])
        from_email = campaign_payload.get("from_email") or getattr(settings, "SENDER_EMAIL", None)
        reply_to = campaign_payload.get("reply_to")
        if not from_email:
            raise ValueError("No from_email provided in payload or settings.SENDER_EMAIL")

        total = len(messages)
        logger.info("SendBulk started campaign=%s total=%s", campaign_id, total)

        results = []
        for i in range(0, total, self.batch_size):
            batch = messages[i: i + self.batch_size]
            logger.info("Processing batch %s - %s (size=%s)", i, i + len(batch) - 1, len(batch))
            tasks = [asyncio.create_task(self._send_one(from_email=from_email, message=m, campaign_id=campaign_id, reply_to=reply_to)) for m in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=False)
            results.extend(batch_results)
            await asyncio.sleep(0.5)

        sent = sum(1 for r in results if r.get("success"))
        failed = sum(1 for r in results if not r.get("success"))

        logger.info("SendBulk finished campaign=%s sent=%s failed=%s total=%s", campaign_id, sent, failed, total)

        return {"campaign_id": campaign_id, "total": total, "sent": sent, "failed": failed, "details": results}

    async def close(self):
        await self.sg_client.close()
