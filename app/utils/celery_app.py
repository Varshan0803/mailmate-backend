# app/utils/celery_app.py

import os
from celery import Celery

def make_celery() -> Celery:
    """
    Create and configure Celery app instance.
    """
    # Priority: 1. REDIS_URL, 2. CELERY_BROKER_URL, 3. Fallback to localhost
    redis_url = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))

    celery = Celery(
        "mailmate",
        broker=redis_url,
        backend=redis_url,
        broker_connection_retry_on_startup=True,
        include=[
            "app.campaigns.tasks",
        ]
    )

    # Optional: common Celery config
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )

    return celery


# This is the Celery app object that the worker will use
celery_app = make_celery()
