from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from datetime import datetime

from database import get_db
from models import TopicMastery, User
from schemas import MasteryResponse, MasteryUpdate
from dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=MasteryResponse)
async def get_mastery(
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get topic mastery for current user"""
    query = db.query(TopicMastery).filter(TopicMastery.user_id == current_user.id)
    
    if subject:
        query = query.filter(TopicMastery.subject.ilike(subject))
    
    mastery_items = query.all()
    
    mastery = {}
    for item in mastery_items:
        accuracy = (item.correct / item.total * 100) if item.total > 0 else 0
        mastery[item.topic] = {
            "accuracy": round(accuracy, 1),
            "attempts": item.total,
            "subject": item.subject
        }
    
    return {"mastery": mastery}


@router.get("/topics")
async def get_topics_mastery(
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get topic mastery with status for heatmap"""
    query = db.query(TopicMastery).filter(TopicMastery.user_id == current_user.id)
    
    if subject:
        query = query.filter(TopicMastery.subject.ilike(subject))
    
    mastery_items = query.all()
    
    result = []
    for item in mastery_items:
        accuracy = (item.correct / item.total * 100) if item.total > 0 else 0
        
        # Determine status
        if accuracy >= 80:
            status = "strong"
        elif accuracy >= 50:
            status = "average"
        elif accuracy > 0:
            status = "weak"
        else:
            status = "not_studied"
        
        result.append({
            "topic": item.topic,
            "accuracy": round(accuracy, 1),
            "attempts": item.total,
            "status": status,
            "subject": item.subject
        })
    
    return result


@router.post("/update", response_model=MasteryResponse)
async def update_mastery(
    data: MasteryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update topic mastery"""
    mastery = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id,
        TopicMastery.subject == data.subject,
        TopicMastery.topic == data.topic
    ).first()
    
    if not mastery:
        mastery = TopicMastery(
            user_id=current_user.id,
            subject=data.subject,
            topic=data.topic,
            correct=0,
            total=0
        )
        db.add(mastery)
    
    # Update with new data
    # This is a simplified version - actual update comes from session results
    mastery.total += 1
    if data.accuracy >= 70:
        mastery.correct += 1
    
    mastery.updated_at = datetime.utcnow()
    db.commit()
    
    # Return updated mastery
    all_mastery = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id
    ).all()
    
    mastery_dict = {}
    for item in all_mastery:
        accuracy = (item.correct / item.total * 100) if item.total > 0 else 0
        mastery_dict[item.topic] = {
            "accuracy": round(accuracy, 1),
            "attempts": item.total,
            "subject": item.subject
        }
    
    return {"mastery": mastery_dict}