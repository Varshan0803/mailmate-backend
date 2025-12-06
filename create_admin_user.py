import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.core.security import hash_password

# Ensure we can import from app
sys.path.append(os.getcwd())

async def create_admin():
    print("Creating admin user...")
    try:
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client.get_default_database()
        users = db.users
        
        email = "admin@mailmate.com"
        password = "securePassword123"
        
        existing_user = await users.find_one({"email": email})
        
        if existing_user:
            print(f"User {email} already exists.")
        else:
            hashed_pwd = hash_password(password)
            new_user = {
                "name": "Admin User",
                "email": email,
                "password_hash": hashed_pwd,
                "role": "admin",
                "username": "admin_mailmate"
            }
            await users.insert_one(new_user)
            print(f"User {email} created successfully.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(create_admin())
