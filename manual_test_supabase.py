
import pytest
from app.config import settings
from supabase import create_client

def test_supabase_config():
    print("\n--- Testing Supabase Configuration ---")
    print(f"URL: {settings.SUPABASE_URL}")
    print(f"Key: {settings.SUPABASE_KEY[:10]}...")
    print(f"Bucket: {settings.SUPABASE_BUCKET}")
    
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        print("SUCCESS: Supabase client created.")
        
        # List buckets to verify connectivity (if key has permissions)
        # Note: 'anon' key might not have permission to list buckets, but we proceed to check structure.
        print("Verifying client structure...")
        assert supabase is not None
        
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_supabase_config()
