"""
Test script to verify SendGrid webhook integration
Sends sample webhook events to your local endpoint
"""
import asyncio
import httpx
import json
from datetime import datetime

WEBHOOK_URL = "http://localhost:8000/sendgrid/webhook"

# Sample webhook events
SAMPLE_EVENTS = [
    # Delivered event
    {
        "email": "test-webhook@example.com",
        "timestamp": int(datetime.utcnow().timestamp()),
        "event": "delivered",
        "campaign_id": "test-campaign-webhook",
        "sg_message_id": "test123.filter0001.sendgrid.net",
        "smtp-id": "<test123@sendgrid.net>",
        "category": ["test-campaign-webhook"],
        "response": "250 OK"
    },
    # Open event
    {
        "email": "test-webhook@example.com",
        "timestamp": int(datetime.utcnow().timestamp()) + 10,
        "event": "open",
        "campaign_id": "test-campaign-webhook",
        "sg_message_id": "test123.filter0001.sendgrid.net",
        "useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "ip": "192.168.1.1",
        "category": ["test-campaign-webhook"]
    },
    # Click event
    {
        "email": "test-webhook@example.com",
        "timestamp": int(datetime.utcnow().timestamp()) + 20,
        "event": "click",
        "campaign_id": "test-campaign-webhook",
        "sg_message_id": "test123.filter0001.sendgrid.net",
        "url": "https://example.com/test-link",
        "useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "ip": "192.168.1.1",
        "category": ["test-campaign-webhook"]
    },
    # Another open event (to test count increment)
    {
        "email": "test-webhook@example.com",
        "timestamp": int(datetime.utcnow().timestamp()) + 30,
        "event": "open",
        "campaign_id": "test-campaign-webhook",
        "sg_message_id": "test123.filter0001.sendgrid.net",
        "useragent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)",
        "ip": "192.168.1.2",
        "category": ["test-campaign-webhook"]
    },
    # Another click event
    {
        "email": "test-webhook@example.com",
        "timestamp": int(datetime.utcnow().timestamp()) + 40,
        "event": "click",
        "campaign_id": "test-campaign-webhook",
        "sg_message_id": "test123.filter0001.sendgrid.net",
        "url": "https://example.com/another-link",
        "useragent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)",
        "ip": "192.168.1.2",
        "category": ["test-campaign-webhook"]
    },
    # Bounce event
    {
        "email": "bounce@example.com",
        "timestamp": int(datetime.utcnow().timestamp()) + 50,
        "event": "bounce",
        "campaign_id": "test-campaign-webhook",
        "sg_message_id": "test456.filter0001.sendgrid.net",
        "reason": "550 5.1.1 The email account does not exist",
        "type": "bounce",
        "category": ["test-campaign-webhook"]
    }
]


async def test_webhook():
    """Send test events to the webhook endpoint"""
    print("=" * 70)
    print("SENDGRID WEBHOOK TEST")
    print("=" * 70)
    print(f"\n🎯 Target: {WEBHOOK_URL}")
    print(f"📧 Sending {len(SAMPLE_EVENTS)} test events...\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Send all events as a batch (SendGrid sends arrays)
            response = await client.post(
                WEBHOOK_URL,
                json=SAMPLE_EVENTS,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"✅ Response Status: {response.status_code}")
            print(f"📝 Response Body: {response.text}\n")
            
            if response.status_code == 200:
                print("=" * 70)
                print("SUCCESS! Webhook processed events")
                print("=" * 70)
                print("\n📊 Events sent:")
                for idx, event in enumerate(SAMPLE_EVENTS, 1):
                    print(f"  {idx}. {event['event']:12} - {event['email']}")
                
                print("\n🔍 Next steps:")
                print("  1. Check your email_logs collection for 'test-webhook@example.com'")
                print("  2. Verify open_count = 2")
                print("  3. Verify click_count = 2")
                print("  4. Check open_events and click_events arrays")
                print("\n  Run: python verify_email_logs.py")
                
            else:
                print("❌ Webhook returned non-200 status")
                print(f"Response: {response.text}")
                
        except httpx.ConnectError:
            print("❌ ERROR: Could not connect to webhook endpoint")
            print("\n💡 Make sure your FastAPI server is running:")
            print("   uvicorn app.main:app --reload --port 8000")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")


async def verify_database():
    """Check if the test events were recorded in the database"""
    print("\n" + "=" * 70)
    print("VERIFYING DATABASE UPDATES")
    print("=" * 70)
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/mailmate")
        
        client = AsyncIOMotorClient(MONGO_URI)
        db = client.get_default_database()
        email_logs = db.get_collection("email_logs")
        
        # Find the test email log
        test_log = await email_logs.find_one({
            "email": "test-webhook@example.com",
            "campaign_id": "test-campaign-webhook"
        })
        
        if test_log:
            print("\n✅ Found test email log in database!")
            print(f"\n📧 Email: {test_log.get('email')}")
            print(f"🎯 Campaign: {test_log.get('campaign_id')}")
            print(f"📊 Status: {test_log.get('status')}")
            print(f"👀 Open Count: {test_log.get('open_count', 0)}")
            print(f"🖱️  Click Count: {test_log.get('click_count', 0)}")
            print(f"📅 Open Events: {len(test_log.get('open_events', []))} events")
            print(f"📅 Click Events: {len(test_log.get('click_events', []))} events")
            
            if test_log.get('open_count', 0) == 2:
                print("\n✅ PASS: Open count is correct (2)")
            else:
                print(f"\n⚠️  WARNING: Expected open_count=2, got {test_log.get('open_count', 0)}")
            
            if test_log.get('click_count', 0) == 2:
                print("✅ PASS: Click count is correct (2)")
            else:
                print(f"⚠️  WARNING: Expected click_count=2, got {test_log.get('click_count', 0)}")
                
        else:
            print("\n❌ Test email log not found in database")
            print("The webhook might not be processing events correctly.")
            
        # Check for bounce event
        bounce_log = await email_logs.find_one({
            "email": "bounce@example.com",
            "campaign_id": "test-campaign-webhook"
        })
        
        if bounce_log:
            print(f"\n✅ Bounce event recorded:")
            print(f"   Status: {bounce_log.get('status')}")
            print(f"   Bounced at: {bounce_log.get('bounced_at')}")
        
        client.close()
        
    except Exception as e:
        print(f"\n⚠️  Could not verify database: {e}")
        print("You can manually check using: python verify_email_logs.py")


async def main():
    # Send test events
    await test_webhook()
    
    # Wait a moment for processing
    await asyncio.sleep(1)
    
    # Verify database
    await verify_database()
    
    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
