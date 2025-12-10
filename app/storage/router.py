# app/storage/router.py
import os
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from app.storage.schemas import UploadResponse
from app.storage import utils as storage_utils
from app.deps import get_current_user  # use your existing auth dependency
from app.config import settings

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
storage_utils.ensure_upload_dir(UPLOAD_DIR)

router = APIRouter(prefix="/storage", tags=["storage"])

@router.post("/upload-image", response_model=UploadResponse, status_code=HTTP_201_CREATED)
async def upload_image(file: UploadFile = File(...), user = Depends(get_current_user)):
    if not storage_utils.is_allowed_extension(file.filename):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid file type")
    contents = await file.read()
    if len(contents) > storage_utils.MAX_SIZE_BYTES:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="File too large")
    # Basic content heuristic
    head = contents[:512]
    if b"<?php" in head or head.startswith(b"#!"):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Executable content not allowed")
    unique = storage_utils.gen_unique_filename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, unique)
    with open(save_path, "wb") as f:
        f.write(contents)
    # Return absolute URL path using BACKEND_PUBLIC_URL to match the /static mount
    # url = f"/storage/files/{unique}" -> INCORRECT
    url = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/static/uploads/{unique}"
    return UploadResponse(filename=unique, url=url, size=len(contents))

@router.get("/files/{filename}")
async def get_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(path)

@router.delete("/files/{filename}")
async def delete_file(filename: str, user = Depends(get_current_user)):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="File not found")
    os.remove(path)
    return {"detail": "deleted"}
