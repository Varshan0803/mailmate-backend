# app/worker.py
import os

# 1. FORCE THE ENVIRONMENT VARIABLES FIRST
# By setting these in os.environ, Celery will pick them up automatically
# and they cannot be overwritten by config files easily.
redis_url = os.getenv("REDIS_URL")

if redis_url:
    print(f"✅ FOUND REDIS URL: {redis_url}")
    # Force Celery to use this via internal env vars
    os.environ["CELERY_BROKER_URL"] = redis_url
    os.environ["CELERY_RESULT_BACKEND"] = redis_url
else:
    print("⚠️ NO REDIS URL FOUND. Defaulting to localhost.")
    # Fallback for local testing
    os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
    os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/1"

# 2. Now import Celery
from celery import Celery

print("-------------------------------------------------------")
print(f"🚀 WORKER LOADING - ENV VAR STRATEGY")
print(f"✅ ENV BROKER: {os.environ.get('CELERY_BROKER_URL')}")
print("-------------------------------------------------------")

# 3. Create Celery App
# NOTICE: We do NOT pass broker= here. Celery will find the env var we just set.
celery_app = Celery(
    "mailmate",
    broker_connection_retry_on_startup=True,
    include=["app.campaigns.tasks"] 
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=1,
)

# 4. Final Verification
print(f"🔒 FINAL CONFIRMED BROKER: {celery_app.conf.broker_url}")