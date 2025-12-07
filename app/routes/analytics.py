from fastapi import APIRouter, HTTPException
from bson import ObjectId

from app.db.client import campaigns, email_logs
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/analytics")
async def analytics_summary(id: str): 
    campaign_id = id  # map the query param 'id' to the variable your code expects
    # ensure campaign exists
    try:
        campaign_obj = await campaigns.find_one({"_id": ObjectId(campaign_id)})
    except Exception:
        campaign_obj = None

    if not campaign_obj:
        raise HTTPException(status_code=404, detail="Campaign not found")

    service = AnalyticsService(email_logs_collection=email_logs)
    details = await service.get_details(str(campaign_id))
    return details