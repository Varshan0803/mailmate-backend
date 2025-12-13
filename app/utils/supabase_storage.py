import mimetypes
from supabase import create_client, Client
from app.config import settings

def get_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def upload_file_to_supabase(file_bytes: bytes, filename: str, content_type: str) -> str:
    """
    Uploads a file to Supabase Storage and returns the public URL.
    """
    supabase = get_supabase_client()
    bucket = settings.SUPABASE_BUCKET
    
    # Upload to Supabase
    # upsert=True allows overwriting if filename collision, but unique filenames are preferred
    response = supabase.storage.from_(bucket).upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": content_type, "upsert": "false"}
    )
    
    # Get Public URL
    # supabase-py returns a generic response, constructing URL manually is often safer/faster
    # or use .get_public_url()
    public_url_response = supabase.storage.from_(bucket).get_public_url(filename)
    
    # public_url_response is just a string in some versions, or an object. 
    # Checking latest supabase-py behavior: get_public_url returns a string.
    return public_url_response
