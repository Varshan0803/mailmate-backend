from fastapi import APIRouter, Depends, HTTPException
from app.schemas.campaign_schema import CampaignCreate, CampaignOut
from app.models.campaign import Campaign
from app.db.client import db
from app.deps import get_current_user
from datetime import datetime

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

@router.post("/create", response_model=CampaignOut)
async def create_campaign(campaign: CampaignCreate, current_user = Depends(get_current_user)):
    """
    Create a new campaign.
    Status can be 'Draft' or 'Pending' (for Send Now).
    """
    campaign_dict = campaign.dict()
    campaign_dict["created_by"] = str(current_user["_id"])
    campaign_dict["created_at"] = datetime.utcnow()
    
    # Initialize stats for analytics
    campaign_dict["stats"] = {
        "sent": 0,
        "opens": 0,
        "clicks": 0,
        "bounces": 0,
        "spam_reports": 0,
        "unsubscribes": 0
    }
    
    # Insert into database
    result = await db.get_collection("campaigns").insert_one(campaign_dict)
    
    # Return created campaign
    campaign_dict["id"] = str(result.inserted_id)
    
    # Trigger Celery task if Pending (Send Now)
    if campaign_dict.get("status") == "Pending":
        from app.campaigns.tasks import send_campaign_task
        send_campaign_task.delay(str(result.inserted_id))
        
    return campaign_dict
