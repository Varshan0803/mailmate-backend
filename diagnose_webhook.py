"""
Diagnostic script to check webhook integration
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")


async def diagnose():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_default_database()
    email_logs = db.get_collection("email_logs")
    
    print("\n" + "="*70)
    print("🔍 WEBHOOK INTEGRATION DIAGNOSTICS")
    print("="*70)
    
    # 1. Check recent email logs
    recent_count = await email_logs.count_documents({
        "created_at": {"$gte": datetime.utcnow() - timedelta(hours=1)}
    })
    print(f"\n📧 Emails sent in last hour: {recent_count}")
    
    # 2. Check for delivered events (webhook should update these)
    delivered_count = await email_logs.count_documents({"status": "delivered"})
    print(f"✅ Emails with 'delivered' status: {delivered_count}")
    
    # 3. Check for opens
    opens_count = await email_logs.count_documents({"open_count": {"$gt": 0}})
    print(f"👀 Emails with opens: {opens_count}")
    
    # 4. Check for clicks
    clicks_count = await email_logs.count_documents({"click_count": {"$gt": 0}})
    print(f"🖱️  Emails with clicks: {clicks_count}")
    
    # 5. Get a sample recent log
    print("\n" + "="*70)
    print("📋 SAMPLE RECENT EMAIL LOG")
    print("="*70)
    
    sample = await email_logs.find_one(
        {"created_at": {"$gte": datetime.utcnow() - timedelta(hours=1)}},
        sort=[("created_at", -1)]
    )
    
    if sample:
        print(f"\n📧 Email: {sample.get('email')}")
        print(f"🎯 Campaign ID: {sample.get('campaign_id')}")
        print(f"📊 Status: {sample.get('status')}")
        print(f"👀 Open Count: {sample.get('open_count', 0)}")
        print(f"🖱️  Click Count: {sample.get('click_count', 0)}")
        print(f"📅 Created: {sample.get('created_at')}")
        print(f"📅 Updated: {sample.get('updated_at', 'Not updated yet')}")
        
        if sample.get('delivered_at'):
            print(f"✅ Delivered At: {sample.get('delivered_at')}")
        
        print(f"\n🔑 Has open_events field: {'open_events' in sample}")
        print(f"🔑 Has click_events field: {'click_events' in sample}")
        
        if 'open_events' in sample:
            print(f"📊 Open events count: {len(sample.get('open_events', []))}")
        if 'click_events' in sample:
            print(f"📊 Click events count: {len(sample.get('click_events', []))}")
    
    print("\n" + "="*70)
    print("💡 TROUBLESHOOTING")
    print("="*70)
    
    if delivered_count == 0 and recent_count > 0:
        print("\n⚠️  WARNING: No 'delivered' status found!")
        print("   This means webhooks from SendGrid are NOT arriving.")
        print("\n   Possible causes:")
        print("   1. SendGrid webhook URL is incorrect")
        print("   2. ngrok tunnel is down")
        print("   3. FastAPI server is not running")
        print("   4. SendGrid webhook is not saved/enabled")
        print("\n   ✅ Action: Check SendGrid Event Webhook settings")
        print("   ✅ URL should be: https://your-ngrok-url.ngrok-free.dev/sendgrid/webhook")
    
    if opens_count == 0 and delivered_count > 0:
        print("\n⚠️  Webhooks are arriving, but no opens tracked yet.")
        print("   This is normal if:")
        print("   - Recipients haven't opened the emails yet")
        print("   - Email was just sent recently")
        print("\n   ✅ Action: Open one of the sent emails and wait 5-10 seconds")
    
    if opens_count > 0:
        print("\n✅ SUCCESS: Webhooks are working! Opens are being tracked.")
    
    print("\n" + "="*70)
    print("🔗 NEXT STEPS")
    print("="*70)
    print("\n1. Check your FastAPI server logs for webhook requests")
    print("   Look for: POST /sendgrid/webhook")
    print("\n2. Check ngrok dashboard: http://127.0.0.1:4040")
    print("   You should see POST requests from SendGrid")
    print("\n3. Open an email you sent and wait ~10 seconds")
    print("\n4. Run this script again: python diagnose_webhook.py")
    print("="*70 + "\n")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(diagnose())
