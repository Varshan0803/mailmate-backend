"""
Comprehensive webhook diagnosis script
Checks every step of the webhook flow
"""
import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

async def diagnose_complete_flow():
    print("\n" + "="*70)
    print("🔍 COMPLETE WEBHOOK FLOW DIAGNOSIS")
    print("="*70)
    
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_default_database()
    email_logs = db.get_collection("email_logs")
    
    # Step 1: Check recent emails sent
    print("\n📧 STEP 1: Recent Emails Sent")
    print("-"*70)
    recent_count = await email_logs.count_documents({
        "created_at": {"$gte": datetime.utcnow() - timedelta(hours=24)}
    })
    print(f"Emails sent in last 24h: {recent_count}")
    
    if recent_count == 0:
        print("⚠️  No emails sent recently. Send a test email first!")
        client.close()
        return
    
    # Get sample recent email
    sample = await email_logs.find_one(
        {"created_at": {"$gte": datetime.utcnow() - timedelta(hours=24)}},
        sort=[("created_at", -1)]
    )
    
    sample_email = sample.get('email')
    sample_campaign = sample.get('campaign_id')
    
    print(f"Sample: {sample_email}")
    print(f"Campaign: {sample_campaign}")
    print(f"Status: {sample.get('status')}")
    print(f"Open Count: {sample.get('open_count', 0)}")
    print(f"Click Count: {sample.get('click_count', 0)}")
    
    # Step 2: Check if webhook endpoint is reachable
    print("\n🌐 STEP 2: Webhook Endpoint Reachability")
    print("-"*70)
    
    local_url = "http://localhost:8000/sendgrid/webhook"
    ngrok_url = "https://lifelike-rotatively-jessi.ngrok-free.dev/sendgrid/webhook"
    
    # Test local
    try:
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            test_payload = [{
                "event": "open",
                "email": "test@example.com",
                "timestamp": int(datetime.utcnow().timestamp()),
                "campaign_id": "test-diagnosis"
            }]
            resp = await http_client.post(local_url, json=test_payload)
            print(f"✅ Local endpoint: REACHABLE (status {resp.status_code})")
    except Exception as e:
        print(f"❌ Local endpoint: UNREACHABLE ({e})")
    
    # Test ngrok
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            test_payload = [{
                "event": "open",
                "email": "test-ngrok@example.com",
                "timestamp": int(datetime.utcnow().timestamp()),
                "campaign_id": "test-diagnosis-ngrok"
            }]
            resp = await http_client.post(ngrok_url, json=test_payload)
            print(f"✅ Ngrok endpoint: REACHABLE (status {resp.status_code})")
    except Exception as e:
        print(f"❌ Ngrok endpoint: UNREACHABLE ({e})")
    
    # Step 3: Check if test events created logs
    print("\n🧪 STEP 3: Test Event Processing")
    print("-"*70)
    
    test_log = await email_logs.find_one({"campaign_id": "test-diagnosis"})
    if test_log:
        print(f"✅ Local test event processed")
        print(f"   Open count: {test_log.get('open_count', 0)}")
    else:
        print("❌ Local test event NOT processed")
    
    test_log_ngrok = await email_logs.find_one({"campaign_id": "test-diagnosis-ngrok"})
    if test_log_ngrok:
        print(f"✅ Ngrok test event processed")
        print(f"   Open count: {test_log_ngrok.get('open_count', 0)}")
    else:
        print("❌ Ngrok test event NOT processed")
    
    # Step 4: Check webhook events received
    print("\n📬 STEP 4: Webhook Events Received (Last 24h)")
    print("-"*70)
    
    delivered_count = await email_logs.count_documents({
        "status": "delivered",
        "created_at": {"$gte": datetime.utcnow() - timedelta(hours=24)}
    })
    
    opens_count = await email_logs.count_documents({
        "open_count": {"$gt": 0},
        "created_at": {"$gte": datetime.utcnow() - timedelta(hours=24)}
    })
    
    clicks_count = await email_logs.count_documents({
        "click_count": {"$gt": 0},
        "created_at": {"$gte": datetime.utcnow() - timedelta(hours=24)}
    })
    
    print(f"Delivered events: {delivered_count}")
    print(f"Open events: {opens_count}")
    print(f"Click events: {clicks_count}")
    
    # Step 5: Analysis
    print("\n" + "="*70)
    print("📊 DIAGNOSIS RESULTS")
    print("="*70)
    
    if delivered_count == 0 and recent_count > 0:
        print("\n❌ PROBLEM: No 'delivered' webhooks received")
        print("\n💡 Likely causes:")
        print("   1. SendGrid webhook URL is incorrect or not saved")
        print("   2. ngrok tunnel is down or URL changed")
        print("   3. SendGrid webhook is not enabled")
        print("\n✅ Solutions:")
        print("   • Check SendGrid Event Webhook settings")
        print("   • Verify URL: https://lifelike-rotatively-jessi.ngrok-free.dev/sendgrid/webhook")
        print("   • Test integration button in SendGrid")
        print("   • Check ngrok dashboard: http://127.0.0.1:4040")
    
    elif opens_count == 0 and delivered_count > 0:
        print("\n⚠️  ISSUE: Webhooks arriving but no opens tracked")
        print("\n💡 Possible causes:")
        print("   1. Emails sent BEFORE tracking_settings fix")
        print("   2. Recipients haven't opened emails yet")
        print("   3. Email clients blocking images")
        print("   4. campaign_id mismatch in webhook vs database")
        print("\n✅ Solutions:")
        print("   • Send a NEW email (after the tracking fix)")
        print("   • Open the email and enable images")
        print("   • Wait 30 seconds and check again")
    
    elif opens_count > 0:
        print("\n✅ SUCCESS: Webhooks are working correctly!")
        print(f"   {opens_count} emails have been opened")
        print(f"   {clicks_count} emails have been clicked")
    
    else:
        print("\n⚠️  No data to analyze. Send test emails first.")
    
    # Step 6: Show sample with opens
    if opens_count > 0:
        print("\n" + "="*70)
        print("📧 SAMPLE EMAIL WITH OPENS")
        print("="*70)
        
        opened_email = await email_logs.find_one(
            {"open_count": {"$gt": 0}},
            sort=[("updated_at", -1)]
        )
        
        if opened_email:
            print(f"\nEmail: {opened_email.get('email')}")
            print(f"Campaign: {opened_email.get('campaign_id')}")
            print(f"Open Count: {opened_email.get('open_count', 0)}")
            print(f"Click Count: {opened_email.get('click_count', 0)}")
            print(f"Last Updated: {opened_email.get('updated_at')}")
            
            if opened_email.get('open_events'):
                print(f"\nOpen Events ({len(opened_email.get('open_events', []))}):")
                for idx, evt in enumerate(opened_email.get('open_events', [])[:3], 1):
                    print(f"  {idx}. {evt.get('timestamp')}")
    
    print("\n" + "="*70)
    print("🔗 NEXT STEPS")
    print("="*70)
    print("\n1. Check FastAPI logs for webhook requests:")
    print("   Look for: 🔔 Webhook received from SendGrid")
    print("\n2. Check ngrok dashboard: http://127.0.0.1:4040")
    print("   Should see POST requests from SendGrid IP addresses")
    print("\n3. If no webhooks arriving:")
    print("   • Verify SendGrid Event Webhook URL")
    print("   • Click 'Test Your Integration' in SendGrid")
    print("\n4. If webhooks arriving but not updating:")
    print("   • Check server logs for errors")
    print("   • Verify campaign_id matches in both webhook and database")
    print("="*70 + "\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(diagnose_complete_flow())
