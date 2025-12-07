# app/worker.py
import os
from celery import Celery

# 1. Get Redis URL from environment
redis_url = os.getenv("REDIS_URL")

# 2. Define the fallback
broker_url = redis_url if redis_url else "redis://localhost:6379/0"

print("-------------------------------------------------------")
print(f"✅ WORKER STARTING. DETECTED BROKER URL: {broker_url}")
print("-------------------------------------------------------")

# 3. Create Celery App
celery_app = Celery(
    "mailmate",
    broker=broker_url,
    backend=broker_url,
    include=["app.campaigns.tasks"]
)

# 4. Standard Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=1,
    broker_connection_retry_on_startup=True,
)

# 5. THE FIX: FORCE OVERRIDE
# We explicitly overwrite these values at the end to prevent
# any config files or defaults from reverting to localhost.
celery_app.conf.broker_url = broker_url
celery_app.conf.result_backend = broker_url

# verify the change
print(f"DEBUG: Final Config Broker: {celery_app.conf.broker_url}")
print(f"DEBUG: Final Config Backend: {celery_app.conf.result_backend}")