# app/storage/utils.py
import os
from uuid import uuid4

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg"}
MAX_SIZE_BYTES = 5 * 1024 * 1024

def is_allowed_extension(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXT

def gen_unique_filename(original: str) -> str:
    _, ext = os.path.splitext(original.lower())
    return f"image_{uuid4().hex}{ext}"

def ensure_upload_dir(path: str):
    os.makedirs(path, exist_ok=True)
