from datetime import timedelta
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.logging_config import get_logger
from app.models import User
from app.schemas import Token, UserRead, UserRegister
from app.security import create_access_token, hash_password, verify_password


router = APIRouter()
logger = get_logger("auth")
AUTH_LOGIN_OPERATION = "auth.login"


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    start = perf_counter()
    user = db.query(User).filter(User.email == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        duration_ms = int((perf_counter() - start) * 1000)
        logger.warning(
            "login_failed",
            operation=AUTH_LOGIN_OPERATION,
            status="failure",
            duration_ms=duration_ms,
            email=form_data.username,
            error="Invalid credentials",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        duration_ms = int((perf_counter() - start) * 1000)
        logger.warning(
            "login_failed",
            operation=AUTH_LOGIN_OPERATION,
            status="failure",
            duration_ms=duration_ms,
            email=form_data.username,
            error="User is inactive",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    duration_ms = int((perf_counter() - start) * 1000)
    logger.info(
        "login_success",
        operation=AUTH_LOGIN_OPERATION,
        status="success",
        duration_ms=duration_ms,
        user_id=user.id,
        email=user.email,
    )
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user
