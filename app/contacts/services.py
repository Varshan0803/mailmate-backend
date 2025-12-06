# app/contacts/services.py
from typing import List, Optional, Dict, Any
from app.db.client import db
from bson import ObjectId
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorCollection

COL: AsyncIOMotorCollection = db.get_collection("contacts")

async def create_contact(data: Dict) -> Dict:
    doc = {
        "name": data["name"],
        "email": data["email"],
        "segment": data.get("segment"),
        "unsubscribed": False,
        "created_at": datetime.utcnow()
    }
    res = await COL.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc

async def get_contact_by_id(contact_id: str) -> Optional[Dict]:
    doc = await COL.find_one({"_id": ObjectId(contact_id)})
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    return doc

async def get_contact_by_email(email: str) -> Optional[Dict]:
    doc = await COL.find_one({"email": email})
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    return doc

async def update_contact(contact_id: str, data: Dict) -> Optional[Dict]:
    update = {"$set": {}}
    for k in ("name", "email", "segment", "unsubscribed"):
        if k in data and data[k] is not None:
            update["$set"][k] = data[k]
    if not update["$set"]:
        return await get_contact_by_id(contact_id)
    await COL.update_one({"_id": ObjectId(contact_id)}, update)
    return await get_contact_by_id(contact_id)

async def delete_contact(contact_id: str) -> bool:
    res = await COL.delete_one({"_id": ObjectId(contact_id)})
    return res.deleted_count == 1

async def list_contacts(filter_query: Dict = None, skip: int = 0, limit: int = 50) -> List[Dict]:
    filter_query = filter_query or {}
    cursor = COL.find(filter_query).skip(skip).limit(limit).sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        results.append(doc)
    return results

async def get_segment_counts() -> List[Dict]:
    pipeline = [
        {"$group": {"_id": "$segment", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    cursor = COL.aggregate(pipeline)
    results = []
    async for doc in cursor:
        # Handle None/null segments if any exist from before
        segment_name = doc["_id"] if doc["_id"] else "Unsegmented"
        results.append({"segment": segment_name, "count": doc["count"]})
    return results

# Bulk insert rows (assumes rows already validated and normalized)
async def bulk_insert_contacts(rows):
    inserted = 0
    duplicates = 0
    errors = []
    now = datetime.utcnow()

    for r in rows:
        # Check duplicate in DB
        exists = await COL.find_one({"email": r["email"]})
        if exists:
            duplicates += 1
            continue
        
        doc = {
            "name": r["name"],
            "email": r["email"],
            "segment": r.get("segment"),
            "unsubscribed": False,
            "created_at": now
        }

        try:
            await COL.insert_one(doc)
            inserted += 1
        except DuplicateKeyError:
            duplicates += 1
        except Exception as ex:
            errors.append({"email": r["email"], "error": str(ex)})

    return {"inserted": inserted, "duplicates": duplicates, "errors": errors}


# ------------------------------- CSV PARSER (UPDATED EMAIL VALIDATION) -------------------------------

import csv
import io
from app.contacts.utils import normalize_email
from pydantic import BaseModel, EmailStr, ValidationError

# FIX → Pydantic v2 requires validation through a model
class EmailCheck(BaseModel):
    email: EmailStr


async def parse_csv_and_prepare(upload_bytes: bytes):
    text = upload_bytes.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    cleaned_rows = []
    errors = []
    seen_in_file = set()
    
    for i, row in enumerate(reader, start=2):  # row numbers start at 2 (1 = header)
        raw_name = (row.get("name") or "").strip()
        raw_email = row.get("email", "")

        print("RAW EMAIL BYTES:", repr(raw_email))  # DEBUG
        raw_email = normalize_email(raw_email)
        print("CLEANED EMAIL:", repr(raw_email))    # DEBUG

        raw_segment = (row.get("segment") or "general").strip()

        # Skip empty rows
        if not raw_email:
            errors.append({"row": i, "error": "Email missing"})
            continue

        # In-file duplicate check
        if raw_email in seen_in_file:
            errors.append({"row": i, "error": "Duplicate email in CSV", "email": raw_email})
            continue
        seen_in_file.add(raw_email)

        # ---------------- EMAIL VALIDATION FIX ----------------
        try:
            EmailCheck(email=raw_email)
        except ValidationError:
            errors.append({"row": i, "error": "Invalid email", "email": raw_email})
            continue
        # ------------------------------------------------------

        # Clean name (title case optional)
        cleaned_name = " ".join(raw_name.split()).title()

        cleaned_rows.append({
            "name": cleaned_name,
            "email": raw_email,
            "segment": raw_segment,
        })
    
    return {"rows": cleaned_rows, "errors": errors}
