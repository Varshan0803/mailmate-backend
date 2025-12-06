# app/contacts/routes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import List, Optional
from app.contacts.schemas import ContactCreate, ContactUpdate, ContactOut
from app.contacts import services
from app.deps import get_current_user, require_role

router = APIRouter(prefix="/contacts", tags=["contacts"])

# Get segment counts
@router.get("/segments")
async def get_segments(user = Depends(get_current_user)):
    return await services.get_segment_counts()

# Create contact (manual)
@router.post("/", response_model=ContactOut)
async def create_contact_endpoint(payload: ContactCreate, user = Depends(require_role("marketing"))):
    # ensure email normalized and uniqueness handled in service
    existing = await services.get_contact_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Contact with this email already exists")
    doc = await services.create_contact(payload.model_dump())
    return {
        "id": doc["_id"],
        "name": doc["name"],
        "email": doc["email"],
        "segment": doc.get("segment"),
        "unsubscribed": doc.get("unsubscribed", False),
        "created_at": doc.get("created_at")
    }

# Get contact by id
@router.get("/{contact_id}", response_model=ContactOut)
async def get_contact(contact_id: str, user = Depends(get_current_user)):
    doc = await services.get_contact_by_id(contact_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {
        "id": doc["id"],
        "name": doc["name"],
        "email": doc["email"],
        "segment": doc.get("segment"),
        "unsubscribed": doc.get("unsubscribed", False),
        "created_at": doc.get("created_at")
    }

# Update contact
@router.put("/{contact_id}", response_model=ContactOut)
async def update_contact(contact_id: str, payload: ContactUpdate, user = Depends(require_role("marketing"))):
    updated = await services.update_contact(contact_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {
        "id": updated["id"],
        "name": updated["name"],
        "email": updated["email"],
        "segment": updated.get("segment"),
        "unsubscribed": updated.get("unsubscribed", False),
        "created_at": updated.get("created_at")
    }

# Delete contact
@router.delete("/{contact_id}")
async def delete_contact(contact_id: str, user = Depends(require_role("marketing"))):
    ok = await services.delete_contact(contact_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"ok": True, "deleted_id": contact_id}

# List contacts (with filters + pagination)
@router.get("/", response_model=List[ContactOut])
async def list_contacts(
    segment: Optional[str] = Query(None),
    unsubscribed: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user = Depends(get_current_user)
):
    q = {}
    if segment:
        q["segment"] = segment
    if unsubscribed is not None:
        q["unsubscribed"] = unsubscribed
    docs = await services.list_contacts(q, skip=skip, limit=limit)
    # convert to ContactOut list
    out = []
    for d in docs:
        out.append({
            "id": d["id"],
            "name": d["name"],
            "email": d["email"],
            "segment": d.get("segment"),
            "unsubscribed": d.get("unsubscribed", False),
            "created_at": d.get("created_at")
        })
    return out

# CSV upload endpoint
@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), user = Depends(require_role("marketing"))):
    if not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    content = await file.read()
    parsed = await services.parse_csv_and_prepare(content)
    rows = parsed["rows"]
    errors = parsed["errors"]
    if not rows:
        return {"inserted": 0, "duplicates": 0, "errors": errors}
    result = await services.bulk_insert_contacts(rows)
    # merge parse errors into result
    result["errors"] = result.get("errors", []) + errors
    return result
