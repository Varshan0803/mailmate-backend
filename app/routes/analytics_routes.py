from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Any
from bson import ObjectId
from datetime import datetime, timedelta

from app.db.client import campaigns, email_logs, contacts
from app.services.analytics_service import AnalyticsService
from app.services.sendgrid_client import SendGridClient
from app.config import settings

from app.deps import require_role

router = APIRouter(dependencies=[Depends(require_role("admin"))])


@router.get("/analytics/{campaign_id}/summary")
async def analytics_summary(campaign_id: str):
    # 1) Ensure campaign exists
    try:
        campaign_obj = await campaigns.find_one({"_id": ObjectId(campaign_id)})
    except Exception:
        campaign_obj = None

    if not campaign_obj:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # 2) Compute unsubscribe stats based on campaign segment
    segment = campaign_obj.get("segment")
    unsubscribed_count = 0
    total_contacts = 0
    unsubscribe_rate = 0.0

    if segment:
        # all contacts in this campaign's segment
        total_contacts = await contacts.count_documents({"segment": segment})
        # only unsubscribed contacts
        unsubscribed_count = await contacts.count_documents(
            {"segment": segment, "unsubscribed": True}
        )
        if total_contacts > 0:
            unsubscribe_rate = unsubscribed_count / total_contacts

    # 3) Try SendGrid stats first
    try:
        sg = SendGridClient(api_key=settings.SENDGRID_API_KEY)
        stats = await sg.get_category_stats_all_time(str(campaign_id))
        await sg.close()

        if stats.get("success"):
            m = stats.get("metrics") or {}
            requests = int(m.get("requests", 0) or 0)
            delivered = int(m.get("delivered", 0) or 0)
            opened = int(m.get("unique_opens", 0) or 0)
            clicked = int(m.get("unique_clicks", 0) or 0)
            open_rate = (opened / delivered) if delivered > 0 else 0.0
            click_rate = (clicked / delivered) if delivered > 0 else 0.0

            return {
                "total": requests,
                "delivered_count": delivered,
                "open_rate": round(open_rate, 4),
                "click_rate": round(click_rate, 4),
                "opens": int(m.get("opens", 0) or 0),
                "unique_opens": opened,
                "clicks": int(m.get("clicks", 0) or 0),
                "unique_clicks": clicked,
                "bounces": int(m.get("bounces", 0) or 0),
                "spam_reports": int(m.get("spam_reports", 0) or 0),

                # 🔻 unsubscribe metrics
                "unsubscribed_count": unsubscribed_count,
                "unsubscribe_rate": round(unsubscribe_rate, 4),        # 0–1
                "unsubscribe_percentage": round(unsubscribe_rate * 100, 2),  # 0–100
               
            }
    except Exception:
        # swallow SendGrid errors and fall back to Mongo analytics
        pass

    # 4) MongoDB fallback analytics
    service = AnalyticsService(email_logs_collection=email_logs)
    summary = await service.get_summary(str(campaign_id))

    # Calculate rates from summary data
    delivered = summary.get("delivered_count", 0)
    unique_opens = summary.get("unique_opens", 0)
    unique_clicks = summary.get("unique_clicks", 0)
    
    open_rate = (unique_opens / delivered) if delivered > 0 else 0.0
    click_rate = (unique_clicks / delivered) if delivered > 0 else 0.0

    # merge summary with unsubscribe metrics
    return {
        "open_rate": round(open_rate, 4),
        "click_rate": round(click_rate, 4),
        "opens": summary.get("total_opens", 0),
        "clicks": summary.get("total_clicks", 0),
        "bounces": 0,
        "spam_reports": 0,
        **summary,
        "unsubscribed_count": unsubscribed_count,
        "unsubscribe_rate": round(unsubscribe_rate, 4),
        "unsubscribe_percentage": round(unsubscribe_rate * 100, 2),
    }


@router.get("/analytics/{campaign_id}/logs")
async def analytics_logs(campaign_id: str, limit: int = 50):
    """
    Get recent activity logs for a campaign.
    """
    try:
        service = AnalyticsService(email_logs_collection=email_logs)
        return await service.get_logs(campaign_id, limit=limit)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
