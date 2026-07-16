from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_
from typing import Optional, List
from datetime import datetime, timedelta

from database import get_db
from models import User, UserStats, Duel, Session as PracticeSession
from dependencies import get_current_user, get_current_admin_user

router = APIRouter()


@router.get("/global")
async def get_global_leaderboard(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get global leaderboard with proper XP calculation"""
    
    # ✅ OPTIMIZED: Single query with join
    results = db.query(
        User.id,
        User.username,
        User.full_name,
        User.avatar,
        User.school,
        UserStats.xp,
        UserStats.level,
        UserStats.current_streak,
        UserStats.longest_streak,
        # Calculate accuracy from all practice sessions
        func.coalesce(
            func.sum(PracticeSession.correct) * 100.0 / 
            func.nullif(func.sum(PracticeSession.total_questions), 0),
            0
        ).label("accuracy")
    ).join(
        UserStats, User.id == UserStats.user_id, isouter=True
    ).outerjoin(
        PracticeSession, User.id == PracticeSession.user_id
    ).filter(
        User.is_active == True
    ).group_by(
        User.id, UserStats.id
    ).order_by(
        desc(UserStats.xp),
        desc(UserStats.current_streak),
        desc("accuracy")
    ).offset(offset).limit(limit).all()
    
    # Format response
    leaderboard = []
    for idx, row in enumerate(results, start=offset + 1):
        leaderboard.append({
            "rank": idx,
            "user_id": row.id,
            "username": row.username,
            "full_name": row.full_name,
            "avatar": row.avatar,
            "school": row.school,
            "xp": row.xp or 0,
            "level": row.level or 1,
            "streak": row.current_streak or 0,
            "longest_streak": row.longest_streak or 0,
            "accuracy": round(row.accuracy or 0, 1)
        })
    
    # Get total count for pagination
    total_count = db.query(User).filter(User.is_active == True).count()
    
    return {
        "leaderboard": leaderboard,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "next": offset + limit < total_count
    }


@router.get("/school")
async def get_school_leaderboard(
    school: str,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get leaderboard filtered by school"""
    
    results = db.query(
        User.id,
        User.username,
        User.full_name,
        User.avatar,
        User.school,
        UserStats.xp,
        UserStats.level,
        UserStats.current_streak,
        func.coalesce(
            func.sum(PracticeSession.correct) * 100.0 / 
            func.nullif(func.sum(PracticeSession.total_questions), 0),
            0
        ).label("accuracy")
    ).join(
        UserStats, User.id == UserStats.user_id, isouter=True
    ).outerjoin(
        PracticeSession, User.id == PracticeSession.user_id
    ).filter(
        User.is_active == True,
        User.school.ilike(f"%{school}%")
    ).group_by(
        User.id, UserStats.id
    ).order_by(
        desc(UserStats.xp)
    ).limit(limit).all()
    
    leaderboard = []
    for idx, row in enumerate(results, start=1):
        leaderboard.append({
            "rank": idx,
            "user_id": row.id,
            "username": row.username,
            "full_name": row.full_name,
            "avatar": row.avatar,
            "school": row.school,
            "xp": row.xp or 0,
            "level": row.level or 1,
            "streak": row.current_streak or 0,
            "accuracy": round(row.accuracy or 0, 1)
        })
    
    return leaderboard


@router.get("/friends")
async def get_friends_leaderboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=50)
):
    """Get leaderboard for user's friends/connections"""
    
    # Get user's friends (simplified - you'll need a Friends table)
    # For now, get users from same school
    friends = db.query(User).filter(
        User.is_active == True,
        User.school == current_user.school,
        User.id != current_user.id
    ).limit(limit).all()
    
    friend_ids = [f.id for f in friends]
    
    # Include current user
    friend_ids.append(current_user.id)
    
    results = db.query(
        User.id,
        User.username,
        User.full_name,
        User.avatar,
        User.school,
        UserStats.xp,
        UserStats.level,
        UserStats.current_streak
    ).join(
        UserStats, User.id == UserStats.user_id
    ).filter(
        User.id.in_(friend_ids)
    ).order_by(
        desc(UserStats.xp)
    ).all()
    
    leaderboard = []
    for idx, row in enumerate(results, start=1):
        is_current = row.id == current_user.id
        leaderboard.append({
            "rank": idx,
            "user_id": row.id,
            "username": row.username,
            "full_name": row.full_name,
            "avatar": row.avatar,
            "school": row.school,
            "xp": row.xp or 0,
            "level": row.level or 1,
            "streak": row.current_streak or 0,
            "is_current_user": is_current
        })
    
    return leaderboard


