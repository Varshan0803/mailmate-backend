from fastapi import APIRouter, Depends
from app.db.client import db, contacts, campaigns
from app.deps import get_current_user
from typing import List, Dict, Any

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats")
async def get_dashboard_stats(current_user = Depends(get_current_user)):
    """
    Get dashboard statistics:
    - Total Contacts
    - Active Contacts
    - Total Campaigns
    - Recent Campaigns (limit 5)
    """
    
    # 1. Total Contacts
    total_contacts = await contacts.count_documents({})
    print(f"DEBUG: Connected to DB: {db.name}, Found {total_contacts} contacts")
    
    # 2. Active Contacts

    active_contacts = await contacts.count_documents({"unsubscribed": {"$ne": True}})
    
    # 3. Total Campaigns
    total_campaigns = await campaigns.count_documents({})
    print(f"DEBUG: Found {total_campaigns} campaigns")
    
    # 4. Recent Campaigns
    cursor = campaigns.find().sort("created_at", -1).limit(5)
    recent_campaigns = []
    async for campaign in cursor:
        recent_campaigns.append({
            "id": str(campaign["_id"]),
            "title": campaign.get("title") or campaign.get("name", "Untitled"),
            "status": campaign.get("status", "Draft"),
            "created_at": campaign.get("created_at")
        })
        
    return {
        "total_contacts": total_contacts,
        "active_contacts": active_contacts,
        "total_campaigns": total_campaigns,
        "recent_campaigns": recent_campaigns
    }
