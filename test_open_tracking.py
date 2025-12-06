"""
Test open tracking with sample webhook event
"""
import asyncio
import httpx
from datetime import datetime

WEBHOOK_URL = "http://localhost:8000/sendgrid/webhook"

async def test_open_event():
    print("="*70)
    print("🧪 TESTING OPEN EVENT TRACKING")
    print("="*70)
    
    # Sample open event from SendGrid
    open_event = [{
        "email": "test-open@example.com",
        "timestamp": int(datetime.utcnow().timestamp()),
        "event": "open",
        "campaign_id": "692199d179573e6ea8f606a0",  # Your actual campaign ID
        "sg_message_id": "test.filter.sendgrid.net",
        "useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "ip": "192.168.1.1",
        "category": ["692199d179573e6ea8f606a0"]
    }]
    
    print(f"\n📤 Sending open event for: test-open@example.com")
    print(f"📋 Campaign ID: 692199d179573e6ea8f606a0\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                WEBHOOK_URL,
                json=open_event,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"✅ Status: {response.status_code}")
            print(f"📝 Response: {response.text}\n")
            
            if response.status_code == 200:
                print("=" * 70)
                print("✅ Open event sent successfully!")
                print("=" * 70)
                print("\n🔍 Now checking database...")
                
                # Verify in database
                from motor.motor_asyncio import AsyncIOMotorClient
                from dotenv import load_dotenv
                import os
                
                load_dotenv()
                client_db = AsyncIOMotorClient(os.getenv("MONGO_URI"))
                db = client_db.get_default_database()
                email_logs = db.get_collection("email_logs")
                
                log = await email_logs.find_one({
                    "email": "test-open@example.com",
                    "campaign_id": "692199d179573e6ea8f606a0"
                })
                
                if log:
                    print(f"\n✅ Found log entry:")
                    print(f"   Email: {log.get('email')}")
                    print(f"   Campaign: {log.get('campaign_id')}")
                    print(f"   Open Count: {log.get('open_count', 0)}")
                    print(f"   Click Count: {log.get('click_count', 0)}")
                    print(f"   Open Events: {len(log.get('open_events', []))} events")
                    
                    if log.get('open_count', 0) > 0:
                        print("\n✅✅ SUCCESS! Open count is being tracked!")
                    else:
                        print("\n⚠️  Open count is still 0")
                else:
                    print("\n❌ No log entry found")
                
                client_db.close()
            else:
                print(f"❌ ERROR: Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_open_event())
