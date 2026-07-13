from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import secrets

from database import get_db
from models import User, UserSettings, UserStats, ReferralCode, Referral
from schemas import UserCreate, UserLogin, TokenResponse, UserResponse, ForgotPasswordRequest, ResetPasswordRequest, RefreshTokenRequest
from auth import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from dependencies import get_current_user
from config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    # Check existing user
    existing = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create user
    hashed = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        school=user_data.school,
        country=user_data.country,
        exam=user_data.exam,
        hashed_password=hashed
    )
    db.add(db_user)
    db.flush()
    
    # Create settings
    settings_obj = UserSettings(user_id=db_user.id)
    db.add(settings_obj)
    
    # Create stats
    stats = UserStats(user_id=db_user.id)
    db.add(stats)
    
    db.commit()
    db.refresh(db_user)
    
    # Handle referral
    if user_data.referral_code:
        referrer_code = db.query(ReferralCode).filter(
            ReferralCode.code == user_data.referral_code
        ).first()
        if referrer_code:
            referral = Referral(
                referrer_id=referrer_code.user_id,
                referred_id=db_user.id,
                referral_code=user_data.referral_code
            )
            db.add(referral)
            referrer_code.signups += 1
            db.commit()
    
    return db_user


# ============================================================
# LOGIN — Now accepts JSON with email + password
# ============================================================
@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,  # ← JSON body: { email, password }
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
        "tier": user.tier.value if hasattr(user.tier, 'value') else user.tier
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "tier": user.tier.value if hasattr(user.tier, 'value') else user.tier
        }
        
        new_access = create_access_token(token_data)
        new_refresh = create_refresh_token(token_data)
        
        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer"
        }
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    # Token blacklisting would go here (Redis)
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    # In production, store in a separate table with expiry
    # For now, we'll just return success
    
    return {
        "success": True,
        "message": "Password reset link sent to email",
        "token": reset_token  # In production, send via email
    }


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    # In production, verify token from database
    # For now, accept any token
    if not request.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token"
        )
    
    return {"success": True, "message": "Password reset successful"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user
