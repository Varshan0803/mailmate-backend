import urllib.request
import urllib.parse
import json
import datetime

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "admin@example.com"
PASSWORD = "securePassword123"

def test_create_campaign():
    # 1. Login
    print(f"Logging in...")
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

    # 2. Create Campaign (Simulate Frontend Payload)
    print("\nCreating Campaign...")
    # Frontend sends:
    # {
    #     name: title,
    #     subject: subject,
    #     segment: audience_id,
    #     html_content: content,
    #     sender_name: senderName,
    #     reply_to: replyTo,
    #     status: 'Pending',
    #     send_at: schedule_time
    # }
    payload = {
        "name": "Test Campaign via Script",
        "subject": "Hello World",
        "segment": "All Contacts",
        "html_content": "<h1>Test Content</h1>",
        "sender_name": "Tester",
        "reply_to": "test@example.com",
        "status": "Pending",
        "send_at": datetime.datetime.utcnow().isoformat()
    }
    
    req = urllib.request.Request(f"{BASE_URL}/campaigns/", data=json.dumps(payload).encode('utf-8'))
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Status: {response.getcode()}")
            data = json.loads(response.read().decode('utf-8'))
            print(f"Created Campaign ID: {data.get('id')}")
            print(f"Template ID: {data.get('template_id')}")
    except urllib.error.HTTPError as e:
        print(f"Create Failed: {e.code} {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_create_campaign()
