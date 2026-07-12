from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import secrets

from database import get_db
from models import User, ParentLink, UserStats, Subscription
from schemas import (
    ParentLinkRequest, ParentLinkResponse,
    ParentCodeResponse, ParentStatusResponse,
    ChildAnalyticsResponse
)
from dependencies import get_current_user, get_current_parent_user

router = APIRouter()


@router.post("/generate-code", response_model=ParentCodeResponse)
async def generate_parent_code(
    current_user: User = Depends(get_current_parent_user),
    db: Session = Depends(get_db)
):
    """Generate a parent linking code"""
    # Generate unique code
    code = secrets.token_hex(4).upper()
    
    # Check if code already exists
    existing = db.query(ParentLink).filter(ParentLink.code == code).first()
    while existing:
        code = secrets.token_hex(4).upper()
        existing = db.query(ParentLink).filter(ParentLink.code == code).first()
    
    # Create parent link entry
    parent_link = ParentLink(
        parent_id=current_user.id,
        child_id=None,
        code=code,
        is_approved=False
    )
    db.add(parent_link)
    db.commit()
    
    return {
        "code": code,
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
    }


@router.post("/link", response_model=ParentLinkResponse)
async def link_child(
    request: ParentLinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Link a child to parent using code"""
    # Find parent link by code
    parent_link = db.query(ParentLink).filter(
        ParentLink.code == request.code,
        ParentLink.is_approved == False
    ).first()
    
    if not parent_link:
        raise HTTPException(status_code=404, detail="Invalid or expired code")
    
    # Check if user is already linked to a parent
    existing = db.query(ParentLink).filter(
        ParentLink.child_id == current_user.id,
        ParentLink.is_approved == True
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already linked to a parent")
    
    # Link child
    parent_link.child_id = current_user.id
    parent_link.is_approved = True
    parent_link.approved_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "linked_at": parent_link.approved_at
    }


@router.get("/status", response_model=ParentStatusResponse)
async def get_parent_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get parent linking status"""
    # Check if user is a parent
    if current_user.role == "parent":
        # Get children
        children = db.query(ParentLink).filter(
            ParentLink.parent_id == current_user.id,
            ParentLink.is_approved == True
        ).all()
        
        return {
            "linked": True,
            "children": [
                {
                    "id": child.child_id,
                    "name": db.query(User).filter(User.id == child.child_id).first().full_name,
                    "linked_at": child.approved_at
                }
                for child in children
            ]
        }
    
    # Check if user is a child
    parent_link = db.query(ParentLink).filter(
        ParentLink.child_id == current_user.id,
        ParentLink.is_approved == True
    ).first()
    
    if parent_link:
        parent = db.query(User).filter(User.id == parent_link.parent_id).first()
        return {
            "linked": True,
            "parent": {
                "id": parent.id,
                "name": parent.full_name,
                "email": parent.email
            }
        }
    
    return {"linked": False, "children": []}


@router.get("/analytics/{student_id}", response_model=ChildAnalyticsResponse)
async def get_student_analytics(
    student_id: int,
    current_user: User = Depends(get_current_parent_user),
    db: Session = Depends(get_db)
):
    """Get analytics for a linked child"""
    # Verify parent-child relationship
    parent_link = db.query(ParentLink).filter(
        ParentLink.parent_id == current_user.id,
        ParentLink.child_id == student_id,
        ParentLink.is_approved == True
    ).first()
    
    if not parent_link:
        raise HTTPException(status_code=403, detail="Not authorized to view this student")
    
    # Get student data
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get stats
    stats = db.query(UserStats).filter(UserStats.user_id == student_id).first()
    
    # Get subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == student_id,
        Subscription.is_active == True
    ).first()
    
    # Get mastery data (simplified)
    subjects = ["Mathematics", "English", "Physics", "Chemistry"]
    subject_readiness = []
    for subject in subjects:
        # In production, get actual mastery data
        subject_readiness.append({
            "name": subject,
            "readiness": 60 + (hash(student_id + subject) % 30)
        })
    
    return {
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
            "study_time": {
                "today": 2,
                "week": 12,
                "month": 45
            },
            "subjects": subject_readiness
        }
    }