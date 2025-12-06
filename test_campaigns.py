import urllib.request
import urllib.parse
import json

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "admin@example.com"
PASSWORD = "securePassword123"

def test_campaigns():
    # 1. Login
    print(f"Logging in as {EMAIL}...")
    login_payload = json.dumps({"email": EMAIL, "password": PASSWORD}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/auth/login", data=login_payload, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            token = data["access_token"]
            print(f"Got Token")
    except Exception as e:
        print(f"Login Failed: {e}")
        return

    # 2. Access Campaigns
    print("\nAccessing /campaigns/...")
    req = urllib.request.Request(f"{BASE_URL}/campaigns/")
    req.add_header("Authorization", f"Bearer {token}")
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Campaigns Status: {response.getcode()}")
            data = json.loads(response.read().decode('utf-8'))
            print(f"Campaigns Count: {len(data)}")
            print(f"First Campaign: {data[0] if data else 'None'}")
    except urllib.error.HTTPError as e:
        print(f"Campaigns Failed: {e.code} {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Campaigns Exception: {e}")

if __name__ == "__main__":
    test_campaigns()
