from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import User, Question, Mistake, TopicMastery, UserStats
from schemas import (
    AIExplanationRequest, AIExplanationResponse,
    AIWeaknessRequest, AIWeaknessResponse,
    AIWeaknessItem, AIStudyPlanRequest, AIStudyPlanResponse
)
from dependencies import get_current_user
from services.ai import ai_service

router = APIRouter()


@router.post("/explain", response_model=AIExplanationResponse)
async def get_explanation(
    request: AIExplanationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI explanation for a question"""
    # Get question
    question = db.query(Question).filter(Question.id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Get AI explanation
    explanation = await ai_service.get_explanation(
        {
            "question_text": question.question,
            "options": question.options,
            "correct_answer": question.answer,
            "explanation": question.explanation,
            "topic": question.topic,
            "subject": question.subject,
            "difficulty": question.difficulty
        },
        request.user_answer
    )
    
    return explanation


@router.post("/weakness", response_model=AIWeaknessResponse)
async def get_weakness_analysis(
    request: AIWeaknessRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI weakness analysis"""
    # Get user's mistakes
    query = db.query(Mistake).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False
    )
    
    if request.subject:
        query = query.filter(Mistake.subject.ilike(request.subject))
    
    mistakes = query.limit(100).all()
    
    if not mistakes:
        return {
            "weak_topics": [],
            "summary": "No mistakes found! Keep up the great work! 🎉",
            "created_at": datetime.utcnow().isoformat()
        }
    
    # Get topic mastery data
    mastery_query = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id
    )
    
    if request.subject:
        mastery_query = mastery_query.filter(TopicMastery.subject.ilike(request.subject))
    
    mastery_data = mastery_query.all()
    
    # Prepare data for AI
    mistake_data = [
        {
            "topic": m.topic,
            "subject": m.subject,
            "user_answer": m.user_answer,
            "correct_answer": m.correct_answer,
            "question_id": m.question_id
        }
        for m in mistakes
    ]
    
    mastery_dict = {
        m.topic: {
            "correct": m.correct,
            "total": m.total,
            "accuracy": (m.correct / m.total * 100) if m.total > 0 else 0
        }
        for m in mastery_data
    }
    
    # Get AI weakness analysis
    weak_topics = await ai_service.get_weakness_analysis(mistake_data, mastery_dict)
    
    # Limit results
    if request.limit and len(weak_topics) > request.limit:
        weak_topics = weak_topics[:request.limit]
    
    # Generate summary
    if weak_topics:
        high_priority = [t for t in weak_topics if t.get('priority') == 'High']
        summary = f"Found {len(weak_topics)} areas to improve. Focus on {len(high_priority)} high-priority topics first."
    else:
        summary = "Great job! No major weaknesses detected. Keep practicing to maintain your skills."
    
    return {
        "weak_topics": weak_topics,
        "summary": summary,
        "created_at": datetime.utcnow().isoformat()
    }


@router.post("/study-plan", response_model=AIStudyPlanResponse)
async def generate_study_plan(
    request: AIStudyPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered study plan"""
    # Get user's weak topics for personalized plan
    mistakes = db.query(Mistake).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False
    ).limit(50).all()
    
    weak_topics = list(set([m.topic for m in mistakes]))
    
    # Get user's stats for context
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    
    # Generate study plan
    study_plan = await ai_service.generate_study_plan(
        goal=request.goal,
        subjects=request.subjects,
        hours_per_week=request.hours_per_week,
        weak_topics=weak_topics,
        days_until_exam=request.days_until_exam,
        target_score=request.target_score,
        study_style=request.study_style
    )
    
    return {"plan": study_plan}


@router.get("/usage")
async def get_ai_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's AI usage statistics"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        return {
            "used_today": 0,
            "used_month": 0,
            "daily_limit": 10,
            "monthly_limit": 100,
            "remaining_today": 10,
            "remaining_month": 100
        }
    
    return {
        "used_today": settings.ai_used_today or 0,
        "used_month": settings.ai_used_month or 0,
        "daily_limit": settings.ai_daily_limit or 10,
        "monthly_limit": 100,
        "remaining_today": max(0, (settings.ai_daily_limit or 10) - (settings.ai_used_today or 0)),
        "remaining_month": max(0, 100 - (settings.ai_used_month or 0))
    }


@router.post("/generate")
async def generate_questions(
    topic: str,
    count: int = Query(10, ge=1, le=20),
    difficulty: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered practice questions (Future feature)"""
    questions = await ai_service.generate_questions(
        topic=topic,
        count=count,
        difficulty=difficulty
    )
    
    return {
        "topic": topic,
        "count": len(questions),
        "difficulty": difficulty or "mixed",
        "questions": questions
    }
