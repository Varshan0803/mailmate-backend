import os
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")

def to_absolute(url_path: str) -> str:
    if url_path.startswith("http"):
        return url_path
    return BACKEND_PUBLIC_URL.rstrip("/") + url_path
