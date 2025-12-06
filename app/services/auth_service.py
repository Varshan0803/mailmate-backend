from app.db.client import db
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.user_schema import UserCreate
from bson import ObjectId

USERS_COLL = db.get_collection("users")

async def create_user(user: UserCreate, role: str = "admin"):
    existing = await USERS_COLL.find_one({"email": user.email})
    if existing:
        raise ValueError("Email already registered")
    hashed = hash_password(user.password)
    doc = {"name": user.name, "email": user.email, "password_hash": hashed, "role": role}
    res = await USERS_COLL.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc

async def authenticate(email: str, password: str):
    doc = await USERS_COLL.find_one({"email": email})
    if not doc:
        return None
    if not verify_password(password, doc["password_hash"]):
        return None
    return doc
