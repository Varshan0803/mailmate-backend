import asyncio
import sys
import os
import httpx

# Ensure we can import from app
sys.path.append(os.getcwd())

async def test_dashboard_stats():
    print("Testing GET /api/dashboard/stats ...")
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        try:
            # Login first
            login_res = await client.post("/auth/login", json={"email": "admin@mailmate.com", "password": "securePassword123"})
            if login_res.status_code != 200:
                print(f"Login failed: {login_res.text}")
                return

            token = login_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            response = await client.get("/dashboard/stats", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Success! Stats received:")
                print(f"Total Contacts: {data.get('total_contacts')}")
                print(f"Active Contacts: {data.get('active_contacts')}")
                print(f"Total Campaigns: {data.get('total_campaigns')}")
                print(f"Recent Campaigns: {len(data.get('recent_campaigns', []))}")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_dashboard_stats())
