
import asyncio
from app.db.client import contacts

async def main():
    try:
        contact = await contacts.find_one()
        if contact:
            print(f"Contact keys: {list(contact.keys())}")
            print(f"Sample 'status' field: {contact.get('status')}")
            print(f"Sample 'unsubscribed' field: {contact.get('unsubscribed')}")
        
        c1 = await contacts.count_documents({"status": "Active"})
        print(f"Count status='Active': {c1}")

        c2 = await contacts.count_documents({"unsubscribed": False})
        print(f"Count unsubscribed=False: {c2}")
        
        c3 = await contacts.count_documents({"unsubscribed": True})
        print(f"Count unsubscribed=True: {c3}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
