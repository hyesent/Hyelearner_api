from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import secrets

from database import get_db
from models import User, ReferralCode, Referral, UserStats
from schemas import ReferralCodeResponse, ReferralTrackRequest, ReferralTrackResponse
from dependencies import get_current_user

router = APIRouter()


@router.get("/code", response_model=ReferralCodeResponse)
async def get_referral_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get or generate user's referral code"""
    referral_code = db.query(ReferralCode).filter(
        ReferralCode.user_id == current_user.id
    ).first()
    
    if not referral_code:
        # Generate unique code
        code = secrets.token_hex(4).upper()
        
        # Check if code exists
        existing = db.query(ReferralCode).filter(ReferralCode.code == code).first()
        while existing:
            code = secrets.token_hex(4).upper()
            existing = db.query(ReferralCode).filter(ReferralCode.code == code).first()
        
        referral_code = ReferralCode(
            user_id=current_user.id,
            code=code,
            clicks=0,
            signups=0
        )
        db.add(referral_code)
        db.commit()
        db.refresh(referral_code)
    
    # Calculate rewards earned
    rewards = referral_code.signups * 500  # 500 XP per referral
    
    return {
        "code": referral_code.code,
        "clicks": referral_code.clicks,
        "signups": referral_code.signups,
        "rewards": rewards
    }


@router.post("/track", response_model=ReferralTrackResponse)
async def track_referral(
    request: ReferralTrackRequest,
    db: Session = Depends(get_db)
):
    """Track a referral click/signup"""
    referral_code = db.query(ReferralCode).filter(
        ReferralCode.code == request.code
    ).first()
    
    if not referral_code:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    
    # Track click
    referral_code.clicks += 1
    db.commit()
    
    return {
        "success": True,
        "referrer": db.query(User).filter(User.id == referral_code.user_id).first().username,
        "reward": 500,
        "message": "Referral tracked! Sign up to claim 500 XP bonus."
    }


@router.post("/claim")
async def claim_referral(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Claim referral reward after signup"""
    # Check if user was referred
    referral = db.query(Referral).filter(
        Referral.referred_id == current_user.id,
        Referral.reward_given == False
    ).first()
    
    if not referral:
        raise HTTPException(status_code=404, detail="No pending referral reward")
    
    # Get referral code
    referral_code = db.query(ReferralCode).filter(
        ReferralCode.code == referral.referral_code
    ).first()
    
    if not referral_code:
        raise HTTPException(status_code=404, detail="Referral code not found")
    
    # Give reward to referrer
    referrer_stats = db.query(UserStats).filter(
        UserStats.user_id == referral.referrer_id
    ).first()
    
    if referrer_stats:
        referrer_stats.xp += 500
        referrer_stats.level = min(referrer_stats.xp // 100 + 1, 20)
    
    # Give reward to referred user
    referred_stats = db.query(UserStats).filter(
        UserStats.user_id == current_user.id
    ).first()
    
    if referred_stats:
        referred_stats.xp += 100
        referred_stats.level = min(referred_stats.xp // 100 + 1, 20)
    
    # Mark reward as given
    referral.reward_given = True
    referral_code.signups += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": "Referral reward claimed! You earned 100 XP and your referrer earned 500 XP."
    }


@router.get("/stats")
async def get_referral_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get referral statistics for current user"""
    referral_code = db.query(ReferralCode).filter(
        ReferralCode.user_id == current_user.id
    ).first()
    
    if not referral_code:
        return {
            "total_clicks": 0,
            "total_signups": 0,
            "xp_earned": 0,
            "code": None
        }
    
    referrals = db.query(Referral).filter(
        Referral.referrer_id == current_user.id
    ).all()
    
    xp_earned = len(referrals) * 500
    
    return {
        "total_clicks": referral_code.clicks,
        "total_signups": referral_code.signups,
        "xp_earned": xp_earned,
        "code": referral_code.code
    }