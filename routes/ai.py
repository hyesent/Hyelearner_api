from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel

from database import get_db
from models import User, Question, Mistake, TopicMastery, UserStats, UserSettings
from dependencies import get_current_user
from services.ai import ai_service
from services.study_plan import StudyPlanGenerator
from services.syllabus import get_cached_syllabus, get_subject_syllabus

router = APIRouter()


# ============================================================
# UPDATED SCHEMAS — Match frontend requests
# ============================================================

class AIExplanationRequest(BaseModel):
    question: str
    userAnswer: str
    options: Optional[List[str]] = None
    correctAnswer: Optional[str] = None


class AIWeaknessRequest(BaseModel):
    mistakes: List[Dict] = []
    mastery: Optional[Dict] = None
    limit: int = 5
    subject: Optional[str] = None  # For backward compatibility


class AIStudyPlanRequest(BaseModel):
    goal: str
    subjects: List[str]
    hours_per_week: int
    weak_topics: Optional[List[str]] = None
    days_until_exam: Optional[int] = None
    target_score: Optional[str] = None
    study_style: Optional[str] = None
    exam_type: Optional[str] = "jamb"


class AIStudyPlanV2Request(BaseModel):
    plan: Dict
    user_data: Dict
    weak_topics: List[str]


class GenerateQuestionsRequest(BaseModel):
    topic: str
    count: int = 5
    difficulty: Optional[str] = None


class CourseFinderRequest(BaseModel):
    university: str
    country: str
    course: str
    score: float
    score_type: str
    subjects: List[str]


# ============================================================
# 1. AI EXPLANATION — Supports frontend data (NO DB lookup)
# ============================================================

