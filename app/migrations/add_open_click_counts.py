"""
Migration script to add open_count and click_count fields to email_logs collection.
This ensures all existing email log documents have these tracking fields initialized.
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/mailmate")


async def migrate_email_logs():
    """
    Add open_count, click_count, open_events, and click_events fields to all email_logs
    that don't have them.
    """
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_default_database()
    email_logs = db.get_collection("email_logs")

    print("Starting migration: Adding open_count and click_count to email_logs...")

    # Find all documents missing open_count or click_count
    query = {
        "$or": [
            {"open_count": {"$exists": False}},
            {"click_count": {"$exists": False}},
            {"open_events": {"$exists": False}},
            {"click_events": {"$exists": False}}
        ]
    }

    count = await email_logs.count_documents(query)
    print(f"Found {count} documents to update")

    if count == 0:
        print("✅ All email logs already have tracking fields!")
        client.close()
        return

    # Update all documents to add missing fields
    update_doc = {
        "$set": {
            "updated_at": None  # Will be set to current time for modified docs
        },
        "$setOnInsert": {
            "open_count": 0,
            "click_count": 0,
            "open_events": [],
            "click_events": []
        }
    }

    # Use update_many with upsert-like behavior
    result = await email_logs.update_many(
        query,
        [
            {
                "$set": {
                    "open_count": {"$ifNull": ["$open_count", 0]},
                    "click_count": {"$ifNull": ["$click_count", 0]},
                    "open_events": {"$ifNull": ["$open_events", []]},
                    "click_events": {"$ifNull": ["$click_events", []]},
                    "updated_at": "$$NOW"
                }
            }
        ]
    )

    print(f"✅ Migration complete!")
    print(f"   - Matched: {result.matched_count}")
    print(f"   - Modified: {result.modified_count}")

    # Verify the migration
    remaining = await email_logs.count_documents(query)
    print(f"   - Remaining documents without fields: {remaining}")

    # Show sample document
    sample = await email_logs.find_one()
    if sample:
        print("\n📋 Sample email_log document structure:")
        print(f"   - email: {sample.get('email')}")
        print(f"   - campaign_id: {sample.get('campaign_id')}")
        print(f"   - status: {sample.get('status')}")
        print(f"   - open_count: {sample.get('open_count')}")
        print(f"   - click_count: {sample.get('click_count')}")
        print(f"   - open_events: {len(sample.get('open_events', []))} events")
        print(f"   - click_events: {len(sample.get('click_events', []))} events")

    client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Email Logs Migration - Add Open/Click Tracking Fields")
    print("=" * 60)
    asyncio.run(migrate_email_logs())
