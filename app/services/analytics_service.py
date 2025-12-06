"""Analytics service: computes campaign-level summary, logs, and detailed metrics."""
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import importlib
from datetime import datetime


class AnalyticsService:
    def __init__(
        self,
        mongo_client: Optional[AsyncIOMotorClient] = None,
        email_logs_collection: Optional[AsyncIOMotorCollection] = None,
    ):
        if email_logs_collection is not None:
            self.email_logs = email_logs_collection
        else:
            if not mongo_client:
                # import settings lazily to avoid module import-time dependency
                try:
                    cfg = importlib.import_module('app.config')
                    mongo_client = AsyncIOMotorClient(getattr(cfg.settings, "MONGO_URI"))
                except Exception:
                    raise RuntimeError("No mongo_client provided and failed to load settings.MONGO_URI")
            self.email_logs = mongo_client.get_default_database().get_collection("email_logs")

    async def get_summary(self, campaign_id: str) -> Dict[str, Any]:
        """Return aggregated summary for a campaign with both total and unique counts"""
        pipeline = [
            {"$match": {"campaign_id": campaign_id}},
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "delivered": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$or": [
                                        {"$in": ["$status", ["sent", "delivered", "accepted"]]},
                                        {"$and": [{"$gte": ["$sendgrid_status", 200]}, {"$lt": ["$sendgrid_status", 300]}]}
                                    ]
                                },
                                1,
                                0,
                            ]
                        }
                    },
                    # Total opens (sum of all open_count)
                    "total_opens": {
                        "$sum": {"$toInt": {"$ifNull": ["$open_count", 0]}}
                    },
                    # Unique opens (count of recipients who opened at least once)
                    "unique_opens": {
                        "$sum": {
                            "$cond": [
                                {"$gt": [{"$toInt": {"$ifNull": ["$open_count", 0]}}, 0]},
                                1,
                                0
                            ]
                        }
                    },
                    # Total clicks (sum of all click_count)
                    "total_clicks": {
                        "$sum": {"$toInt": {"$ifNull": ["$click_count", 0]}}
                    },
                    # Unique clicks (count of recipients who clicked at least once)
                    "unique_clicks": {
                        "$sum": {
                            "$cond": [
                                {"$gt": [{"$toInt": {"$ifNull": ["$click_count", 0]}}, 0]},
                                1,
                                0
                            ]
                        }
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "total": 1,
                    "delivered": 1,
                    "total_opens": 1,
                    "unique_opens": 1,
                    "total_clicks": 1,
                    "unique_clicks": 1
                }
            }
        ]

        cursor = self.email_logs.aggregate(pipeline, allowDiskUse=False)
        result = await cursor.to_list(length=1)
        if not result:
            return {
                "total": 0,
                "delivered_count": 0,
                "total_opens": 0,
                "unique_opens": 0,
                "total_clicks": 0,
                "unique_clicks": 0
            }

        row = result[0]
        return {
            "total": int(row.get("total", 0)),
            "delivered_count": int(row.get("delivered", 0)),
            "total_opens": int(row.get("total_opens", 0)),
            "unique_opens": int(row.get("unique_opens", 0)),
            "total_clicks": int(row.get("total_clicks", 0)),
            "unique_clicks": int(row.get("unique_clicks", 0))
        }

    async def get_logs(self, campaign_id: str, limit: int = 50, after: Optional[str] = None) -> Dict[str, Any]:
        """Return logs for a campaign. Pagination supports `after` ISO timestamp or cursor (created_at).

        - `limit` controls page size (max clamp to 500)
        - `after` if provided should be an ISO timestamp; returns documents with created_at < after (for reverse pagination)
        """
        limit = max(1, min(limit, 500))
        filter_q = {"campaign_id": campaign_id}
        if after:
            try:
                after_dt = datetime.fromisoformat(after)
                filter_q["created_at"] = {"$lt": after_dt}
            except Exception:
                pass

        projection = {"sendgrid_body": 0}
        # Ensure we fetch event arrays if they exist
        # projection is inclusive or exclusive. If we exclude one field, others are included by default.
        # But here we are excluding sendgrid_body.
        # So open_events and click_events will be included by default.
        # No change needed here actually, unless we want to be explicit.
        # Let's just leave it as is, since excluding one field includes all others.
        
        cursor = self.email_logs.find(filter_q, projection=projection).sort("created_at", -1).limit(limit)
        items = await cursor.to_list(length=limit)

        # Convert ObjectId to string for JSON serialization
        for item in items:
            if "_id" in item:
                item["_id"] = str(item["_id"])

        next_cursor = None
        if items:
            last = items[-1]
            ca = last.get("created_at")
            if isinstance(ca, datetime):
                next_cursor = ca.isoformat()

        return {"items": items, "limit": limit, "next_cursor": next_cursor}

    async def get_details(self, campaign_id: str) -> Dict[str, Any]:
        """Return a detailed summary for the campaign including delivered/failed counts,
        first/last send timestamps, average attempts and basic status breakdown.
        """
        pipeline = [
            {"$match": {"campaign_id": campaign_id}},
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "delivered": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$or": [
                                        {"$in": ["$status", ["sent", "delivered", "accepted"]]},
                                        {"$and": [{"$gte": ["$sendgrid_status", 200]}, {"$lt": ["$sendgrid_status", 300]}]}
                                    ]
                                },
                                1,
                                0,
                            ]
                        }
                    },
                    "failed": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$or": [
                                        {"$in": ["$status", ["failed", "bounced", "rejected"]]},
                                        {"$and": [{"$gte": ["$sendgrid_status", 400]}, {"$lt": ["$sendgrid_status", 600]}]}
                                    ]
                                },
                                1,
                                0
                            ]
                        }
                    },
                    "first_sent": {"$min": "$created_at"},
                    "last_sent": {"$max": "$created_at"},
                    "avg_attempts": {"$avg": {"$ifNull": ["$attempts", 0]}},
                    "status_list": {"$push": "$status"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "total": 1,
                    "delivered": 1,
                    "failed": 1,
                    "first_sent": 1,
                    "last_sent": 1,
                    "avg_attempts": 1,
                    "status_list": 1
                }
            }
        ]

        cursor = self.email_logs.aggregate(pipeline, allowDiskUse=False)
        rows = await cursor.to_list(length=1)
        if not rows:
            return {
                "total": 0,
                "delivered_count": 0,
                "failed_delivery": 0,
                "first_sent": None,
                "last_sent": None,
                "avg_attempts": 0.0,
                "status_breakdown": {}
            }

        row = rows[0]

        # build a simple status breakdown map
        status_map: Dict[str, int] = {}
        for s in row.get("status_list", []):
            status_map[s] = status_map.get(s, 0) + 1

        first_sent = row.get("first_sent")
        last_sent = row.get("last_sent")
        if isinstance(first_sent, datetime):
            first_sent = first_sent.isoformat()
        if isinstance(last_sent, datetime):
            last_sent = last_sent.isoformat()

        return {
            "total": int(row.get("total", 0)),
            "delivered_count": int(row.get("delivered", 0)),
            "failed_delivery": int(row.get("failed", 0)),
            "first_sent": first_sent,
            "last_sent": last_sent,
            "avg_attempts": float(row.get("avg_attempts", 0.0)),
            "status_breakdown": status_map
        }