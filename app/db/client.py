from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client.get_default_database()

# NO renaming, no suffixes
campaigns = db["campaigns"]
contacts = db["contacts"]
templates = db["templates"]
email_logs = db["email_logs"]
scheduled_jobs = db["scheduled_jobs"]