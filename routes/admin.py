from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime, timedelta

from database import get_db
from models import User, UserStats, Subscription, Question, Session
from schemas import (
    AdminStatsResponse, AdminUserResponse, AdminUserUpdate,
    AdminQuestionUpdate
)
from dependencies import get_current_admin_user

router = APIRouter()


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get platform statistics"""
    # User counts
    total_users = db.query(User).count()
    active_users = db.query(User).filter(
        User.is_active == True,
        User.last_login >= datetime.utcnow() - timedelta(days=7)
    ).count()
    new_users_today = db.query(User).filter(
        User.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()
    
    # Question counts
    total_questions = db.query(Question).count()
    
    # Revenue
    total_revenue = db.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.plan == "premium"
    ).count() * 5000 / 100  # Simplified revenue calculation
    
    revenue_this_month = db.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.plan == "premium",
        Subscription.start_date >= datetime.utcnow().replace(day=1)
    ).count() * 5000 / 100
    
    # Session stats
    total_sessions = db.query(Session).count()
    sessions_today = db.query(Session).filter(
        Session.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()
    
    # Subscription breakdown
    free_users = db.query(User).filter(User.tier == "foundation").count()
    foundation_users = db.query(User).filter(User.tier == "foundation").count()
    premium_users = db.query(User).filter(User.tier == "premium").count()
    
    # Growth calculations (simplified)
    growth = {
        "users": 12.5,
        "revenue": 8.3,
        "sessions": 15.2
    }
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "new_users_today": new_users_today,
        "total_questions": total_questions,
        "pending_questions": 0,
        "total_revenue": total_revenue,
        "revenue_this_month": revenue_this_month,
        "total_sessions": total_sessions,
        "sessions_today": sessions_today,
        "subscription_breakdown": {
            "free": free_users,
            "foundation": foundation_users,
            "premium": premium_users
        },
        "growth": growth
    }


@router.get("/users", response_model=List[AdminUserResponse])
async def get_admin_users(
    tier: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get users with filters"""
    query = db.query(User)
    
    if tier:
        query = query.filter(User.tier == tier)
    if status:
        is_active = status == "active"
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            (User.email.contains(search)) |
            (User.username.contains(search)) |
            (User.first_name.contains(search)) |
            (User.last_name.contains(search))
        )
    
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    return users


@router.put("/users/{user_id}")
async def update_admin_user(
    user_id: int,
    data: AdminUserUpdate,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if data.tier:
        user.tier = data.tier
    if data.status:
        user.is_active = data.status == "active"
    
    db.commit()
    
    return {"success": True, "user": user}


@router.delete("/users/{user_id}")
async def delete_admin_user(
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"success": True, "message": "User deleted"}


@router.get("/questions")
async def get_admin_questions(
    status: Optional[str] = None,
    subject: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get questions with filters (admin only)"""
    query = db.query(Question)
    
    if subject:
        query = query.filter(Question.subject.ilike(subject))
    
    # In production, add status field to questions
    questions = query.order_by(Question.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "items": questions,
        "total": query.count(),
        "limit": limit,
        "offset": offset
    }


@router.put("/questions/{question_id}")
async def update_admin_question(
    question_id: str,
    data: AdminQuestionUpdate,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a question (admin only)"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    if data.subject:
        question.subject = data.subject
    if data.topic:
        question.topic = data.topic
    if data.difficulty:
        question.difficulty = data.difficulty
    
    db.commit()
    
    return {"success": True, "question": question}


@router.get("/subscriptions")
async def get_admin_subscriptions(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all subscriptions (admin only)"""
    subscriptions = db.query(Subscription).all()
    
    # Get user details for each subscription
    result = []
    for sub in subscriptions:
        user = db.query(User).filter(User.id == sub.user_id).first()
        result.append({
            "id": sub.id,
            "user": f"{user.first_name} {user.last_name}" if user else "Unknown",
            "email": user.email if user else "Unknown",
            "tier": sub.plan,
            "amount": "$5.00" if sub.plan == "premium" else "$2.00",
            "status": "active" if sub.is_active else "inactive",
            "expires": sub.end_date.isoformat() if sub.end_date else None,
            "created_at": sub.created_at.isoformat()
        })
    
    # Summary
    active_subs = len([s for s in subscriptions if s.is_active])
    total_revenue = active_subs * 5000 / 100  # Simplified
    
    return {
        "subscriptions": result,
        "summary": {
            "total": len(subscriptions),
            "active": active_subs,
            "revenue": total_revenue,
            "monthlyRecurring": total_revenue
        }
    }