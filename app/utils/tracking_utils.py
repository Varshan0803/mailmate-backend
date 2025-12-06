# app/utils/tracking_utils.py
import base64
import hashlib
import hmac
import os
from uuid import uuid4
from urllib.parse import quote

SECRET = os.getenv("TRACKING_SECRET", "replace_with_strong_random")
BASE_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")


def make_tracking_id() -> str:
    return uuid4().hex


def make_click_id() -> str:
    return uuid4().hex


def _sign(data: str) -> str:
    return hmac.new(SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()


def make_signed_click_url(click_id: str, dest: str) -> str:
    dest_b64 = base64.urlsafe_b64encode(dest.encode()).decode()
    data = f"{click_id}|{dest_b64}"
    sig = _sign(data)
    return f"{BASE_URL}/track/click/{click_id}?sig={sig}&d={quote(dest_b64)}"
