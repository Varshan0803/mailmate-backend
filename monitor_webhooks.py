"""
Real-time webhook activity monitor
Watches email_logs collection for recent updates
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/mailmate")


async def monitor_webhooks(duration_seconds=60):
    """Monitor webhook activity for specified duration"""
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_default_database()
    email_logs = db.get_collection("email_logs")
    
    print("=" * 70)
    print("📡 WEBHOOK ACTIVITY MONITOR")
    print("=" * 70)
    print(f"Monitoring for {duration_seconds} seconds...")
    print("Watching for open/click events in real-time\n")
    print("Press Ctrl+C to stop early\n")
    
    # Get initial state
    start_time = datetime.utcnow()
    cutoff_time = start_time - timedelta(minutes=5)
    
    initial_opens = await email_logs.count_documents({"open_count": {"$gt": 0}})
    initial_clicks = await email_logs.count_documents({"click_count": {"$gt": 0}})
    
    print(f"📊 Initial State:")
    print(f"   Emails with opens: {initial_opens}")
    print(f"   Emails with clicks: {initial_clicks}")
    print("\n" + "-" * 70)
    print("🔴 LIVE (watching for new events)...")
    print("-" * 70 + "\n")
    
    try:
        elapsed = 0
        last_check = datetime.utcnow()
        
        while elapsed < duration_seconds:
            await asyncio.sleep(2)  # Check every 2 seconds
            
            current_time = datetime.utcnow()
            elapsed = (current_time - start_time).total_seconds()
            
            # Find recently updated logs (last 10 seconds)
            recent_cutoff = current_time - timedelta(seconds=10)
            
            recent_updates = await email_logs.find({
                "updated_at": {"$gte": recent_cutoff}
            }).sort("updated_at", -1).to_list(length=10)
            
            for log in recent_updates:
                update_time = log.get("updated_at")
                if update_time and update_time > last_check:
                    email = log.get("email", "unknown")
                    campaign_id = log.get("campaign_id", "unknown")
                    open_count = log.get("open_count", 0)
                    click_count = log.get("click_count", 0)
                    
                    timestamp = update_time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] 📧 {email[:30]}")
                    print(f"           Campaign: {campaign_id}")
                    print(f"           Opens: {open_count} | Clicks: {click_count}")
                    print()
            
            last_check = current_time
            
            # Show progress every 10 seconds
            if int(elapsed) % 10 == 0 and elapsed > 0:
                current_opens = await email_logs.count_documents({"open_count": {"$gt": 0}})
                current_clicks = await email_logs.count_documents({"click_count": {"$gt": 0}})
                new_opens = current_opens - initial_opens
                new_clicks = current_clicks - initial_clicks
                
                print(f"⏱️  {int(elapsed)}s elapsed | New opens: +{new_opens} | New clicks: +{new_clicks}")
                print()
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
    
    # Final summary
    final_opens = await email_logs.count_documents({"open_count": {"$gt": 0}})
    final_clicks = await email_logs.count_documents({"click_count": {"$gt": 0}})
    
    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)
    print(f"Duration: {elapsed:.0f} seconds")
    print(f"Initial opens: {initial_opens} → Final: {final_opens} (Change: +{final_opens - initial_opens})")
    print(f"Initial clicks: {initial_clicks} → Final: {final_clicks} (Change: +{final_clicks - initial_clicks})")
    print("=" * 70 + "\n")
    
    client.close()


async def show_recent_activity():
    """Show recent webhook activity (last 24 hours)"""
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_default_database()
    email_logs = db.get_collection("email_logs")
    
    print("=" * 70)
    print("📊 RECENT WEBHOOK ACTIVITY (Last 24 Hours)")
    print("=" * 70 + "\n")
    
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    # Find logs updated in last 24 hours
    recent_logs = await email_logs.find({
        "updated_at": {"$gte": cutoff},
        "$or": [
            {"open_count": {"$gt": 0}},
            {"click_count": {"$gt": 0}}
        ]
    }).sort("updated_at", -1).limit(20).to_list(length=20)
    
    if not recent_logs:
        print("❌ No recent webhook activity found in the last 24 hours")
        print("\nTo test the webhook:")
        print("   python test_webhook.py")
    else:
        print(f"Found {len(recent_logs)} recently tracked emails:\n")
        
        for idx, log in enumerate(recent_logs, 1):
            email = log.get("email", "unknown")
            campaign_id = log.get("campaign_id", "unknown")[:20]
            open_count = log.get("open_count", 0)
            click_count = log.get("click_count", 0)
            updated_at = log.get("updated_at")
            
            time_str = updated_at.strftime("%Y-%m-%d %H:%M:%S") if updated_at else "N/A"
            
            print(f"{idx}. {email[:40]}")
            print(f"   Campaign: {campaign_id}...")
            print(f"   Opens: {open_count} | Clicks: {click_count}")
            print(f"   Last Updated: {time_str}")
            print()
    
    print("=" * 70 + "\n")
    client.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "recent":
            asyncio.run(show_recent_activity())
        elif sys.argv[1] == "monitor":
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            asyncio.run(monitor_webhooks(duration))
        else:
            print("Usage:")
            print("  python monitor_webhooks.py recent          # Show recent activity")
            print("  python monitor_webhooks.py monitor [secs]  # Monitor live (default: 60s)")
    else:
        # Default: show recent activity
        asyncio.run(show_recent_activity())
