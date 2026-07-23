# ============================================================
# routes/feedback.py — Feedback & Contributions
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import User, Feedback, Contribution
from schemas import (
    FeedbackCreate, FeedbackResponse, FeedbackListResponse,
    ContributionCreate, ContributionResponse, ContributionListResponse,
    ContributionApproveResponse, ContributionRejectRequest
)
from dependencies import get_current_user, get_current_admin_user

router = APIRouter()


# ============================================================
# 1. FEEDBACK — Submit Feedback
# ============================================================

@router.post("/feedback")
async def submit_feedback(
    data: FeedbackCreate,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback (logged-in or anonymous)"""
    
    feedback = Feedback(
        user_id=current_user.id if current_user else None,
        type=data.type,
        message=data.message,
        rating=data.rating,
        email=data.email
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return {
        "success": True,
        "data": {
            "id": feedback.id,
            "type": feedback.type,
            "message": feedback.message,
            "rating": feedback.rating,
            "email": feedback.email,
            "userId": feedback.user_id,
            "createdAt": feedback.created_at
        }
    }


# ============================================================
# 2. FEEDBACK — Get All (Admin Only)
# ============================================================

@router.get("/feedback", response_model=FeedbackListResponse)
async def get_all_feedback(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all feedback (Admin only)"""
    
    feedbacks = db.query(Feedback).order_by(
        Feedback.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    total = db.query(Feedback).count()
    
    return {
        "success": True,
        "data": {
            "feedback": [
                {
                    "id": f.id,
                    "type": f.type,
                    "message": f.message,
                    "rating": f.rating,
                    "email": f.email,
                    "userId": f.user_id,
                    "user": {
                        "id": f.user.id,
                        "username": f.user.username
                    } if f.user else None,
                    "createdAt": f.created_at
                }
                for f in feedbacks
            ],
            "total": total
        }
    }


# ============================================================
# 3. FEEDBACK — Delete (Admin Only)
# ============================================================

@router.delete("/feedback/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete feedback (Admin only)"""
    
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(404, "Feedback not found")
    
    db.delete(feedback)
    db.commit()
    
    return {"success": True, "message": "Feedback deleted successfully"}


# ============================================================
# 4. CONTRIBUTIONS — Submit Contribution
# ============================================================

@router.post("/cutoffs/contribute")
async def submit_contribution(
    data: ContributionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a cutoff contribution"""
    
    contribution = Contribution(
        user_id=current_user.id,
        university=data.university,
        course=data.course,
        year=data.year,
        cutoff=data.cutoff,
        exam_type=data.exam_type,
        source=data.source,
        status="pending"
    )
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    
    return {
        "success": True,
        "data": {
            "id": contribution.id,
            "university": contribution.university,
            "course": contribution.course,
            "year": contribution.year,
            "cutoff": contribution.cutoff,
            "examType": contribution.exam_type,
            "source": contribution.source,
            "status": contribution.status,
            "userId": contribution.user_id,
            "createdAt": contribution.created_at
        }
    }


# ============================================================
# 5. CONTRIBUTIONS — Get My Contributions
# ============================================================

@router.get("/cutoffs/my-contributions")
async def get_my_contributions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's contributions"""
    
    contributions = db.query(Contribution).filter(
        Contribution.user_id == current_user.id
    ).order_by(Contribution.created_at.desc()).all()
    
    return {
        "success": True,
        "data": {
            "contributions": [
                {
                    "id": c.id,
                    "university": c.university,
                    "course": c.course,
                    "year": c.year,
                    "cutoff": c.cutoff,
                    "examType": c.exam_type,
                    "source": c.source,
                    "status": c.status,
                    "createdAt": c.created_at
                }
                for c in contributions
            ],
            "total": len(contributions)
        }
    }


# ============================================================
# 6. CONTRIBUTIONS — Get All (Admin Only)
# ============================================================

@router.get("/admin/contributions")
async def get_all_contributions(
    status: Optional[str] = Query(None, regex="^(pending|approved|rejected)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all contributions (Admin only)"""
    
    query = db.query(Contribution)
    if status:
        query = query.filter(Contribution.status == status)
    
    contributions = query.order_by(
        Contribution.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    total = db.query(Contribution).count()
    pending = db.query(Contribution).filter(Contribution.status == "pending").count()
    approved = db.query(Contribution).filter(Contribution.status == "approved").count()
    rejected = db.query(Contribution).filter(Contribution.status == "rejected").count()
    
    return {
        "success": True,
        "data": {
            "contributions": [
                {
                    "id": c.id,
                    "university": c.university,
                    "course": c.course,
                    "year": c.year,
                    "cutoff": c.cutoff,
                    "examType": c.exam_type,
                    "source": c.source,
                    "status": c.status,
                    "userId": c.user_id,
                    "user": {
                        "id": c.user.id,
                        "username": c.user.username
                    },
                    "createdAt": c.created_at,
                    "approvedAt": c.approved_at,
                    "rejectedAt": c.rejected_at,
                    "rejectionReason": c.rejection_reason
                }
                for c in contributions
            ],
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected
        }
    }


# ============================================================
# 7. CONTRIBUTIONS — Approve (Admin Only)
# ============================================================

@router.post("/admin/contributions/{contribution_id}/approve")
async def approve_contribution(
    contribution_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Approve a contribution (Admin only)"""
    
    contribution = db.query(Contribution).filter(
        Contribution.id == contribution_id
    ).first()
    
    if not contribution:
        raise HTTPException(404, "Contribution not found")
    
    if contribution.status != "pending":
        raise HTTPException(400, f"Contribution already {contribution.status}")
    
    contribution.status = "approved"
    contribution.approved_by = current_user.id
    contribution.approved_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "data": {
            "id": contribution.id,
            "status": contribution.status,
            "approvedAt": contribution.approved_at,
            "approvedBy": contribution.approved_by
        }
    }


# ============================================================
# 8. CONTRIBUTIONS — Reject (Admin Only)
# ============================================================

@router.post("/admin/contributions/{contribution_id}/reject")
async def reject_contribution(
    contribution_id: int,
    data: ContributionRejectRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reject a contribution (Admin only)"""
    
    contribution = db.query(Contribution).filter(
        Contribution.id == contribution_id
    ).first()
    
    if not contribution:
        raise HTTPException(404, "Contribution not found")
    
    if contribution.status != "pending":
        raise HTTPException(400, f"Contribution already {contribution.status}")
    
    contribution.status = "rejected"
    contribution.rejected_by = current_user.id
    contribution.rejected_at = datetime.utcnow()
    contribution.rejection_reason = data.reason
    db.commit()
    
    return {
        "success": True,
        "data": {
            "id": contribution.id,
            "status": contribution.status,
            "rejectedAt": contribution.rejected_at,
            "rejectedBy": contribution.rejected_by,
            "reason": contribution.rejection_reason
        }
    }


# ============================================================
# 9. ADMIN STATS — Dashboard (Enhanced)
# ============================================================

@router.get("/admin/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get admin dashboard stats"""
    
    from models import UserStats, Session, Mistake, Bookmark, Subscription
    
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = total_users - active_users
    
    # New users today
    today = datetime.utcnow().date()
    new_users_today = db.query(User).filter(
        func.date(User.created_at) == today
    ).count()
    
    # Sessions
    total_sessions = db.query(Session).count()
    sessions_today = db.query(Session).filter(
        func.date(Session.completed_at) == today
    ).count()
    
    # Mistakes & Bookmarks
    total_mistakes = db.query(Mistake).count()
    total_bookmarks = db.query(Bookmark).count()
    
    # Feedback & Contributions
    total_feedback = db.query(Feedback).count()
    total_contributions = db.query(Contribution).count()
    pending_contributions = db.query(Contribution).filter(Contribution.status == "pending").count()
    approved_contributions = db.query(Contribution).filter(Contribution.status == "approved").count()
    rejected_contributions = db.query(Contribution).filter(Contribution.status == "rejected").count()
    
    # Subscriptions
    subscriptions = db.query(Subscription).all()
    subscription_breakdown = {
        "free": sum(1 for s in subscriptions if s.plan == "free"),
        "foundation": sum(1 for s in subscriptions if s.plan == "foundation"),
        "premium": sum(1 for s in subscriptions if s.plan == "premium"),
        "pro": sum(1 for s in subscriptions if s.plan == "pro")
    }
    
    return {
        "success": True,
        "data": {
            "totalUsers": total_users,
            "activeUsers": active_users,
            "inactiveUsers": inactive_users,
            "newUsersToday": new_users_today,
            "totalSessions": total_sessions,
            "sessionsToday": sessions_today,
            "totalMistakes": total_mistakes,
            "totalBookmarks": total_bookmarks,
            "totalFeedback": total_feedback,
            "totalContributions": total_contributions,
            "pendingContributions": pending_contributions,
            "approvedContributions": approved_contributions,
            "rejectedContributions": rejected_contributions,
            "subscriptionBreakdown": subscription_breakdown
        }
    }


# ============================================================
# 10. ADMIN USERS — Get Users
# ============================================================

@router.get("/admin/users")
async def get_admin_users(
    search: Optional[str] = None,
    status: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get users for admin panel"""
    
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )
    
    if status:
        is_active = status == "active"
        query = query.filter(User.is_active == is_active)
    
    if tier:
        query = query.filter(User.tier == tier)
    
    total = query.count()
    users = query.offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "data": {
            "users": [
                {
                    "id": u.id,
                    "firstName": u.first_name,
                    "lastName": u.last_name,
                    "username": u.username,
                    "email": u.email,
                    "school": u.school,
                    "country": u.country,
                    "exam": u.exam,
                    "tier": u.tier.value if hasattr(u.tier, 'value') else u.tier,
                    "xp": u.stats.xp if u.stats else 0,
                    "level": u.stats.level if u.stats else 1,
                    "streak": u.stats.streak if u.stats else 0,
                    "accuracy": u.stats.accuracy if u.stats else 0,
                    "status": "active" if u.is_active else "inactive",
                    "joinedAt": u.created_at,
                    "lastActive": u.last_login
                }
                for u in users
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    }
