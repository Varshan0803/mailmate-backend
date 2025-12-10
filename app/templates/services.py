# app/templates/services.py
import zipfile
import os
import shutil
from datetime import datetime
from bson import ObjectId

from fastapi import HTTPException, UploadFile

from app.db.client import db
from app.storage.utils import gen_unique_filename, ensure_upload_dir
from app.utils.absolute import to_absolute_urls

TEMPLATES_DIR = "templates_storage"     # folder for extracted ZIP (temporary)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Uploads directory for permanent image hosting
UPLOAD_DIR = os.path.join("static", "uploads")
ensure_upload_dir(UPLOAD_DIR)

COL = db.get_collection("templates")


# ---------------------------------------------------------
# Create Template manually (not zip upload)
# ---------------------------------------------------------
async def create_template(doc: dict):
    doc["created_at"] = datetime.utcnow()
    res = await COL.insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def list_templates(skip=0, limit=50):
    cursor = COL.find().skip(skip).limit(limit).sort("created_at", -1)
    out = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        # Ensure stored HTML has absolute image URLs when sent to clients
        doc["html"] = to_absolute_urls(doc.get("html", ""))
        out.append(doc)
    return out


async def get_template(template_id: str):
    doc = await COL.find_one({"_id": ObjectId(template_id)})
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    doc["html"] = to_absolute_urls(doc.get("html", ""))
    return doc


async def update_template(template_id: str, updates: dict):
    await COL.update_one({"_id": ObjectId(template_id)}, {"$set": updates})
    return await get_template(template_id)


async def delete_template(template_id: str):
    res = await COL.delete_one({"_id": ObjectId(template_id)})
    return res.deleted_count == 1



# ---------------------------------------------------------
# PROCESS ZIP UPLOAD (MAIN FUNCTION)
# ---------------------------------------------------------
# ---------------------------------------------------------
# PROCESS ZIP UPLOAD (MAIN FUNCTION)
# ---------------------------------------------------------
async def process_template_upload(file: UploadFile, segment: str, name: str, user_id: str):
    """
    Steps:
    1. Save uploaded ZIP temporarily
    2. Extract ZIP to /templates_storage/<unique_id>/
    3. Find index.html
    4. Copy all images into static/uploads/
    5. Rewrite HTML image paths -> /storage/files/<uuid>
    6. Save template record in MongoDB
    """

    if not name:
        raise HTTPException(status_code=400, detail="Template name is required")

    if not segment:
        raise HTTPException(status_code=400, detail="Segment is required")

    # -----------------------------------
    # 1. Save ZIP temporarily
    # -----------------------------------
    temp_zip_path = f"{TEMPLATES_DIR}/temp_{file.filename}"

    with open(temp_zip_path, "wb") as buffer:
        buffer.write(await file.read())

    # -----------------------------------
    # 2. Extract ZIP
    # -----------------------------------
    template_folder = f"{TEMPLATES_DIR}/{name.replace(' ', '_').lower()}_{int(datetime.utcnow().timestamp())}"
    os.makedirs(template_folder, exist_ok=True)

    try:
        with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
            zip_ref.extractall(template_folder)
    except:
        raise HTTPException(status_code=400, detail="Invalid ZIP format")

    os.remove(temp_zip_path)

    # -----------------------------------
    # 3. Locate index.html
    # -----------------------------------
    index_path = None
    for root, dirs, files in os.walk(template_folder):
        if "index.html" in files:
            index_path = os.path.join(root, "index.html")
            break

    if not index_path:
        raise HTTPException(status_code=400, detail="index.html not found inside ZIP")

    # Read HTML
    with open(index_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # -----------------------------------
    # 4 & 5. Copy all images → uploads and rewrite HTML paths
    # -----------------------------------
    saved_image_names = []  # names stored in DB

    for root, dirs, files in os.walk(template_folder):
        for fname in files:
            if fname.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".gif")):

                # Original extracted file path
                full_path = os.path.join(root, fname)

                # Relative path (as referenced in HTML)
                relative_path = os.path.relpath(full_path, template_folder).replace("\\", "/")

                # Generate unique name for storage
                new_name = gen_unique_filename(fname)
                dest_path = os.path.join(UPLOAD_DIR, new_name)

                # Copy image into static/uploads/
                shutil.copy2(full_path, dest_path)

                saved_image_names.append(new_name)

                # Rewrite HTML references (relative) first
                html_content = html_content.replace(relative_path, f"/storage/files/{new_name}")

    # Convert any remaining /storage/files paths to absolute using BACKEND_PUBLIC_URL
    html_content = to_absolute_urls(html_content)

    # -----------------------------------
    # OPTIONAL — Cleanup extracted template folder
    # -----------------------------------
    try:
        shutil.rmtree(template_folder)
    except:
        pass

    # -----------------------------------
    # 6. Save template record in MongoDB
    # -----------------------------------
    doc = {
        "name": name,
        "segment": segment,
        "html": html_content,
        "images": saved_image_names,
        "created_by": user_id,
        "created_at": datetime.utcnow()
    }

    res = await COL.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    return doc
