# app/utils/celery_app.py

import os
import sys
from celery import Celery

def make_celery() -> Celery:
    """
    Create and configure Celery app instance.
    """
    # 1. Fetch the REDIS_URL from environment variables
    # Railway automatically provides REDIS_URL if the service is linked.
    env_redis_url = os.getenv("REDIS_URL")
    
    # Fallback logic: Use REDIS_URL first, then CELERY_BROKER_URL, then localhost
    redis_url = env_redis_url or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

    # --- DEBUGGING BLOCK: This prints to your Railway Logs ---
    print("----------------------------------------------------------------")
    print(f"DEBUG_CHECK: System Platform: {sys.platform}")
    print(f"DEBUG_CHECK: Raw REDIS_URL from env: '{env_redis_url}'")
    print(f"DEBUG_CHECK: Final redis_url being used: '{redis_url}'")
    print("----------------------------------------------------------------")
    # ---------------------------------------------------------

    # 2. Initialize Celery
    celery = Celery(
        "mailmate",
        broker=redis_url,
        backend=redis_url,
        broker_connection_retry_on_startup=True,
        # Ensure this path matches exactly where your task files are located
        include=[
            "app.campaigns.tasks", 
        ]
    )

    # 3. Apply Configuration
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        worker_concurrency=1,  # Matches your start command flag
    )

    return celery

# This is the Celery app object that the worker will use
celery_app = make_celery()