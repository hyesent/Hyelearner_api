# ============================================================
# routes/daily_tutor.py — AI Daily Tutor Endpoints
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import (
    GenerateLessonRequest, GenerateLessonResponse,
    GenerateQuizRequest, GenerateQuizResponse
)
from dependencies import get_current_user
from services.daily_tutor import daily_tutor_service

router = APIRouter(prefix="/daily-tutor", tags=["Daily Tutor"])


# ============================================================
# 1. GENERATE LESSON
# ============================================================

@router.post("/lesson", response_model=GenerateLessonResponse)
async def generate_lesson(
    request: GenerateLessonRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a personalized lesson for the student.
    AI-powered with Gemini (primary) and Groq (fallback).
    """
    
    print(f"📥 Lesson request for user {current_user.id}: {request.topic}")
    
    # Convert request to dict
    data = request.model_dump()
    
    # Generate lesson
    result = await daily_tutor_service.generate_lesson(data)
    
    return result


# ============================================================
# 2. GENERATE QUIZ
# ============================================================

@router.post("/quiz", response_model=GenerateQuizResponse)
async def generate_quiz(
    request: GenerateQuizRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a quiz based on the lesson content.
    AI-powered with Gemini (primary) and Groq (fallback).
    """
    
    print(f"📥 Quiz request for user {current_user.id}: {request.topic}")
    
    # Convert request to dict
    data = request.model_dump()
    
    # Generate quiz
    result = await daily_tutor_service.generate_quiz(data)
    
    return result
