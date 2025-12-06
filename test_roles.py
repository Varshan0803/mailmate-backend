import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://127.0.0.1:8000"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "securePassword123"

NEW_USER_EMAIL = f"test_user_{int(time.time())}@example.com"
NEW_USER_PASSWORD = "password123"
NEW_USER_NAME = "Test User"

def request(method, url, data=None, token=None):
    req = urllib.request.Request(url, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    
    if data:
        req.data = json.dumps(data).encode('utf-8')
        
    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode(), json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
        return 500, str(e)

def run_test():
    print(f"--- Testing User Roles & Permissions ---")
    
    # 1. Register New User
    print(f"\n1. Registering new user: {NEW_USER_EMAIL}")
    code, data = request('POST', f"{BASE_URL}/auth/register", {
        "name": NEW_USER_NAME,
        "email": NEW_USER_EMAIL,
        "password": NEW_USER_PASSWORD
    })
    print(f"   Status: {code}")
    if code != 200:
        print(f"   Failed to register: {data}")
        return

    user_role = data.get("role")
    print(f"   Assigned Role: {user_role}")
    if user_role != "marketing":
        print("   ❌ FAIL: Role should be 'marketing'")
    else:
        print("   ✅ PASS: Role is 'marketing'")

    # 2. Login as New User
    print(f"\n2. Logging in as new user...")
    code, data = request('POST', f"{BASE_URL}/auth/login", {
        "email": NEW_USER_EMAIL,
        "password": NEW_USER_PASSWORD
    })
    user_token = data.get("access_token")
    print(f"   Got Token: {bool(user_token)}")

    # 3. Access Analytics as New User (Should Fail)
    print(f"\n3. Accessing Analytics as 'marketing' user...")
    # We need a valid campaign ID for the route, but the permission check happens first.
    # We can use a dummy ID, if it fails with 403 it's a pass. If 404, it passed auth but failed lookup.
    dummy_id = "507f1f77bcf86cd799439011" 
    code, data = request('GET', f"{BASE_URL}/analytics/{dummy_id}/summary", token=user_token)
    print(f"   Status: {code}")
    if code == 403:
        print("   ✅ PASS: Access Denied (403)")
    else:
        print(f"   ❌ FAIL: Expected 403, got {code}")

    # 4. Login as Admin
    print(f"\n4. Logging in as Admin...")
    code, data = request('POST', f"{BASE_URL}/auth/login", {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    admin_token = data.get("access_token")
    print(f"   Got Token: {bool(admin_token)}")

    # 5. Access Analytics as Admin (Should Succeed or 404 if campaign missing)
    print(f"\n5. Accessing Analytics as 'admin' user...")
    code, data = request('GET', f"{BASE_URL}/analytics/{dummy_id}/summary", token=admin_token)
    print(f"   Status: {code}")
    if code == 403:
        print("   ❌ FAIL: Admin was denied access")
    elif code == 404:
        print("   ✅ PASS: Admin allowed (404 Campaign Not Found is expected for dummy ID)")
    elif code == 200:
        print("   ✅ PASS: Admin allowed (200 OK)")
    else:
        print(f"   ❓ Unexpected status: {code}")

if __name__ == "__main__":
    run_test()
