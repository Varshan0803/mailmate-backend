# app/routes/auth.py

from fastapi import APIRouter, HTTPException, Depends
from app.schemas.user_schema import UserCreate, UserOut, LoginSchema
from app.services.auth_service import create_user, authenticate
from app.core.security import create_access_token
from app.deps import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["auth"])


from app.config import settings

# REGISTER
@router.post("/register", response_model=UserOut)
async def register(user: UserCreate):
    if user.secret_key != settings.REGISTRATION_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid registration secret key")
    try:
        doc = await create_user(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "email": doc["email"],
        "role": doc["role"]
    }


# LOGIN  ← FIXED HERE (LoginSchema instead of UserCreate)
@router.post("/login")
async def login(form: LoginSchema):
    user = await authenticate(form.email, form.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(str(user["_id"]))

    return {"access_token": token, "token_type": "bearer"}


# CURRENT USER DETAILS
@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"]
    }


# ADMIN ONLY CHECK
@router.get("/admin-only")
async def admin_only(user=Depends(require_role("admin"))):
    return {
        "ok": True,
        "message": "You are admin",
        "user": {"id": str(user["_id"]), "email": user["email"]}
    }


# PROMOTE USER TO ADMIN
@router.post("/promote/{user_email}")
async def promote_user(user_email: str, caller=Depends(require_role("admin"))):
    users_coll = __import__("app.db.client", fromlist=["db"]).db.get_collection("users")
    res = await users_coll.update_one(
        {"email": user_email},
        {"$set": {"role": "admin"}}
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"ok": True, "email": user_email, "promoted_to": "admin"}
