from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import base64

from database import get_db
from models import User, UserSettings, UserStats
from schemas import (
    UserResponse, UserUpdate, UserSettingsResponse, UserSettingsUpdate,
    GamificationResponse
)
from dependencies import get_current_user
from auth import get_password_hash, verify_password

router = APIRouter()


# ============================================================
# PROFILE
# ============================================================

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    for key, value in user_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(current_user, key, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    ext = file.filename.split('.')[-1] if file.filename else 'png'
    avatar_data = base64.b64encode(contents).decode('utf-8')
    avatar_url = f"data:image/{ext};base64,{avatar_data}"
    
    current_user.avatar_url = avatar_url
    db.commit()
    
    return {"avatar_url": avatar_url}


# ============================================================
# SETTINGS
# ============================================================

@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings


@router.put("/settings", response_model=UserSettingsResponse)
async def update_settings(
    settings_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    
    for key, value in settings_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    return settings


# ============================================================
# SUBJECTS
# ============================================================

@router.get("/subjects", response_model=List[str])
async def get_subjects(
    current_user: User = Depends(get_current_user)
):
    return ["Mathematics", "English", "Physics", "Chemistry"]


@router.put("/subjects")
async def update_subjects(
    subjects: List[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {"message": "Subjects updated", "subjects": subjects}


# ============================================================
# PASSWORD
# ============================================================

@router.put("/password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )
    
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 6 characters"
        )
    
    current_user.hashed_password = get_password_hash(new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Password updated successfully"}