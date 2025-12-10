# app/utils/absolute.py
import re
from app.config import settings

# Use backend public URL from Pydantic Settings
BACKEND_PUBLIC_URL = settings.BACKEND_PUBLIC_URL.rstrip("/")


def _replace(src: str, old: str, new: str) -> str:
    """Small helper to keep replacements readable."""
    return src.replace(old, new)


def to_absolute_urls(html: str) -> str:
    """
    Convert storage URLs inside HTML to absolute URLs.

    Handles:
    - /storage/files/* (relative)
    - /static/uploads/* (relative)
    - localhost/127.0.0.1 static URLs persisted in older content
    """
    if not html:
        return html or ""

    target_storage = f"{BACKEND_PUBLIC_URL}/storage/files/"
    target_uploads = f"{BACKEND_PUBLIC_URL}/static/uploads/"

    # Common relative patterns
    html = _replace(html, 'src="/storage/files/', f'src="{target_storage}')
    html = _replace(html, "src='/storage/files/", f"src='{target_storage}")
    html = re.sub(r'src=/storage/files/', f'src={target_storage}', html)

    html = _replace(html, 'src="/static/uploads/', f'src="{target_uploads}')
    html = _replace(html, "src='/static/uploads/", f"src='{target_uploads}")
    html = re.sub(r'src=/static/uploads/', f'src={target_uploads}', html)

    # Legacy absolute hosts to normalize
    legacy_hosts = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://localhost:8000",
        "https://127.0.0.1:8000",
    ]
    for host in legacy_hosts:
        html = _replace(html, f'src="{host}/static/uploads/', f'src="{target_uploads}')
        html = _replace(html, f"src='{host}/static/uploads/", f"src='{target_uploads}")
        html = _replace(html, f'src={host}/static/uploads/', f'src={target_uploads}')

    return html
