import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "mailmate"
    # Default to deployed backend; can be overridden via env
    BACKEND_PUBLIC_URL: str = "https://web-production-dab80.up.railway.app"

    ENV: str = "development"
    DEBUG: bool = True

    MONGO_URI: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60*24*30
    SENDGRID_API_KEY: str
    SENDGRID_PUBLIC_KEY: str | None = None
    SENDGRID_WEBHOOK_DISABLE_VERIFY: bool = False
    SENDER_EMAIL: str
    
    # --- THE FIX IS HERE ---
    # We use os.getenv("REDIS_URL") to grab the Railway variable.
    # If it's missing (local dev), we fall back to localhost.
    CELERY_BROKER_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")
    # -----------------------

    # Supabase Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://fxaqxrqmizrfnkpxgdpp.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ4YXF4cnFtaXpyZm5rcHhnZHBwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTYwMzAzMCwiZXhwIjoyMDgxMTc5MDMwfQ.n8vZw6h_D5Ih773af6A1Eh_NnafsxjRJj-wL3TncrWE")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "images")

    REGISTRATION_SECRET_KEY: str = "secret123"

    class Config:
        env_file = ".env"

settings = Settings()