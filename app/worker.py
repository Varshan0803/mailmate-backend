# app/worker.py
import os
from celery import Celery

# 1. Get Redis URL
redis_url = os.getenv("REDIS_URL")
broker_url = redis_url if redis_url else "redis://localhost:6379/0"

print(f"✅ WORKER STARTING. BROKER: {broker_url}")

# 2. Create Celery App
# IMPORTANT: We removed 'include=['app.campaigns.tasks']' to stop the sabotage
celery_app = Celery(
    "mailmate",
    broker=broker_url,
    backend=broker_url,
    broker_connection_retry_on_startup=True
)

celery_app.conf.update(worker_concurrency=1)

# 3. Force Config
celery_app.conf.broker_url = broker_url
celery_app.conf.result_backend = broker_url

print(f"DEBUG: Final Config is: {celery_app.conf.broker_url}")