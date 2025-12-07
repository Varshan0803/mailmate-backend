# app/utils/celery_app.py

import os
from celery import Celery

# --- DELETED THE BROKEN IMPORT LINE HERE ---

def make_celery() -> Celery:
    # 1. Get the Railway Redis URL directly from environment
    redis_url = os.getenv("REDIS_URL")
    
    # Fallback to localhost if not found (for local dev)
    broker_url = redis_url if redis_url else "redis://localhost:6379/0"

    # 2. Create the Celery App
    celery = Celery(
        "mailmate",
        broker=broker_url,
        backend=broker_url,
        broker_connection_retry_on_startup=True,
        include=["app.campaigns.tasks"]
    )

    # 3. Apply standard configuration
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        worker_concurrency=1,
    )

    # 4. FORCE OVERRIDE (The Nuclear Fix)
    # If we are on Railway (redis_url exists), we force these settings
    # to ensure config.py cannot mess it up.
    if redis_url:
        print(f"DEBUG: Forcing Broker URL to: {redis_url}")
        celery.conf.broker_url = redis_url
        celery.conf.result_backend = redis_url

    return celery

# Export both names
celery = make_celery()
celery_app = celery