import os
import json
import requests
from pymongo import MongoClient

# Load MONGO_URI from .env or env
from dotenv import load_dotenv
load_dotenv()
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    raise SystemExit('MONGO_URI not set')

client = MongoClient(MONGO_URI)
db = client.get_default_database()

# try to find a campaign_id from email_logs
doc = db['email_logs'].find_one({}, {'campaign_id': 1})
if not doc:
    print('No email_logs documents found')
    raise SystemExit(0)

campaign_id = doc.get('campaign_id')
print('Using campaign_id:', campaign_id)

url = f'http://127.0.0.1:8000/analytics/{campaign_id}/summary'
print('Calling', url)
try:
    r = requests.get(url, timeout=10)
    print('Status:', r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)
except Exception as e:
    print('Request failed:', e)
