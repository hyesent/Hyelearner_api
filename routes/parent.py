from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import uuid

from database import get_db
from models import User, ParentLink, UserStats, Subscription, Session, TopicMastery
from schemas import (
    ParentLinkRequest, ParentLinkResponse,
    ParentCodeResponse, ParentStatusResponse,
    ChildAnalyticsResponse
)
from dependencies import get_current_user

router = APIRouter()


# ============================================================
# 1. GENERATE CODE — Child App
# ============================================================

@router.post("/generate-code")
async def generate_parent_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Child generates a 6-character code for parent to link.
    If code already exists, return existing code.
    """
    
    # Check if user already has active or pending link
    existing = db.query(ParentLink).filter(
        ParentLink.child_id == current_user.id,
        ParentLink.status.in_(['pending', 'active'])
    ).first()
    
    if existing:
        # Return existing code instead of generating new one
        return {
            "success": True,
            "data": {
                "code": existing.code,
                "expiresAt": existing.expires_at.isoformat() if existing.expires_at else None
            }
        }
    
    # Generate unique 6-character code
    code = secrets.token_hex(3).upper()
    
    # Ensure code is unique
    while db.query(ParentLink).filter(ParentLink.code == code).first():
        code = secrets.token_hex(3).upper()
    
    # Create link record
    link = ParentLink(
        child_id=current_user.id,
        parent_id=None,  # NULL until parent links
        code=code,
        status='pending',
        expires_at=datetime.utcnow() + timedelta(days=7),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    
    return {
        "success": True,
        "data": {
            "code": link.code,
            "expiresAt": link.expires_at.isoformat()
        }
    }


# ============================================================
# 2. LINK CHILD — Child App (Child enters parent's code)
# ============================================================

@router.post("/link")
async def link_child(
    request: ParentLinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Child enters code from parent to link.
    """
    
    # Find the pending link by code
    link = db.query(ParentLink).filter(
        ParentLink.code == request.code.upper(),
        ParentLink.status == 'pending',
        ParentLink.expires_at > datetime.utcnow()
    ).first()
    
    if not link:
        raise HTTPException(404, detail="Invalid or expired code")
    
    # Check if user is already linked to a parent
    existing = db.query(ParentLink).filter(
        ParentLink.child_id == current_user.id,
        ParentLink.status == 'active'
    ).first()
    
    if existing:
        raise HTTPException(400, detail="Already linked to a parent")
    
    # Link the child
    link.child_id = current_user.id
    link.parent_id = current_user.id  # In this flow, parent is the one who generated code
    link.status = 'active'
    link.updated_at = datetime.utcnow()
    db.commit()
    
    # Get updated stats for response
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    
    return {
        "success": True,
        "data": {
            "linked": True,
            "linkedAt": link.updated_at.isoformat(),
            "studentId": current_user.id,
            "student": {
                "name": f"{current_user.first_name} {current_user.last_name}",
                "streak": stats.streak if stats else 0,
                "xp": stats.xp if stats else 0,
                "accuracy": stats.accuracy if stats else 0
            }
        }
    }


# ============================================================
# 3. GET STATUS — Child App
# ============================================================

