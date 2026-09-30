from typing import Iterable
from time import perf_counter

from opentelemetry import trace
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models import User, UserRole
from app.security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
logger = get_logger("auth")
tracer = trace.get_tracer("app.auth")
AUTH_VALIDATE_OPERATION = "auth.validate"
AUTH_TOKEN_VALID_ATTRIBUTE = "auth.token_valid"


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    start = perf_counter()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    with tracer.start_as_current_span(AUTH_VALIDATE_OPERATION) as span:
        try:
            payload = decode_access_token(token)
            user_id_raw = payload.get("sub")
            if user_id_raw is None:
                raise credentials_exception
            user_id = int(user_id_raw)
            span.set_attribute("auth.user_id", user_id)
            span.set_attribute(AUTH_TOKEN_VALID_ATTRIBUTE, True)
        except Exception as exc:
            duration_ms = int((perf_counter() - start) * 1000)
            span.set_attribute(AUTH_TOKEN_VALID_ATTRIBUTE, False)
            logger.warning(
                "token_validation_failed",
                operation=AUTH_VALIDATE_OPERATION,
                status="failure",
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise credentials_exception from exc

        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            duration_ms = int((perf_counter() - start) * 1000)
            span.set_attribute(AUTH_TOKEN_VALID_ATTRIBUTE, False)
            logger.warning(
                "token_validation_failed",
                operation=AUTH_VALIDATE_OPERATION,
                status="failure",
                duration_ms=duration_ms,
                error="User missing or inactive",
            )
            raise credentials_exception

        duration_ms = int((perf_counter() - start) * 1000)
        logger.info(
            "token_validated",
            operation=AUTH_VALIDATE_OPERATION,
            status="success",
            duration_ms=duration_ms,
            user_id=user.id,
        )
        return user


def require_roles(roles: Iterable[UserRole]):
    role_values = {role.value if isinstance(role, UserRole) else str(role) for role in roles}

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in role_values:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return role_checker
