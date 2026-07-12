from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import random

from database import get_db
from models import Question
from schemas import QuestionResponse, QuestionListResponse
from dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=QuestionListResponse)
async def get_questions(
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get filtered questions"""
    query = db.query(Question)
    
    if subject:
        query = query.filter(Question.subject.ilike(subject))
    if topic:
        query = query.filter(Question.topic.ilike(topic))
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    
    total = query.count()
    questions = query.offset(offset).limit(limit).all()
    
    return {
        "items": questions,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/random")
async def get_random_questions(
    subject: str,
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    count: int = Query(30, ge=1, le=50),
    exclude_ids: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get random questions for practice sessions"""
    query = db.query(Question).filter(Question.subject.ilike(subject))
    
    if topic:
        query = query.filter(Question.topic.ilike(topic))
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    
    # Exclude specific IDs
    if exclude_ids:
        ids = exclude_ids.split(',')
        query = query.filter(~Question.id.in_(ids))
    
    total = query.count()
    if total == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No questions found for subject: {subject}"
        )
    
    # Random offset
    offset = random.randint(0, max(0, total - count))
    questions = query.offset(offset).limit(count).all()
    
    # If not enough, get more from beginning
    if len(questions) < count:
        remaining = query.limit(count - len(questions)).all()
        questions.extend(remaining)
    
    return {
        "items": questions,
        "count": len(questions),
        "subject": subject,
        "topic": topic or "all",
        "difficulty": difficulty or "mixed"
    }


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Get a single question by ID"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=404,
            detail=f"Question {question_id} not found"
        )
    return question


@router.get("/subjects")
async def get_subjects(db: Session = Depends(get_db)):
    """Get all subjects with question counts"""
    from sqlalchemy import func
    
    results = db.query(
        Question.subject,
        func.count(Question.id).label('count')
    ).group_by(Question.subject).all()
    
    return [{"subject": r.subject, "count": r.count} for r in results]


@router.get("/topics")
async def get_topics(
    subject: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get topics with question counts"""
    from sqlalchemy import func
    
    query = db.query(
        Question.topic,
        func.count(Question.id).label('count')
    )
    if subject:
        query = query.filter(Question.subject.ilike(subject))
    
    results = query.group_by(Question.topic).all()
    return [{"topic": r.topic, "count": r.count} for r in results]