@router.get("/status")
async def get_parent_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if child is linked to a parent.
    Works for both Child and Parent roles.
    """
    
    # Check if user is a parent (has children)
    if current_user.role == "parent":
        children = db.query(ParentLink).filter(
            ParentLink.parent_id == current_user.id,
            ParentLink.status == 'active'
        ).all()
        
        # Get child details
        child_data = []
        for link in children:
            child = db.query(User).filter(User.id == link.child_id).first()
            if child:
                child_data.append({
                    "id": child.id,
                    "name": f"{child.first_name} {child.last_name}",
                    "linkedAt": link.created_at.isoformat()
                })
        
        return {
            "success": True,
            "data": {
                "linked": len(child_data) > 0,
                "children": child_data
            }
        }
    
    # Check if user is a child (has parent)
    link = db.query(ParentLink).filter(
        ParentLink.child_id == current_user.id,
        ParentLink.status == 'active'
    ).first()
    
    if link:
        parent = db.query(User).filter(User.id == link.parent_id).first()
        return {
            "success": True,
            "data": {
                "linked": True,
                "parent": {
                    "id": parent.id,
                    "name": f"{parent.first_name} {parent.last_name}",
                    "email": parent.email
                },
                "children": []
            }
        }
    
    return {
        "success": True,
        "data": {
            "linked": False,
            "children": []
        }
    }


# ============================================================
# 4. GET STUDENT ANALYTICS — Child App (View own stats)
# ============================================================

@router.get("/analytics/{student_id}")
async def get_student_analytics(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get student analytics.
    - Child can view their own stats
    - Parent can view linked child's stats
    """
    
    # Check if user is viewing themselves
    if current_user.id == student_id:
        student = current_user
    else:
        # Check if user is parent of this student
        link = db.query(ParentLink).filter(
            ParentLink.child_id == student_id,
            ParentLink.parent_id == current_user.id,
            ParentLink.status == 'active'
        ).first()
        
        if not link:
            raise HTTPException(403, detail="Not authorized to view this student")
        
        student = db.query(User).filter(User.id == student_id).first()
    
    if not student:
        raise HTTPException(404, detail="Student not found")
    
    # Get stats
    stats = db.query(UserStats).filter(UserStats.user_id == student_id).first()
    
    # Get subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == student_id,
        Subscription.is_active == True
    ).first()
    
    # Get sessions for study time
    sessions = db.query(Session).filter(
        Session.user_id == student_id,
        Session.is_completed == True
    ).all()
    
    # Calculate study time
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    study_today = sum(s.time_taken for s in sessions if s.completed_at and s.completed_at.date() == today)
    study_week = sum(s.time_taken for s in sessions if s.completed_at and s.completed_at.date() >= week_ago)
    study_month = sum(s.time_taken for s in sessions if s.completed_at and s.completed_at.date() >= month_ago)
    
    # Get topic mastery for subject readiness
    mastery = db.query(TopicMastery).filter(TopicMastery.user_id == student_id).all()
    
    # Get distinct subjects
    subjects = {}
    for m in mastery:
        if m.subject not in subjects:
            subjects[m.subject] = {
                "name": m.subject,
                "readiness": 50  # Default
            }
        # Calculate readiness based on mastery score
        if m.total > 0:
            readiness = (m.correct / m.total) * 100
            subjects[m.subject]["readiness"] = round(readiness, 1)
    
    # If no subjects, add default ones
    if not subjects:
        default_subjects = ["Mathematics", "English", "Physics", "Chemistry"]
        for s in default_subjects:
            subjects[s] = {"name": s, "readiness": 50}
    
    return {
        "success": True,
        "data": {
            "student": {
                "id": student.id,
                "name": f"{student.first_name} {student.last_name}",
                "streak": stats.streak if stats else 0,
                "xp": stats.xp if stats else 0,
                "level": stats.level if stats else 1,
                "accuracy": stats.accuracy if stats else 0,
                "school": student.school,
                "exam": student.exam,
                "subscription": {
                    "plan": subscription.plan if subscription else "free",
                    "status": "active" if subscription and subscription.is_active else "inactive",
                    "expires": subscription.end_date.isoformat() if subscription and subscription.end_date else None
                },
                "studyTime": {
                    "today": round(study_today / 60, 1),  # Convert to hours
                    "week": round(study_week / 60, 1),
                    "month": round(study_month / 60, 1)
                },
                "subjects": list(subjects.values())
            }
        }
    }


# ============================================================
# 5. UNLINK — Child App
# ============================================================

@router.post("/unlink")
async def unlink_parent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Child disconnects from parent.
    """
    
    link = db.query(ParentLink).filter(
        ParentLink.child_id == current_user.id,
        ParentLink.status == 'active'
    ).first()
    
    if not link:
        raise HTTPException(404, detail="No active link found")
    
    link.status = 'unlinked'
    link.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Unlinked successfully"
    }


# ============================================================
# 6. APPROVE ACTION — Parent App
# ============================================================

@router.post("/approve/{student_id}")
async def approve_action(
    student_id: int,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Parent approves child's action request.
    """
    
    action = request.get("action")
    if not action:
        raise HTTPException(400, detail="Action is required")
    
    # Verify current user is parent of this student
    link = db.query(ParentLink).filter(
        ParentLink.child_id == student_id,
        ParentLink.parent_id == current_user.id,
        ParentLink.status == 'active'
    ).first()
    
    if not link:
        raise HTTPException(403, detail="Not authorized")
    
    # TODO: Store approval in a separate table (ParentApproval)
    # For now, just log and return success
    
    return {
        "success": True,
        "approved": True,
        "approvedAt": datetime.utcnow().isoformat(),
        "action": action
    }


# ============================================================
# 7. GET CHILDREN LIST — Parent App
# ============================================================

@router.get("/children")
async def get_children(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Parent gets list of linked children.
    """
    
    if current_user.role != "parent":
        raise HTTPException(403, detail="Parent access required")
    
    children = db.query(ParentLink).filter(
        ParentLink.parent_id == current_user.id,
        ParentLink.status == 'active'
    ).all()
    
    child_data = []
    for link in children:
        child = db.query(User).filter(User.id == link.child_id).first()
        if child:
            stats = db.query(UserStats).filter(UserStats.user_id == child.id).first()
            child_data.append({
                "id": child.id,
                "name": f"{child.first_name} {child.last_name}",
                "streak": stats.streak if stats else 0,
                "xp": stats.xp if stats else 0,
                "level": stats.level if stats else 1,
                "linkedAt": link.created_at.isoformat()
            })
    
    return {
        "success": True,
        "data": {
            "children": child_data,
            "total": len(child_data)
        }
    }
