import os
from datetime import datetime, timedelta, timezone
from jose import jwt

ALGORITHM = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change")


def create_access_token(sub: str, expires_minutes: int = 60) -> str:
    to_encode = {
        "sub": sub,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
