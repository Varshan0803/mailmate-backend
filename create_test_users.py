import asyncio
import sys
import os

# Ensure we can import from app
sys.path.append(os.getcwd())

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.core.security import hash_password

async def create_users():
    print("="*60)
    print("[INFO] CREATING TEST USERS")
    print("="*60)

    # Connect to MongoDB
    try:
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client.get_default_database()
        users_collection = db.users
        print(f"   [OK] Connected to database: {db.name}")
    except Exception as e:
        print(f"   [ERROR] Failed to connect to MongoDB: {e}")
        return

    # Define users to create
    users_to_create = [
        {
            "username": "admin_user",
            "email": "admin@example.com",
            "password": "securePassword123",
            "role": "admin",
            "name": "Admin User"
        },
        {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "password123",
            "role": "user",
            "name": "John Doe"
        },
        {
            "username": "jane_smith",
            "email": "jane@example.com",
            "password": "mysecretpass",
            "role": "user",
            "name": "Jane Smith"
        }
    ]

    for user_data in users_to_create:
        email = user_data["email"]
        
        # Check if user exists
        existing_user = await users_collection.find_one({"email": email})
        
        if existing_user:
            print(f"   [SKIP] User {email} already exists")
        else:
            # Hash password
            hashed_pwd = hash_password(user_data["password"])
            
            # Create user document
            new_user = {
                "name": user_data["name"],
                "email": email,
                "password_hash": hashed_pwd,
                "role": user_data["role"],
                # Add username if your schema supports it, otherwise just name/email
                # Based on analysis, schema has 'name', 'email', 'password_hash', 'role'
                # I'll add 'username' just in case, but rely on email for auth
                "username": user_data["username"] 
            }
            
            result = await users_collection.insert_one(new_user)
            print(f"   [OK] Created user: {user_data['username']} ({email}) - ID: {result.inserted_id}")

    print("\n" + "="*60)
    print("Users created successfully")
    print("="*60)
    client.close()

if __name__ == "__main__":
    # Run the async function
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(create_users())
    except RuntimeError:
        # For environments where event loop is already running or closed
        asyncio.run(create_users())
