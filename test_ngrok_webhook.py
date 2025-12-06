"""
Test if the webhook endpoint is accessible from ngrok
"""
import httpx
import asyncio
import json
from datetime import datetime

NGROK_URL = "https://lifelike-rotatively-jessi.ngrok-free.dev/sendgrid/webhook"

async def test_ngrok_webhook():
    print("="*70)
    print("🧪 TESTING NGROK WEBHOOK ACCESS")
    print("="*70)
    print(f"\n🔗 Testing URL: {NGROK_URL}\n")
    
    # Sample event
    test_event = [{
        "email": "test@example.com",
        "timestamp": int(datetime.utcnow().timestamp()),
        "event": "open",
        "campaign_id": "692199d179573e6ea8f606a0",
        "sg_message_id": "test.filter.sendgrid.net"
    }]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("📤 Sending test event via ngrok URL...")
            response = await client.post(
                NGROK_URL,
                json=test_event,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"✅ Status Code: {response.status_code}")
            print(f"📝 Response: {response.text[:200]}")
            
            if response.status_code == 200:
                print("\n✅ SUCCESS! Webhook is accessible via ngrok")
            else:
                print(f"\n❌ ERROR: Got status {response.status_code}")
                print(f"Response body: {response.text}")
                
        except httpx.ConnectError as e:
            print(f"\n❌ CONNECTION ERROR: {e}")
            print("\n💡 Possible causes:")
            print("   1. ngrok tunnel is down")
            print("   2. FastAPI server is not running")
            print("   3. Wrong ngrok URL")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_ngrok_webhook())