@router.get("/subject")
async def get_subject_leaderboard(
    subject: str,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100)
):
    """Get leaderboard for a specific subject"""
    
    # This requires a SubjectStats table
    # For now, use practice sessions
    results = db.query(
        User.id,
        User.username,
        User.full_name,
        User.avatar,
        UserStats.xp,
        func.count(PracticeSession.id).label("sessions"),
        func.sum(PracticeSession.correct).label("correct"),
        func.sum(PracticeSession.total_questions).label("total")
    ).join(
        UserStats, User.id == UserStats.user_id
    ).join(
        PracticeSession, User.id == PracticeSession.user_id
    ).filter(
        User.is_active == True,
        PracticeSession.subject.ilike(subject),
        PracticeSession.completed_at.isnot(None)
    ).group_by(
        User.id, UserStats.id
    ).having(
        func.sum(PracticeSession.total_questions) > 0
    ).order_by(
        desc(func.sum(PracticeSession.correct))
    ).limit(limit).all()
    
    leaderboard = []
    for idx, row in enumerate(results, start=1):
        accuracy = (row.correct / row.total * 100) if row.total > 0 else 0
        leaderboard.append({
            "rank": idx,
            "user_id": row.id,
            "username": row.username,
            "full_name": row.full_name,
            "avatar": row.avatar,
            "xp": row.xp or 0,
            "sessions": row.sessions or 0,
            "correct": row.correct or 0,
            "total": row.total or 0,
            "accuracy": round(accuracy, 1)
        })
    
    return leaderboard


@router.get("")
async def get_leaderboard(
    filter_type: str = Query("global", regex="^(global|school|friends|subject)$"),
    subject: Optional[str] = None,
    school: Optional[str] = None,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Combined leaderboard endpoint"""
    
    if filter_type == "global":
        return await get_global_leaderboard(db, limit, 0)
    elif filter_type == "school":
        if not school:
            school = current_user.school
        return await get_school_leaderboard(school, db, limit, current_user)
    elif filter_type == "friends":
        return await get_friends_leaderboard(current_user, db, limit)
    elif filter_type == "subject":
        if not subject:
            raise HTTPException(400, "Subject is required for subject filter")
        return await get_subject_leaderboard(subject, db, limit)
    
    return {"error": "Invalid filter"}


@router.get("/user/{user_id}")
async def get_user_rank(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific user's rank and stats"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Get user stats
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    
    # Calculate rank
    rank = db.query(UserStats).filter(
        UserStats.xp > (stats.xp if stats else 0)
    ).count() + 1
    
    total_users = db.query(User).filter(User.is_active == True).count()
    
    return {
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "avatar": user.avatar,
        "school": user.school,
        "rank": rank,
        "total_users": total_users,
        "xp": stats.xp if stats else 0,
        "level": stats.level if stats else 1,
        "streak": stats.current_streak if stats else 0,
        "top_percent": round((1 - rank / total_users) * 100, 1) if total_users > 0 else 0
    }


@router.get("/weekly")
async def get_weekly_leaderboard(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=50)
):
    """Get weekly XP leaders"""
    
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Get XP earned in the last week from practice sessions
    weekly_xp = db.query(
        User.id,
        User.username,
        User.full_name,
        User.avatar,
        func.sum(PracticeSession.xp_earned).label("weekly_xp")
    ).join(
        User, PracticeSession.user_id == User.id
    ).filter(
        PracticeSession.completed_at >= week_ago,
        User.is_active == True
    ).group_by(
        User.id
    ).order_by(
        desc("weekly_xp")
    ).limit(limit).all()
    
    results = []
    for idx, row in enumerate(weekly_xp, start=1):
        results.append({
            "rank": idx,
            "user_id": row.id,
            "username": row.username,
            "full_name": row.full_name,
            "avatar": row.avatar,
            "weekly_xp": row.weekly_xp or 0
        })
    
    return results