@router.post("/explain")
async def get_ai_explanation(
    request: AIExplanationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI explanation for a question.
    Questions come from FRONTEND (no database lookup).
    Groq primary, Gemini fallback.
    """
    
    # Build question dict from frontend data
    question_data = {
        "question_text": request.question,
        "options": request.options or [],
        "correct_answer": request.correctAnswer or "Unknown"
    }
    
    # Get explanation from AI service (Groq → Gemini fallback)
    result = await ai_service.get_explanation(
        question=question_data,
        user_answer=request.userAnswer
    )
    
    # Add context to response
    result["question"] = request.question
    result["user_answer"] = request.userAnswer
    if request.correctAnswer:
        result["correct_answer"] = request.correctAnswer
    
    return result


# ============================================================
# 2. AI WEAKNESS ANALYSIS — Accepts mistakes + mastery from frontend
# ============================================================

@router.post("/weakness")
async def get_weakness_analysis(
    request: AIWeaknessRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI weakness analysis using Groq (primary) or Gemini (fallback).
    Expects mistakes and optional mastery data from frontend.
    """
    
    # ✅ Use data from frontend if provided
    mistakes_data = request.mistakes
    mastery_data = request.mastery or {}
    
    # If no mistakes provided, try to get from database (backward compatibility)
    if not mistakes_data:
        query = db.query(Mistake).filter(
            Mistake.user_id == current_user.id,
            Mistake.is_resolved == False
        )
        if request.subject:
            query = query.filter(Mistake.subject.ilike(request.subject))
        
        db_mistakes = query.limit(100).all()
        
        if not db_mistakes:
            return {
                "weakTopics": [],
                "summary": "No mistakes found! Keep up the great work! 🎉",
                "createdAt": datetime.utcnow().isoformat(),
                "totalMistakes": 0,
                "topicsAnalyzed": 0
            }
        
        # Convert DB mistakes to dict format
        mistakes_data = [
            {
                "topic": m.topic,
                "subject": m.subject,
                "user_answer": m.user_answer,
                "correct_answer": m.correct_answer,
                "question_id": m.question_id
            }
            for m in db_mistakes
        ]
        
        # Get mastery from DB if not provided
        if not mastery_data:
            mastery_query = db.query(TopicMastery).filter(
                TopicMastery.user_id == current_user.id
            )
            if request.subject:
                mastery_query = mastery_query.filter(TopicMastery.subject.ilike(request.subject))
            
            db_mastery = mastery_query.all()
            mastery_data = {
                m.topic: {
                    "correct": m.correct,
                    "total": m.total,
                    "accuracy": (m.correct / m.total * 100) if m.total > 0 else 0
                }
                for m in db_mastery
            }
    
    # Get analysis from AI service (Groq → Gemini fallback)
    result = await ai_service.get_weakness_analysis(
        mistakes=mistakes_data,
        mastery=mastery_data
    )
    
    # Limit results
    if request.limit and len(result) > request.limit:
        result = result[:request.limit]
    
    # Generate summary
    high_priority = [t for t in result if t.get('priority') == 'High']
    summary = f"Found {len(result)} areas to improve. Focus on {len(high_priority)} high-priority topics first."
    
    return {
        "weakTopics": result,
        "summary": summary,
        "createdAt": datetime.utcnow().isoformat(),
        "totalMistakes": len(mistakes_data),
        "topicsAnalyzed": len(result)
    }


# ============================================================
# 3. AI STUDY PLAN (Legacy v1) — Gemini primary, Groq fallback
# ============================================================

@router.post("/study-plan")
async def generate_study_plan_v1(
    request: AIStudyPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy study plan endpoint (v1). Gemini primary, Groq fallback."""
    
    # Get weak topics from mistakes if not provided
    weak_topics = request.weak_topics or []
    if not weak_topics:
        mistakes = db.query(Mistake).filter(
            Mistake.user_id == current_user.id,
            Mistake.is_resolved == False
        ).limit(50).all()
        weak_topics = list(set([m.topic for m in mistakes if m.topic]))

    result = await ai_service.generate_study_plan(
        goal=request.goal,
        subjects=request.subjects,
        hours_per_week=request.hours_per_week,
        weak_topics=weak_topics,
        days_until_exam=request.days_until_exam,
        target_score=request.target_score,
        study_style=request.study_style
    )

    return {"plan": result}


# ============================================================
# 4. AI STUDY PLAN V2 (Premium) — Gemini primary, Groq fallback
# ============================================================

@router.post("/study-plan-v2")
async def generate_study_plan_v2(
    request: AIStudyPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    PREMIUM FEATURE: Generate an advanced AI-powered study plan.
    Uses dynamic syllabus + user performance data + AI insights.
    Gemini primary, Groq fallback.
    """
    
    # 1. Get user's weak topics from mistakes
    mistakes = db.query(Mistake).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False
    ).limit(100).all()
    
    weak_topics = list(set([m.topic for m in mistakes if m.topic]))

    # 2. Get topic mastery data
    mastery_data = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id
    ).all()
    
    mastery_dict = {
        m.topic: (m.correct / m.total) if m.total > 0 else 0.5
        for m in mastery_data
    }

    # 3. Get user's stats
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()

    # 4. Build user data
    exam_type = request.exam_type or "jamb"
    
    user_data = {
        "subjects": request.subjects,
        "hours_per_week": request.hours_per_week,
        "target_score": request.target_score or "300+",
        "study_style": request.study_style or "balanced",
        "days_until_exam": request.days_until_exam or 30,
        "goal": request.goal
    }

    # 5. Generate study plan using StudyPlanGenerator
    generator = StudyPlanGenerator(
        user_data=user_data,
        weak_topics=weak_topics,
        exam_type=exam_type,
        mastery_data=mastery_dict
    )

    plan = generator.generate_plan()

    # 6. Get AI enhancement (Gemini → Groq fallback)
    ai_insights = await ai_service.enhance_study_plan(
        plan=plan,
        user_data=user_data,
        weak_topics=weak_topics
    )

    return {
        "plan": plan,
        "ai_insights": ai_insights,
        "user_stats": {
            "xp": stats.xp if stats else 0,
            "level": stats.level if stats else 1,
            "streak": stats.streak if stats else 0,
            "total_sessions": stats.total_sessions if stats else 0,
            "accuracy": stats.accuracy if stats else 0
        },
        "exam_info": {
            "exam_type": exam_type.upper(),
            "subjects": request.subjects,
            "days_remaining": user_data["days_until_exam"],
            "target_score": user_data["target_score"]
        },
        "generated_at": datetime.utcnow().isoformat()
    }


