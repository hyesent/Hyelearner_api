from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date, timedelta
import base64

from database import get_db
from models import User, UserSettings, UserStats, Session as PracticeSession, UserDailyStats
from schemas import (
    UserResponse, UserUpdate, UserSettingsResponse, UserSettingsUpdate,
    GamificationResponse, UserStatsResponse, UserStatsUpdate, UserStatsRangeResponse
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


# ============================================================
# DAILY STATS — GET TODAY'S STATS
# ============================================================

@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get today's user stats.
    Returns cached daily stats if available, otherwise computes fresh.
    """
    today = date.today()
    
    # Try to get today's stats from cache
    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date == today
    ).first()
    
    if stats:
        return {
            "date": stats.date.isoformat(),
            "xp": stats.xp,
            "level": stats.level,
            "streak": stats.streak,
            "accuracy": stats.accuracy,
            "sessions": stats.sessions,
            "totalQuestions": stats.total_questions,
            "correct": stats.correct,
            "wrong": stats.wrong,
            "studyTime": stats.study_time_minutes,
            "fromCache": True,
            "cachedAt": stats.updated_at.isoformat()
        }
    
    # Compute fresh stats from user data
    return await compute_user_stats(current_user.id, db)


async def compute_user_stats(user_id: int, db: Session):
    """Compute user stats from scratch"""
    today = date.today()
    
    # Get all completed sessions
    sessions = db.query(PracticeSession).filter(
        PracticeSession.user_id == user_id,
        PracticeSession.is_completed == True
    ).all()
    
    # Get gamification stats
    gamification = db.query(UserStats).filter(
        UserStats.user_id == user_id
    ).first()
    
    # Calculate stats
    total_questions = sum(s.total_questions or 0 for s in sessions)
    correct = sum(s.correct_answers or 0 for s in sessions)
    wrong = sum(s.wrong_answers or 0 for s in sessions)
    accuracy = (correct / total_questions * 100) if total_questions > 0 else 0
    
    # Get today's sessions
    today_sessions = [
        s for s in sessions 
        if s.completed_at and s.completed_at.date() == today
    ]
    
    # Calculate study time
    study_time_minutes = sum(
        (s.time_taken or 0) for s in today_sessions
    ) // 60
    
    result = {
        "date": today.isoformat(),
        "xp": gamification.xp if gamification else 0,
        "level": gamification.level if gamification else 1,
        "streak": gamification.streak if gamification else 0,
        "accuracy": round(accuracy, 1),
        "sessions": len(today_sessions),
        "totalQuestions": total_questions,
        "correct": correct,
        "wrong": wrong,
        "studyTime": study_time_minutes,
        "fromCache": False
    }
    
    # Save to cache for future
    await save_daily_stats(user_id, result, db)
    
    return result


# ============================================================
# DAILY STATS — SAVE
# ============================================================

@router.post("/stats")
async def save_user_stats(
    stats_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save today's user stats to the database.
    """
    today = date.today()
    
    # Get or create daily stats
    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date == today
    ).first()
    
    if stats:
        stats.xp = stats_data.get("xp", stats.xp)
        stats.level = stats_data.get("level", stats.level)
        stats.streak = stats_data.get("streak", stats.streak)
        stats.accuracy = stats_data.get("accuracy", stats.accuracy)
        stats.sessions = stats_data.get("sessions", stats.sessions)
        stats.total_questions = stats_data.get("totalQuestions", stats.total_questions)
        stats.correct = stats_data.get("correct", stats.correct)
        stats.wrong = stats_data.get("wrong", stats.wrong)
        stats.study_time_minutes = stats_data.get("studyTime", stats.study_time_minutes)
        stats.updated_at = datetime.utcnow()
    else:
        stats = UserDailyStats(
            user_id=current_user.id,
            date=today,
            xp=stats_data.get("xp", 0),
            level=stats_data.get("level", 1),
            streak=stats_data.get("streak", 0),
            accuracy=stats_data.get("accuracy", 0),
            sessions=stats_data.get("sessions", 0),
            total_questions=stats_data.get("totalQuestions", 0),
            correct=stats_data.get("correct", 0),
            wrong=stats_data.get("wrong", 0),
            study_time_minutes=stats_data.get("studyTime", 0)
        )
        db.add(stats)
    
    db.commit()
    
    return {
        "success": True,
        "date": today.isoformat(),
        "saved": True
    }


async def save_daily_stats(user_id: int, stats_data: dict, db: Session):
    """Helper function to save daily stats"""
    today = date.today()
    
    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == user_id,
        UserDailyStats.date == today
    ).first()
    
    if stats:
        stats.xp = stats_data.get("xp", stats.xp)
        stats.level = stats_data.get("level", stats.level)
        stats.streak = stats_data.get("streak", stats.streak)
        stats.accuracy = stats_data.get("accuracy", stats.accuracy)
        stats.sessions = stats_data.get("sessions", stats.sessions)
        stats.total_questions = stats_data.get("totalQuestions", stats.total_questions)
        stats.correct = stats_data.get("correct", stats.correct)
        stats.wrong = stats_data.get("wrong", stats.wrong)
        stats.study_time_minutes = stats_data.get("studyTime", stats.study_time_minutes)
        stats.updated_at = datetime.utcnow()
    else:
        stats = UserDailyStats(
            user_id=user_id,
            date=today,
            xp=stats_data.get("xp", 0),
            level=stats_data.get("level", 1),
            streak=stats_data.get("streak", 0),
            accuracy=stats_data.get("accuracy", 0),
            sessions=stats_data.get("sessions", 0),
            total_questions=stats_data.get("totalQuestions", 0),
            correct=stats_data.get("correct", 0),
            wrong=stats_data.get("wrong", 0),
            study_time_minutes=stats_data.get("studyTime", 0)
        )
        db.add(stats)
    
    db.commit()


