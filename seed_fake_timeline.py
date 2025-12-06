import asyncio
import os
import random
from datetime import datetime, timedelta
from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "mailmate_db")

async def seed_timeline():
    # 1. Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    email_logs = db["email_logs"]
    campaigns = db["campaigns"]

    print("--- Seed Fake Timeline ---")
    
    # 2. Get Campaign ID
    default_id = "6931d5a51df277881aed0995" # User provided ID (might be invalid in real DB if random, but we use it)
    # Let's try to find a valid one if the default doesn't exist, or just ask.
    # Actually, let's list the last 3 campaigns to help the user.
    print("Recent Campaigns:")
    async for c in campaigns.find().sort("created_at", -1).limit(3):
        print(f"- {c['_id']} : {c.get('title', 'Untitled')}")

    campaign_id_input = input(f"\nEnter Campaign ID (default: {default_id}): ").strip()
    campaign_id = campaign_id_input if campaign_id_input else default_id

    try:
        oid = ObjectId(campaign_id)
    except Exception:
        print("❌ Invalid Campaign ID format.")
        return

    campaign = await campaigns.find_one({"_id": oid})
    if not campaign:
        print(f"❌ Campaign {campaign_id} not found.")
        return

    print(f"✅ Found Campaign: {campaign.get('title', 'Untitled')}")
    print("Generating 10 events over the last 5 hours...")

    # 3. Generate Events
    now = datetime.utcnow()
    events_count = 10
    duration_hours = 5
    interval_minutes = (duration_hours * 60) / events_count

    new_opens = 0
    new_clicks = 0

    for i in range(events_count):
        # Calculate time: from 5 hours ago up to now
        # Event 0: 5 hours ago
        # Event 9: near now
        minutes_ago = (events_count - 1 - i) * interval_minutes
        event_time = now - timedelta(minutes=minutes_ago)
        
        # Alternate types or randomize
        is_click = (i % 3 == 0) # Every 3rd event is a click
        event_type = "click" if is_click else "open"

        # Create dummy log
        log_entry = {
            "campaign_id": campaign_id,
            "email": f"fake_user_{i}@example.com",
            "status": "sent",
            "subject": "Fake Timeline Test",
            "created_at": event_time,
            "updated_at": event_time,
            "open_count": 0,
            "click_count": 0,
            "open_events": [],
            "click_events": []
        }

        if event_type == "open":
            log_entry["open_count"] = 1
            log_entry["open_events"] = [event_time] # Storing as datetime object (pymongo handles it)
            new_opens += 1
        else:
            # A click usually implies an open too, but let's just do click for specific testing
            log_entry["click_count"] = 1
            log_entry["click_events"] = [event_time]
            # Let's add an open too so it looks realistic
            log_entry["open_count"] = 1
            log_entry["open_events"] = [event_time]
            new_clicks += 1
            new_opens += 1

        await email_logs.insert_one(log_entry)
        print(f"[{i+1}/{events_count}] Inserted {event_type.upper()} at {event_time.strftime('%H:%M:%S')}")

    # 4. Update Campaign Stats
    print(f"\nUpdating Campaign Stats: +{new_opens} Opens, +{new_clicks} Clicks")
    await campaigns.update_one(
        {"_id": oid},
        {
            "$inc": {
                "stats.opens": new_opens,
                "stats.clicks": new_clicks
            }
        }
    )

    print("✅ Done! Refresh your Analytics page.")

if __name__ == "__main__":
    asyncio.run(seed_timeline())
