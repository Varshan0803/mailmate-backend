import asyncio
import os
import motor.motor_asyncio
from datetime import datetime
from bson import ObjectId

# Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "mailmate_db")

async def create_dummy_data():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Create Dummy Campaign
    campaign_id = ObjectId()
    campaign = {
        "_id": campaign_id,
        "name": "Test Analytics Campaign",
        "subject": "Test Subject",
        "content": "<html><body><a href='http://example.com'>Link</a></body></html>",
        "status": "sent",
        "created_at": datetime.utcnow()
    }
    await db.campaigns.insert_one(campaign)
    print(f"Created dummy campaign: {campaign_id}")

    # Create Dummy Email Log
    log = {
        "campaign_id": str(campaign_id),
        "email": "test@example.com",
        "status": "delivered",
        "tracking_id": "track_123",
        "click_map": {"click_123": "http://example.com"},
        "open_count": 0,
        "click_count": 0,
        "opens_count": 0, # Legacy field
        "clicks": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await db.email_logs.insert_one(log)
    print("Created dummy email log.")

if __name__ == "__main__":
    asyncio.run(create_dummy_data())
