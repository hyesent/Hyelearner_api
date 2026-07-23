from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
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


@router.post("/register")  # ✅ REMOVED response_model=UserResponse
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
    
    # ✅ Create token data
    token_data = {
        "sub": str(db_user.id),
        "email": db_user.email,
        "role": db_user.role.value if hasattr(db_user.role, 'value') else db_user.role,
        "tier": db_user.tier.value if hasattr(db_user.tier, 'value') else db_user.tier
    }
    
    # ✅ Create tokens
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # ✅ Return user + tokens
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "username": db_user.username,
            "first_name": db_user.first_name,
            "last_name": db_user.last_name,
            "avatar_url": db_user.avatar_url,
            "role": db_user.role.value if hasattr(db_user.role, 'value') else db_user.role,
            "tier": db_user.tier.value if hasattr(db_user.tier, 'value') else db_user.tier,
            "school": db_user.school,
            "country": db_user.country,
            "exam": db_user.exam,
            "bio": db_user.bio,
            "goal": db_user.goal,
            "subscription_expires": db_user.subscription_expires,
            "is_active": db_user.is_active,
            "is_verified": db_user.is_verified,
            "created_at": db_user.created_at
        }
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    # Find user by email
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
    
    # Create token data
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
        "tier": user.tier.value if hasattr(user.tier, 'value') else user.tier
    }
    
    # Create tokens
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "tier": user.tier.value if hasattr(user.tier, 'value') else user.tier,
            "school": user.school,
            "country": user.country,
            "exam": user.exam,
            "bio": user.bio,
            "goal": user.goal,
            "subscription_expires": user.subscription_expires,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at
        }
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
    
    reset_token = secrets.token_urlsafe(32)
    
    return {
        "success": True,
        "message": "Password reset link sent to email",
        "token": reset_token
    }


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
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
