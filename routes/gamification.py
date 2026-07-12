from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import UserStats, User
from schemas import GamificationResponse, XPAddRequest
from dependencies import get_current_user

router = APIRouter()


@router.get("/stats", response_model=GamificationResponse)
async def get_gamification_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's gamification stats"""
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    
    if not stats:
        stats = UserStats(user_id=current_user.id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    
    return stats


@router.post("/xp", response_model=GamificationResponse)
async def add_xp(
    data: XPAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add XP to user"""
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    
    if not stats:
        stats = UserStats(user_id=current_user.id)
        db.add(stats)
    
    stats.xp += data.amount
    stats.level = min(stats.xp // 100 + 1, 20)
    stats.last_activity = datetime.utcnow()
    stats.total_sessions += 1 if data.source == "session" else 0
    stats.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(stats)
    
    return stats


@router.get("/badges")
async def get_badges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's earned and available badges"""
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    
    earned_badges = stats.badges if stats else []
    
    # All available badges
    all_badges = [
        {"id": "first_exam", "icon": "🎯", "label": "First Exam", "description": "Complete your first exam"},
        {"id": "first_100", "icon": "💯", "label": "100 Questions", "description": "Answer 100 questions"},
        {"id": "first_500", "icon": "🔥", "label": "500 Questions", "description": "Answer 500 questions"},
        {"id": "first_1000", "icon": "⭐", "label": "1000 Questions", "description": "Answer 1000 questions"},
        {"id": "streak_7", "icon": "🔥", "label": "7-Day Streak", "description": "Study for 7 days in a row"},
        {"id": "streak_30", "icon": "🏆", "label": "30-Day Streak", "description": "Study for 30 days in a row"},
        {"id": "level_10", "icon": "🌟", "label": "Level 10", "description": "Reach Level 10"},
        {"id": "level_25", "icon": "💎", "label": "Level 25", "description": "Reach Level 25"},
        {"id": "level_50", "icon": "👑", "label": "Level 50", "description": "Reach Level 50"},
        {"id": "xp_5000", "icon": "💰", "label": "5,000 XP", "description": "Earn 5,000 XP"},
        {"id": "xp_10000", "icon": "💎", "label": "10,000 XP", "description": "Earn 10,000 XP"},
    ]
    
    # Check which badges are unlocked
    available_badges = []
    for badge in all_badges:
        is_earned = badge["id"] in earned_badges if earned_badges else False
        available_badges.append({
            **badge,
            "earned": is_earned
        })
    
    return {
        "earned": earned_badges if earned_badges else [],
        "available": available_badges,
        "total_earned": len(earned_badges) if earned_badges else 0,
        "total_available": len(all_badges)
    }


@router.post("/badges/{badge_id}")
async def earn_badge(
    badge_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Earn a badge"""
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    
    if not stats:
        stats = UserStats(user_id=current_user.id)
        db.add(stats)
    
    if not stats.badges:
        stats.badges = []
    
    if badge_id not in stats.badges:
        stats.badges.append(badge_id)
        db.commit()
    
    return {"message": f"Badge {badge_id} earned!", "badges": stats.badges}


@router.get("/streak")
async def get_streak(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current streak"""
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    
    if not stats:
        return {"streak": 0, "last_activity": None}
    
    return {
        "streak": stats.streak,
        "last_activity": stats.last_activity,
        "xp": stats.xp,
        "level": stats.level
    }