# ============================================================
# DAILY STATS — GET RANGE (Weekly/Monthly)
# ============================================================

@router.get("/stats/range")
async def get_stats_range(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user stats for a date range.
    """
    start_date = date.today() - timedelta(days=days)
    
    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date >= start_date
    ).order_by(UserDailyStats.date).all()
    
    return {
        "range": f"Last {days} days",
        "start": start_date.isoformat(),
        "end": date.today().isoformat(),
        "stats": [
            {
                "date": s.date.isoformat(),
                "xp": s.xp,
                "level": s.level,
                "streak": s.streak,
                "accuracy": s.accuracy,
                "sessions": s.sessions,
                "studyTime": s.study_time_minutes
            }
            for s in stats
        ],
        "total": len(stats)
    }


# ============================================================
# DAILY STATS — GET TODAY'S PROGRESS (Quick Check)
# ============================================================

@router.get("/stats/today")
async def get_today_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick check: how many sessions today?
    """
    today = date.today()
    
    # Count today's sessions
    session_count = db.query(PracticeSession).filter(
        PracticeSession.user_id == current_user.id,
        func.date(PracticeSession.completed_at) == today,
        PracticeSession.is_completed == True
    ).count()
    
    # Get today's stats
    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date == today
    ).first()
    
    # Get gamification for streak
    gamification = db.query(UserStats).filter(
        UserStats.user_id == current_user.id
    ).first()
    
    return {
        "sessions_today": session_count,
        "goal": 5,  # Daily goal
        "remaining": max(0, 5 - session_count),
        "xp_today": stats.xp if stats else 0,
        "streak": gamification.streak if gamification else 0,
        "accuracy": stats.accuracy if stats else 0
    }


# ============================================================
# DAILY STATS — WEEKLY AGGREGATED
# ============================================================

@router.get("/stats/weekly")
async def get_weekly_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get weekly aggregated stats (last 7 days).
    """
    start_date = date.today() - timedelta(days=7)
    
    # Get stats for last 7 days
    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date >= start_date
    ).all()
    
    # If no daily stats, compute from sessions
    if not stats:
        sessions = db.query(PracticeSession).filter(
            PracticeSession.user_id == current_user.id,
            func.date(PracticeSession.completed_at) >= start_date,
            PracticeSession.is_completed == True
        ).all()
        
        # Group by date
        daily_data = {}
        for s in sessions:
            if s.completed_at:
                day = s.completed_at.date().isoformat()
                if day not in daily_data:
                    daily_data[day] = {"sessions": 0, "xp": 0, "accuracy": 0, "correct": 0, "total": 0}
                daily_data[day]["sessions"] += 1
                daily_data[day]["correct"] += s.correct_answers or 0
                daily_data[day]["total"] += s.total_questions or 0
        
        # Format response
        weekly_data = []
        for day, data in daily_data.items():
            acc = (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0
            weekly_data.append({
                "day": day,
                "sessions": data["sessions"],
                "accuracy": round(acc, 1),
                "xp": data["sessions"] * 10  # Estimate
            })
        
        return {
            "range": "Last 7 days",
            "start": start_date.isoformat(),
            "end": date.today().isoformat(),
            "stats": weekly_data,
            "total_sessions": sum(d["sessions"] for d in weekly_data),
            "avg_accuracy": round(sum(d["accuracy"] for d in weekly_data) / len(weekly_data), 1) if weekly_data else 0
        }
    
    return {
        "range": "Last 7 days",
        "start": start_date.isoformat(),
        "end": date.today().isoformat(),
        "stats": [
            {
                "day": s.date.isoformat(),
                "sessions": s.sessions,
                "accuracy": s.accuracy,
                "xp": s.xp
            }
            for s in stats
        ],
        "total_sessions": sum(s.sessions for s in stats),
        "avg_accuracy": round(sum(s.accuracy for s in stats) / len(stats), 1) if stats else 0
    }


# ============================================================
# DAILY STATS — CLEANUP OLD STATS
# ============================================================

@router.delete("/stats/old")
async def cleanup_old_stats(
    days_to_keep: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cleanup stats older than specified days.
    """
    cutoff = date.today() - timedelta(days=days_to_keep)
    
    deleted = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date < cutoff
    ).delete()
    
    db.commit()
    
    return {
        "success": True,
        "deleted": deleted,
        "days_kept": days_to_keep,
        "cutoff_date": cutoff.isoformat()
    }
