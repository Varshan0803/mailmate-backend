# app/utils/celery_app.py

import os
from celery import Celery
from app.utils.config import settings

def make_celery() -> Celery:
    # 1. Get the Railway Redis URL
    # We grab this directly from the environment to be 100% sure
    redis_url = os.getenv("REDIS_URL")

    # 2. Create the Celery App
    # We initially pass the URL, but config.py might try to overwrite it later
    celery = Celery(
        "mailmate",
        broker=redis_url,
        backend=redis_url,
        broker_connection_retry_on_startup=True,
        include=["app.campaigns.tasks"]
    )

    # 3. Load other settings (serialization, timezone, etc)
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        worker_concurrency=1,
    )

    # ---------------------------------------------------------
    # 4. THE NUCLEAR FIX: FORCE OVERRIDE
    # ---------------------------------------------------------
    # If we found a valid REDIS_URL in the environment, we FORCE
    # Celery to use it, ignoring whatever is in config.py
    if redis_url:
        print(f"DEBUG: Forcing Broker URL to: {redis_url}")
        celery.conf.broker_url = redis_url
        celery.conf.result_backend = redis_url
    else:
        print("DEBUG: No REDIS_URL found. Falling back to default (localhost).")
    # ---------------------------------------------------------

    return celery

# Export both names to satisfy Railway and your imports
celery = make_celery()
celery_app = celery