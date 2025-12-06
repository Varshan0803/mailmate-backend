import asyncio
import os
import motor.motor_asyncio

# Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "mailmate_db")

async def fix_database_stats():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    print("--- Starting Database Migration: Fix Campaign Stats ---")
    
    # Define default stats
    default_stats = {
        "sent": 0,
        "opens": 0,
        "clicks": 0,
        "bounces": 0,
        "spam_reports": 0,
        "unsubscribes": 0
    }
    
    # Find campaigns where 'stats' field does not exist
    query = {"stats": {"$exists": False}}
    cursor = db.campaigns.find(query)
    
    count = 0
    async for campaign in cursor:
        await db.campaigns.update_one(
            {"_id": campaign["_id"]},
            {"$set": {"stats": default_stats}}
        )
        count += 1
        print(f"Fixed campaign: {campaign.get('title', campaign.get('name', 'Untitled'))} ({campaign['_id']})")
        
    print(f"--- Migration Complete. Fixed {count} campaigns. ---")

if __name__ == "__main__":
    asyncio.run(fix_database_stats())
