# app/templates/routes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from app.templates.schemas import TemplateCreate, TemplateOut, TemplateUpdate
from app.templates import services
from app.deps import get_current_user, require_role

router = APIRouter(prefix="/templates", tags=["templates"])

# --------------------------
# 1) UPLOAD TEMPLATE ZIP
# --------------------------
@router.post("/upload", response_model=TemplateOut, status_code=201)
async def upload_template(
    file: UploadFile = File(...),
    segment: str = Form(...),
    name: str = Form(...),
    user = Depends(require_role("marketing"))
):
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")

    # Pass to service for processing
    template = await services.process_template_upload(
        file=file,
        segment=segment,
        name=name,
        user_id=str(user["_id"])
    )

    return template


# --------------------------
# 2) MANUAL TEMPLATE CREATION
# --------------------------
@router.post("/", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(payload: TemplateCreate, user = Depends(require_role("marketing"))):
    doc = payload.model_dump()
    doc["created_by"] = str(user["_id"])
    res = await services.create_template(doc)
    return {
        "id": str(res["_id"]),
        "name": res["name"],
        "html": res["html"],
        "images": res.get("images", []),
        "created_by": res["created_by"],
        "created_at": res["created_at"]
    }

# --------------------------
# 3) LIST TEMPLATES
# --------------------------
@router.get("/", response_model=list[TemplateOut])
async def list_templates(skip: int = 0, limit: int = 50, user = Depends(get_current_user)):
    return await services.list_templates(skip=skip, limit=limit)

# --------------------------
# 4) GET TEMPLATE BY ID
# --------------------------
@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: str, user = Depends(get_current_user)):
    doc = await services.get_template(template_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    return doc

# --------------------------
# 5) UPDATE TEMPLATE
# --------------------------
@router.put("/{template_id}", response_model=TemplateOut)
async def update_template(template_id: str, payload: TemplateUpdate, user = Depends(require_role("marketing"))):
    updates = payload.model_dump(exclude_none=True)
    updated = await services.update_template(template_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Template not found")
    return updated

# --------------------------
# 6) DELETE TEMPLATE
# --------------------------
@router.delete("/{template_id}", status_code=status.HTTP_200_OK)
async def delete_template(template_id: str, user = Depends(require_role("marketing"))):
    ok = await services.delete_template(template_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}
