"""
Auth API Routes

Endpoints for user registration, login, and profile.
"""
from __future__ import annotations

import logging
import re
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, ForgotPasswordRequest, ResetPasswordRequest, RefreshRequest, UserResponse, TokenResponse
from app.services.auth_service import auth_service
from app.api.deps import get_current_user
from app.config.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$')


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    if not PASSWORD_REGEX.match(payload.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with 1 uppercase, 1 lowercase, and 1 number."
        )

    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    hashed, salt = auth_service.hash_password(payload.password)
    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        hashed_password=hashed,
        salt=salt,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = auth_service.create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = auth_service.create_access_token({"sub": str(user.id), "email": user.email, "type": "refresh"}, expires_delta=timedelta(days=30))
    logger.info("User registered: %s", user.email)

    return TokenResponse(
        access_token=token,
        refresh_token=refresh_token,
        user=UserResponse(id=user.id, full_name=user?.full_name, email=user.email, created_at=user.created_at)
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and return a JWT token."""
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No account found. Please sign up first."
        )

    if not auth_service.verify_password(payload.password, user.hashed_password, user.salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    expires = timedelta(days=7) if payload.remember_me else timedelta(hours=2)
    token = auth_service.create_access_token({"sub": str(user.id), "email": user.email}, expires_delta=expires)
    refresh_token = auth_service.create_access_token({"sub": str(user.id), "email": user.email, "type": "refresh"}, expires_delta=timedelta(days=30))
    logger.info("User logged in: %s (remember_me=%s)", user.email, payload.remember_me)

    return TokenResponse(
        access_token=token,
        refresh_token=refresh_token,
        user=UserResponse(id=user.id, full_name=user?.full_name, email=user.email, created_at=user.created_at)
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh an access token using a refresh token."""
    decoded = auth_service.decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    user_id = decoded.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token payload")
        
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    token = auth_service.create_access_token({"sub": str(user.id), "email": user.email}, expires_delta=timedelta(hours=2))
    new_refresh_token = auth_service.create_access_token({"sub": str(user.id), "email": user.email, "type": "refresh"}, expires_delta=timedelta(days=30))
    
    return TokenResponse(
        access_token=token,
        refresh_token=new_refresh_token,
        user=UserResponse(id=user.id, full_name=user?.full_name, email=user.email, created_at=user.created_at)
    )

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return UserResponse(id=user.id, full_name=user?.full_name, email=user.email, created_at=user.created_at)


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Forgot password endpoint.
    Email delivery is pending infrastructure — logs the token instead.
    """
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    
    if user:
        reset_token = auth_service.create_access_token({"sub": str(user.id), "type": "reset"}, expires_delta=timedelta(hours=1))
        logger.warning(f"Simulating email to {user.email}. Reset token: {reset_token}")
        
    return {
        "message": "If an account exists for this email, a reset link will be sent once email delivery is configured.",
        "status": "pending_infrastructure"
    }

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset the user's password using a reset token."""
    if not PASSWORD_REGEX.match(payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with 1 uppercase, 1 lowercase, and 1 number."
        )
        
    decoded = auth_service.decode_token(payload.token)
    if not decoded or decoded.get("type") != "reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")
        
    user_id = decoded.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload.")
        
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found.")
        
    hashed, salt = auth_service.hash_password(payload.new_password)
    user.hashed_password = hashed
    user.salt = salt
    
    await db.commit()
    
    return {"message": "Password successfully reset."}
