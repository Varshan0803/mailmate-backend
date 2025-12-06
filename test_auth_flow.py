import urllib.request
import urllib.parse
import json

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "admin@example.com"
PASSWORD = "securePassword123"

def test_flow():
    # 1. Login
    print(f"Logging in as {EMAIL}...")
    login_payload = json.dumps({"email": EMAIL, "password": PASSWORD}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/auth/login", data=login_payload, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Login Status: {response.getcode()}")
            data = json.loads(response.read().decode('utf-8'))
            token = data["access_token"]
            print(f"Got Token: {token[:20]}...")
    except urllib.error.HTTPError as e:
        print(f"Login Failed: {e.code} {e.read().decode('utf-8')}")
        return
    except Exception as e:
        print(f"Login Exception: {e}")
        return

    # 2. Access Protected Route
    print("\nAccessing /dashboard/stats...")
    req = urllib.request.Request(f"{BASE_URL}/dashboard/stats")
    req.add_header("Authorization", f"Bearer {token}")
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Stats Status: {response.getcode()}")
            print(f"Stats Response: {response.read().decode('utf-8')}")
    except urllib.error.HTTPError as e:
        print(f"Stats Failed: {e.code} {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Stats Exception: {e}")

if __name__ == "__main__":
    test_flow()
