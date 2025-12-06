# app/utils/celery_app.py

from celery import Celery
from app.config import settings  # ✅ FIXED: correct import path


def make_celery() -> Celery:
    """
    Create and configure Celery app instance.
    """
    celery = Celery(
    "mailmate",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.campaigns.tasks",   # 👈 ensures auto-discovery of tasks
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
