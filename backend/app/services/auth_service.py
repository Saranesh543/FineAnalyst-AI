import os
import hashlib
import hmac
import jwt
import time
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.config.settings import settings

SECRET_KEY = settings.JWT_SECRET if hasattr(settings, "JWT_SECRET") else "fallback-secret-key-for-dev"
ALGORITHM = "HS256"

class AuthService:
    @staticmethod
    def hash_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
        if salt is None:
            salt = os.urandom(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return hashed, salt

    @staticmethod
    def verify_password(password: str, hashed: bytes, salt: bytes) -> bool:
        new_hash, _ = AuthService.hash_password(password, salt)
        return hmac.compare_digest(new_hash, hashed)

    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=60)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> dict | None:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None

auth_service = AuthService()
