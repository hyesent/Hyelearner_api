from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import User, Question, Mistake, TopicMastery, UserStats, UserSettings
from schemas import (
    AIExplanationRequest, AIExplanationResponse,
    AIWeaknessRequest, AIWeaknessResponse,
    AIWeaknessItem, AIStudyPlanRequest, AIStudyPlanResponse
)
from dependencies import get_current_user
from services.ai import ai_service
from services.study_plan import StudyPlanGenerator
from services.syllabus import get_cached_syllabus, get_subject_syllabus

router = APIRouter()


@router.post("/explain", response_model=AIExplanationResponse)
async def get_explanation(
    request: AIExplanationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI explanation for a question"""
    question = db.query(Question).filter(Question.id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

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

    mastery_query = db.query(TopicMastery).filter(TopicMastery.user_id == current_user.id)
    if request.subject:
        mastery_query = mastery_query.filter(TopicMastery.subject.ilike(request.subject))

    mastery_data = mastery_query.all()

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

    weak_topics = await ai_service.get_weakness_analysis(mistake_data, mastery_dict)

    if request.limit and len(weak_topics) > request.limit:
        weak_topics = weak_topics[:request.limit]

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


# ============================================================
# PREMIUM STUDY PLAN V2 — Uses dynamic syllabus + AI
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
    Supports 50+ subjects with 300+ topics.
    """
    # 1. Get user's weak topics from mistakes
    mistakes = db.query(Mistake).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False
    ).limit(100).all()

    weak_topics = list(set([m.topic for m in mistakes]))

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

    # 4. Build user data for study plan generator
    exam_type = current_user.exam or "jamb"
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

    # 6. Get AI enhancement
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
# GET SYLLABUS DATA
# ============================================================

@router.get("/syllabus")
async def get_syllabus_data(
    exam_type: str = Query("jamb", regex="^(jamb|waec|neco)$"),
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get syllabus data for a specific exam.
    Returns all topics with weights and priorities.
    """
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
# GET STUDY PLAN PRESETS
# ============================================================

@router.get("/study-plan-presets")
async def get_study_plan_presets(
    current_user: User = Depends(get_current_user)
):
    """Get preset study plans for different scenarios"""
    from services.study_plan import get_preset_plans
    return get_preset_plans()


# ============================================================
# AI USAGE
# ============================================================

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


# ============================================================
# AI QUESTION GENERATOR (Future Feature)
# ============================================================

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


# ============================================================
# STUDY PLAN V1 (Legacy — Keep for backward compatibility)
# ============================================================

@router.post("/study-plan", response_model=AIStudyPlanResponse)
async def generate_study_plan_v1(
    request: AIStudyPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy study plan endpoint (v1) — kept for backward compatibility"""
    mistakes = db.query(Mistake).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False
    ).limit(50).all()

    weak_topics = list(set([m.topic for m in mistakes]))

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
