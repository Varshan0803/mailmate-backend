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

from typing import List
from app.storage.schemas import UploadResponse, BatchUploadResponse, BatchUploadResult
from app.utils import supabase_storage

@router.post("/upload-images/batch", response_model=BatchUploadResponse, status_code=HTTP_201_CREATED)
async def upload_images_batch(files: List[UploadFile] = File(...), user = Depends(get_current_user)):
    results = []
    for file in files:
        try:
            if not storage_utils.is_allowed_extension(file.filename):
                results.append(BatchUploadResult(
                    success=False, 
                    original_filename=file.filename, 
                    error="Invalid file type"
                ))
                continue
            
            contents = await file.read()
            if len(contents) > storage_utils.MAX_SIZE_BYTES:
                 results.append(BatchUploadResult(
                    success=False, 
                    original_filename=file.filename, 
                    error="File too large"
                ))
                 continue

            unique_filename = storage_utils.gen_unique_filename(file.filename)
            
            # --- SUPABASE UPLOAD ---
            url = supabase_storage.upload_file_to_supabase(
                file_bytes=contents,
                filename=unique_filename,
                content_type=file.content_type or "application/octet-stream"
            )
            
            results.append(BatchUploadResult(
                success=True,
                url=url,
                filename=unique_filename,
                original_filename=file.filename,
                size=len(contents)
            ))
        except Exception as e:
             print(f"Upload failed for {file.filename}: {e}")
             results.append(BatchUploadResult(
                    success=False, 
                    original_filename=file.filename, 
                    error=str(e)
                ))
    return BatchUploadResponse(results=results)

@router.post("/upload-image", response_model=UploadResponse, status_code=HTTP_201_CREATED)
async def upload_image(file: UploadFile = File(...), user = Depends(get_current_user)):
    if not storage_utils.is_allowed_extension(file.filename):
        raise HTTPException(status_code=400, detail="Invalid file type")

    contents = await file.read()
    if len(contents) > storage_utils.MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    unique_filename = storage_utils.gen_unique_filename(file.filename)
    
    try:
        # --- SUPABASE UPLOAD ---
        url = supabase_storage.upload_file_to_supabase(
            file_bytes=contents,
            filename=unique_filename,
            content_type=file.content_type or "application/octet-stream"
        )
        return UploadResponse(filename=unique_filename, url=url, size=len(contents))
    except Exception as e:
        print(f"Supabase upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image to storage")

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
