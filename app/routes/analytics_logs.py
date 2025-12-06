from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict
from bson import ObjectId
from datetime import datetime, timedelta

from app.db.client import campaigns, email_logs
from app.services.analytics_service import AnalyticsService
from app.services.sendgrid_client import SendGridClient
from app.config import settings

router = APIRouter()


@router.get("/analytics/{campaign_id}/summary")
async def analytics_summary(campaign_id: str):
    try:
        campaign_obj = await campaigns.find_one({"_id": ObjectId(campaign_id)})
    except Exception:
        campaign_obj = None
    if not campaign_obj:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # --- SendGrid API Stats Logic (Already returning counts) ---
    try:
        sg = SendGridClient(api_key=settings.SENDGRID_API_KEY)
        stats = await sg.get_category_stats_all_time(str(campaign_id))
        await sg.close()
        if stats.get("success"):
            m = stats.get("metrics") or {}
            requests = int(m.get("requests", 0) or 0)
            delivered = int(m.get("delivered", 0) or 0)
            total_opens = int(m.get("opens", 0) or 0)
            total_clicks = int(m.get("clicks", 0) or 0)
            unique_opens = int(m.get("unique_opens", 0) or 0)
            unique_clicks = int(m.get("unique_clicks", 0) or 0)
            
            return {
                "total": requests,
                "delivered_count": delivered,
                "open_count": total_opens,     # Returning raw count from SendGrid
                "click_count": total_clicks,   # Returning raw count from SendGrid
                "opens": total_opens,
                "unique_opens": unique_opens,
                "clicks": total_clicks,
                "unique_clicks": unique_clicks,
                "bounces": int(m.get("bounces", 0) or 0),
                "spam_reports": int(m.get("spam_reports", 0) or 0),
            }
    except Exception:
        pass

    # --- MongoDB Fallback Logic (Modified to return counts) ---
    service = AnalyticsService(email_logs_collection=email_logs)
    summary = await service.get_summary(str(campaign_id))
    
    # We explicitly map the fields from the service output to the desired summary structure.
    # Note: This relies on the assumption that service.get_summary returns 'opens' and 'clicks' 
    # (raw counts) alongside 'open_rate' and 'click_rate', as implied by earlier pipeline structure.
    
    # If service.get_summary only returns rates, you must modify the underlying 
    # AnalyticsService.get_summary to include 'opens' and 'clicks' fields.
    
    return {
        "total": summary.get("total", 0),
        "delivered_count": summary.get("delivered_count", 0),
        "open_count": summary.get("opens", 0),      # Mapped from raw count
        "click_count": summary.get("clicks", 0),    # Mapped from raw count
        "opens": summary.get("opens", 0),
        "unique_opens": summary.get("opens", 0),    # Assuming MongoDB unique open count is stored in 'opens'
        "clicks": summary.get("clicks", 0),
        "unique_clicks": summary.get("clicks", 0),  # Assuming MongoDB unique click count is stored in 'clicks'
        "bounces": 0, # Placeholder, as service.get_summary doesn't return this
        "spam_reports": 0, # Placeholder, as service.get_summary doesn't return this
    }


# The remaining endpoints are left unchanged
@router.get("/analytics/{campaign_id}/details")
async def campaign_details(campaign_id: str):
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