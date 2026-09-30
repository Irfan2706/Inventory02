from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import bcrypt as _bcrypt
from passlib.context import CryptContext

from app.config import settings


if not hasattr(_bcrypt, "__about__"):
    _bcrypt.__about__ = SimpleNamespace(__version__=_bcrypt.__version__)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_DECODE_OPTIONS = {"require": ["sub", "exp"], "verify_exp": True}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        options=_DECODE_OPTIONS,
    )
