# app/utils/absolute.py
import re
from app.config import settings

# Use backend public URL from Pydantic Settings
BACKEND_PUBLIC_URL = settings.BACKEND_PUBLIC_URL.rstrip("/")


def to_absolute_urls(html: str) -> str:
    """
    Convert all relative storage URLs inside HTML to absolute URLs.

    Examples converted:
        src="/storage/files/abc.png"
        src='/storage/files/abc.png'
        src=/storage/files/abc.png

    Output:
        src="http://host/storage/files/abc.png"
    """

    if not html:
        return html or ""

    # Double-quoted → src="/storage/files/xxx"
    html = html.replace(
        'src="/storage/files/',
        f'src="{BACKEND_PUBLIC_URL}/storage/files/'
    )

    # Single-quoted → src='/storage/files/xxx'
    html = html.replace(
        "src='/storage/files/",
        f"src='{BACKEND_PUBLIC_URL}/storage/files/"
    )

    # No quotes → src=/storage/files/xxx
    html = re.sub(
        r'src=/storage/files/',
        f'src={BACKEND_PUBLIC_URL}/storage/files/',
        html
    )

    return html
