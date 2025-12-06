# app/deps.py
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.config import settings
from app.db.client import db
from bson import ObjectId

bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.get_collection("users").find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    # convert ObjectId to str for convenience
    user["id"] = str(user["_id"])
    return user

def require_role(role: str):
    async def _require(user = Depends(get_current_user)):
        # admin always allowed
        if user.get("role") == "admin":
            return user
        if user.get("role") != role:
            raise HTTPException(status_code=403, detail="Not authorized for this action")
        return user
    return _require
