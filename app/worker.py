# app/worker.py
import os
from celery import Celery

# 1. Capture the Redis URL immediately
redis_url = os.getenv("REDIS_URL")

# Fallback string for local development
fallback = "redis://localhost:6379/0"

# Select the actual URL to use
broker_url = redis_url if redis_url else fallback

print("-------------------------------------------------------")
print(f"🚀 WORKER LOADING - VERSION FINAL")
print(f"✅ DETECTED REDIS URL: {broker_url}")
print("-------------------------------------------------------")

# 2. Configure Celery
# We pass the broker DIRECTLY here. This is the strongest way to set it.
celery_app = Celery(
    "mailmate",
    broker=broker_url,  # <--- Forced here
    backend=broker_url, # <--- Forced here
    broker_connection_retry_on_startup=True,
    include=["app.campaigns.tasks"]
)

# 3. Apply settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=1,
)

# 4. SAFETY LOCK: Overwrite config one last time
# This protects against any imported tasks resetting the config
celery_app.conf.broker_url = broker_url
celery_app.conf.result_backend = broker_url

print(f"🔒 LOCKED CONFIG BROKER: {celery_app.conf.broker_url}")