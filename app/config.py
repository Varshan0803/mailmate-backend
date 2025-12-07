import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "mailmate"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"

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

    REGISTRATION_SECRET_KEY: str = "secret123"

    class Config:
        env_file = ".env"

settings = Settings()