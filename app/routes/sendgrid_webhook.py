from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from datetime import datetime
from app.db.client import db
from app.config import settings
import logging
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature

router = APIRouter()
logger = logging.getLogger(__name__)
print("DEBUG: sendgrid_webhook module loaded")

@router.post("/sendgrid/webhook")
async def sendgrid_event_webhook(request: Request):
    """
    Endpoint to receive SendGrid event webhook callbacks for email events.
    Processes events such as open, click, bounce, spamreport and updates email_logs.
    """
    print("\n\n🚨🚨🚨 WEBHOOK HIT! DATA RECEIVED! 🚨🚨🚨\n\n")
    logger.info("🔔 Webhook received from SendGrid")
    disable_verify = getattr(settings, "SENDGRID_WEBHOOK_DISABLE_VERIFY", False)
    if disable_verify:
        try:
            events: List[Dict[str, Any]] = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse SendGrid webhook payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
    else:
        try:
            raw_body: bytes = await request.body()
            timestamp = request.headers.get("X-Twilio-Email-Event-Webhook-Timestamp")
            signature_b64 = request.headers.get("X-Twilio-Email-Event-Webhook-Signature")
            if not timestamp or not signature_b64:
                raise HTTPException(status_code=401, detail="Missing webhook signature headers")

            pub_key_val = getattr(settings, "SENDGRID_PUBLIC_KEY", None)
            if not pub_key_val:
                raise HTTPException(status_code=500, detail="SendGrid public key not configured")

            try:
                if pub_key_val.startswith("-----BEGIN"):
                    public_key = serialization.load_pem_public_key(pub_key_val.encode())
                else:
                    der_bytes = base64.b64decode(pub_key_val)
                    public_key = serialization.load_der_public_key(der_bytes)
            except Exception as e:
                logger.error(f"Failed loading SendGrid public key: {e}")
                raise HTTPException(status_code=500, detail="Invalid SendGrid public key")

            signed_payload = (timestamp + raw_body.decode("utf-8")).encode("utf-8")
            signature = base64.b64decode(signature_b64)
            try:
                public_key.verify(signature, signed_payload, ec.ECDSA(hashes.SHA256()))
            except InvalidSignature:
                logger.warning("Invalid SendGrid webhook signature")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

            events: List[Dict[str, Any]] = await request.json()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to parse/verify SendGrid webhook payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(events, list):
        logger.error("SendGrid webhook payload is not a list")
        raise HTTPException(status_code=400, detail="Expected a list of events")

    # DEBUG: Print raw payload
    print(f"DEBUG: Raw SendGrid Payload: {events}")

    coll = db.get_collection("email_logs")
    campaigns_coll = db.get_collection("campaigns")
    from bson import ObjectId

    for event in events:
        try:
            email = event.get("email")
            event_type = event.get("event")
            timestamp = event.get("timestamp")
            
            # Extract Campaign ID
            unique_args = event.get("unique_args") or event.get("custom_args") or {}
            categories = event.get("category")
            if isinstance(categories, list) and categories:
                category_val = categories[0]
            else:
                category_val = categories
            
            campaign_id_raw = (
                event.get("campaign_id")
                or unique_args.get("campaign_id")
                or category_val
                or None
            )

            print(f"DEBUG: Processing event: {event_type} for Campaign ID: {campaign_id_raw}, Email: {email}")

            if not email or not event_type or not timestamp or not campaign_id_raw:
                logger.warning(f"Skipping event missing required fields: {event}")
                print(f"DEBUG: Skipping event due to missing fields.")
                continue

            event_datetime = datetime.utcfromtimestamp(timestamp)

            # --- 1. Robust Campaign Lookup ---
            campaign_doc = None
            
            # Try String Match
            campaign_doc = await campaigns_coll.find_one({"_id": campaign_id_raw})
            
            # Try ObjectId Match
            if not campaign_doc and ObjectId.is_valid(campaign_id_raw):
                print(f"DEBUG: No string match for campaign_id {campaign_id_raw}, trying ObjectId...")
                campaign_doc = await campaigns_coll.find_one({"_id": ObjectId(campaign_id_raw)})

            if not campaign_doc:
                print(f"❌ CRITICAL: Campaign {campaign_id_raw} not found in DB (String or ObjectId). Skipping stats update.")
                # We might still want to log the email event even if campaign is missing?
                # For now, let's proceed with email_logs update using the raw ID, but we can't update campaign stats.
            else:
                print(f"DEBUG: Found Campaign document: {campaign_doc['_id']}")

            # --- 2. Update Email Logs ---
            # Find matching email log entry
            query = {"campaign_id": campaign_id_raw, "email": email}
            existing_log = await coll.find_one(query)
            
            # If not found, try ObjectId match for the log query too (consistency)
            if not existing_log and ObjectId.is_valid(campaign_id_raw):
                 query = {"campaign_id": ObjectId(campaign_id_raw), "email": email}
                 existing_log = await coll.find_one(query)

            if not existing_log:
                print(f"DEBUG: Log entry not found for {email}. Creating new one.")
                new_log = {
                    "campaign_id": campaign_id_raw,
                    "email": email,
                    "open_count": 0,
                    "click_count": 0,
                    "open_events": [],
                    "click_events": [],
                    "created_at": event_datetime,
                    "updated_at": event_datetime,
                }
                await coll.insert_one(new_log)
                existing_log = new_log
            
            # Prepare updates
            log_update = {"$set": {"updated_at": event_datetime}}
            campaign_update = {}

            if event_type == "open":
                log_update["$inc"] = {"open_count": 1}
                log_update["$push"] = {"open_events": {"timestamp": event_datetime}}
                campaign_update = {"$inc": {"stats.opens": 1}}
                logger.info(f"Recording open event for {email}")
                
            elif event_type == "click":
                log_update["$inc"] = {"click_count": 1}
                log_update["$push"] = {"click_events": {"timestamp": event_datetime}}
                campaign_update = {"$inc": {"stats.clicks": 1}}
                logger.info(f"Recording click event for {email}")
                
            elif event_type == "bounce":
                log_update["$set"]["status"] = "bounced"
                log_update["$set"]["bounced_at"] = event_datetime
                campaign_update = {"$inc": {"stats.bounces": 1}}
                
            elif event_type == "spamreport":
                log_update["$set"]["status"] = "spamreport"
                log_update["$set"]["spam_report_at"] = event_datetime
                campaign_update = {"$inc": {"stats.spam_reports": 1}}
                
            elif event_type == "delivered":
                log_update["$set"]["status"] = "delivered"
                log_update["$set"]["delivered_at"] = event_datetime
                # campaign_update = {"$inc": {"stats.delivered": 1}} # Optional

            # Execute Log Update
            await coll.update_one({"_id": existing_log["_id"]}, log_update)
            
            # Execute Campaign Update (if campaign found and update exists)
            if campaign_doc and campaign_update:
                await campaigns_coll.update_one({"_id": campaign_doc["_id"]}, campaign_update)
                print(f"✅ Updated Campaign {campaign_doc['_id']} stats!")

        except Exception as e:
            logger.error(f"Failed processing SendGrid event: {event}, error: {e}")
            print(f"DEBUG: Exception processing event: {e}")

    logger.info(f"✅ Processed {len(events)} webhook events from SendGrid")
    return JSONResponse(content={"message": "Events processed"}, status_code=200)
