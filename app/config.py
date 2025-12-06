from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "mailmate"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"

    # add these two lines:
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
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    REGISTRATION_SECRET_KEY: str = "secret123"

    class Config:
        env_file = ".env"

settings = Settings()
