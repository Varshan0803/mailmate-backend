# app/core/security.py
from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

# Use pbkdf2_sha256 instead of bcrypt to avoid 72-byte issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using pbkdf2_sha256.
    No manual truncation needed; works with normal passwords.
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against stored hash.
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_delta: int = None) -> str:
    """
    Create a JWT access token for a given user id (subject).
    """
    expire = datetime.utcnow() + timedelta(
        minutes=expires_delta or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
