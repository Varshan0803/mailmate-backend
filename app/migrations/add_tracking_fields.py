# migrations/add_tracking_fields.py
import os
from uuid import uuid4
from pymongo import MongoClient, ASCENDING
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "mailmate_db")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
email_logs = db["email_logs"]
events = db["events"]

def add_fields():
    cursor = email_logs.find({"tracking_id": {"$exists": False}})
    count = 0
    for doc in cursor:
        tracking_id = uuid4().hex
        email_logs.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "tracking_id": tracking_id,
                "click_map": {},
                "clicks": {},
                "opens_count": doc.get("opens_count", 0),
                "unique_open_keys": []
            }}
        )
        count += 1
    print(f"Updated {count} documents with tracking fields")

def create_indexes():
    # Create indexes
    try:
        email_logs.create_index([("tracking_id", ASCENDING)], unique=True)
    except Exception as e:
        print("Warning creating unique index on tracking_id:", e)
    email_logs.create_index([("campaign_id", ASCENDING)])
    events.create_index([("tracking_id", ASCENDING)])
    events.create_index([("click_id", ASCENDING)])
    events.create_index([("timestamp", ASCENDING)])
    print("Indexes created/ensured")

if __name__ == "__main__":
    add_fields()
    create_indexes()
