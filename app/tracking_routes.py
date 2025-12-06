# app/tracking_routes.py
import base64
import hashlib
import hmac
import os
from datetime import datetime
from urllib.parse import unquote

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
import motor.motor_asyncio

router = APIRouter()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "mailmate_db")
SECRET = os.getenv("TRACKING_SECRET", "replace_with_strong_random")
BASE_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
EMAIL_LOGS = db["email_logs"]
EVENTS = db["events"]

# 1x1 PNG
PIXEL_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)
PIXEL_BYTES = base64.b64decode(PIXEL_B64)


def sign(data: str) -> str:
    return hmac.new(SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()


def verify_signature(data: str, sig: str) -> bool:
    return hmac.compare_digest(sign(data), sig)


@router.get("/track/open/{tracking_id}.png")
async def track_open(tracking_id: str, request: Request):
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")[:1000]
    ts = datetime.utcnow()

    # Write lightweight event (audit)
    await EVENTS.insert_one({
        "type": "open",
        "tracking_id": tracking_id,
        "ip": ip,
        "ua": ua,
        "timestamp": ts
    })

    # update aggregates in email_logs
    unique_key = hashlib.sha256(f"{ip}-{ua}".encode()).hexdigest()
    await EMAIL_LOGS.update_one(
        {"tracking_id": tracking_id},
        {
            "$inc": {"open_count": 1},  # FIXED: opens_count -> open_count
            "$set": {"last_opened_at": ts},
            "$addToSet": {"unique_open_keys": unique_key},
            "$push": {"open_events": ts}  # NEW: store event history
        }
    )

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, private, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    return Response(content=PIXEL_BYTES, media_type="image/png", headers=headers)


@router.get("/track/click/{click_id}")
async def track_click(click_id: str, sig: str, d: str, request: Request):
    """
    click endpoint: /track/click/{click_id}?sig={sig}&d={base64url(dest)}
    """
    try:
        dest_b64 = unquote(d)
        dest = base64.urlsafe_b64decode(dest_b64.encode()).decode()
    except Exception:
        raise HTTPException(400, "Bad destination")

    data = f"{click_id}|{dest_b64}"
    if not verify_signature(data, sig):
        raise HTTPException(403, "Invalid signature")

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")[:1000]
    ts = datetime.utcnow()

    # log event
    await EVENTS.insert_one({
        "type": "click",
        "click_id": click_id,
        "dest": dest,
        "ip": ip,
        "ua": ua,
        "timestamp": ts
    })

    # increment click counter on the email_logs doc that has this click_id in click_map
    await EMAIL_LOGS.update_one(
        {f"click_map.{click_id}": {"$exists": True}},
        {
            "$inc": {
                f"clicks.{click_id}": 1,
                "click_count": 1  # NEW: increment total click count
            },
            "$push": {"click_events": ts}  # NEW: store event history
        }
    )

    return RedirectResponse(dest)
