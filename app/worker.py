# app/worker.py

import os
from celery import Celery

# 1. Get Redis URL from environment
redis_url = os.getenv('REDIS_URL')

# 2. Define the fallback (Localhost)
broker_url = redis_url if redis_url else 'redis://localhost:6379/0'

print('-------------------------------------------------------')
print(f'✅ WORKER STARTING. DETECTED BROKER URL: {broker_url}')
print('-------------------------------------------------------')

# 3. Create Celery App
celery_app = Celery(
    'mailmate',
    broker=broker_url,
    backend=broker_url,
    broker_connection_retry_on_startup=True,
    include=['app.campaigns.tasks']
)

# 4. Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_concurrency=1,
)