# ============================================================
# 5. AI QUESTION GENERATOR — Gemini primary (no Groq fallback)
# ============================================================

@router.post("/generate-questions")
async def generate_questions(
    request: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered practice questions using Gemini."""
    
    questions = await ai_service.generate_questions(
        topic=request.topic,
        count=request.count,
        difficulty=request.difficulty
    )

    return {
        "topic": request.topic,
        "count": len(questions),
        "difficulty": request.difficulty or "mixed",
        "questions": questions
    }


# ============================================================
# 6. SYLLABUS — Not AI, but useful for study plan
# ============================================================

@router.get("/syllabus")
async def get_syllabus_data(
    exam_type: str = Query("jamb", regex="^(jamb|waec|neco|ssce|pre-university)$"),
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get syllabus data for a specific exam."""
    syllabus = get_cached_syllabus(exam_type)

    if subject:
        subject_data = syllabus.get(subject, {})
        return {
            "exam_type": exam_type.upper(),
            "subject": subject,
            "topics": subject_data.get("topics", {}),
            "total_topics": subject_data.get("total_topics", 0),
            "is_complete": subject_data.get("is_complete", False)
        }

    return {
        "exam_type": exam_type.upper(),
        "subjects": syllabus
    }


# ============================================================
# 7. STUDY PLAN PRESETS
# ============================================================

@router.get("/study-plan-presets")
async def get_study_plan_presets(
    current_user: User = Depends(get_current_user)
):
    """Get preset study plan configurations."""
    from services.study_plan import get_preset_plans
    return get_preset_plans()


# ============================================================
# 8. AI USAGE STATS
# ============================================================

@router.get("/usage")
async def get_ai_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's AI usage statistics."""
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


# ============================================================
# 9. COURSE FINDER — Gemini primary, Groq fallback
# ============================================================

@router.post("/course-finder")
async def course_finder_check(
    request: CourseFinderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Global course finder — check admission eligibility for ANY university.
    Gemini primary, Groq fallback.
    """
    
    result = await ai_service.course_finder_check(
        university=request.university,
        country=request.country,
        course=request.course,
        score=request.score,
        score_type=request.score_type,
        subjects=request.subjects
    )
    
    return result


# ============================================================
# 10. AI TEST ENDPOINT (Health Check)
# ============================================================

@router.get("/test")
async def test_ai(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test AI connectivity — checks Gemini and Groq status.
    """
    
    gemini_status = "❌ Not initialized"
    groq_status = "❌ Not initialized"
    
    if ai_service.gemini:
        try:
            test_response = ai_service.gemini.generate_content("Say 'Hello' in one word.")
            if test_response and test_response.text:
                gemini_status = "✅ Working"
            else:
                gemini_status = "⚠️ Responded but no content"
        except Exception as e:
            gemini_status = f"❌ Error: {str(e)[:50]}..."
    
    if ai_service.groq:
        try:
            test_response = ai_service.groq.chat.completions.create(
                model=ai_service.groq_model,
                messages=[{"role": "user", "content": "Say 'Hello' in one word."}],
                max_tokens=10
            )
            if test_response and test_response.choices:
                groq_status = "✅ Working"
            else:
                groq_status = "⚠️ Responded but no content"
        except Exception as e:
            groq_status = f"❌ Error: {str(e)[:50]}..."
    
    return {
        "gemini": gemini_status,
        "groq": groq_status,
        "gemini_api_key_set": bool(settings.GEMINI_API_KEY),
        "groq_api_key_set": bool(settings.GROQ_API_KEY),
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }
