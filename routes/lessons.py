from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import Lesson, LessonProgress, User, UserStats
from schemas import LessonResponse, LessonProgressResponse
from dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=List[LessonResponse])
async def get_lessons(
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all lessons with optional filters"""
    query = db.query(Lesson)
    
    if subject:
        query = query.filter(Lesson.subject.ilike(subject))
    if topic:
        query = query.filter(Lesson.topic.ilike(topic))
    
    lessons = query.order_by(Lesson.order).all()
    
    # Get user progress
    progress = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id
    ).all()
    
    progress_map = {p.lesson_id: p for p in progress}
    
    # Add completion status to response
    for lesson in lessons:
        lesson.is_completed = lesson.id in progress_map and progress_map[lesson.id].is_completed
    
    return lessons


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific lesson"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Track view (update last_accessed)
    progress = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.lesson_id == lesson_id
    ).first()
    
    if not progress:
        progress = LessonProgress(
            user_id=current_user.id,
            lesson_id=lesson_id
        )
        db.add(progress)
        db.commit()
    
    return lesson


@router.post("/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a lesson as completed"""
    # Check if lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Check if already completed
    existing = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.lesson_id == lesson_id,
        LessonProgress.is_completed == True
    ).first()
    
    if existing:
        return {"message": "Lesson already completed", "completed": True}
    
    # Get or create progress
    progress = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.lesson_id == lesson_id
    ).first()
    
    if not progress:
        progress = LessonProgress(
            user_id=current_user.id,
            lesson_id=lesson_id
        )
        db.add(progress)
    
    progress.is_completed = True
    progress.completed_at = datetime.utcnow()
    
    # ✅ Award XP for completing a lesson
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    if stats:
        stats.xp += 25  # XP for lesson completion
        stats.level = min(stats.xp // 100 + 1, 20)
        stats.last_activity = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Lesson marked as completed",
        "xp_earned": 25,
        "completed": True
    }


@router.get("/progress", response_model=LessonProgressResponse)
async def get_lesson_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get lesson progress for current user"""
    total = db.query(Lesson).count()
    
    completed = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.is_completed == True
    ).count()
    
    progress = int((completed / total * 100)) if total > 0 else 0
    
    return {
        "total": total,
        "completed": completed,
        "progress": progress
    }
