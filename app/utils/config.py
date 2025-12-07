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
    SENDER_EMAIL: str
    
    # Intelligently grab the Redis URL from Railway
    CELERY_BROKER_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")

    class Config:
        env_file = ".env"
        extra = "ignore" 

settings = Settings()
