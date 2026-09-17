# ============================================================
# HYELEARNER: ROUTES — AI
# All AI calls go through call_ai_with_limit
# Built by Hyesent.dev
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel

from database import get_db
from models import (
    User, Question, Mistake, TopicMastery, UserStats, UserSettings,
    MistakeExplanation, WeaknessSnapshot, StudyPlan, CareerCheck,
)
from dependencies import get_current_user, call_ai_with_limit, get_ai_usage_today
from services.ai import ai_service
from services.study_plan import StudyPlanGenerator
from services.syllabus import get_cached_syllabus, get_subject_syllabus

router = APIRouter()


# ============================================================
# SCHEMAS
# ============================================================

class AIExplanationRequest(BaseModel):
    question: str
    userAnswer: str
    options: Optional[List[str]] = None
    correctAnswer: Optional[str] = None
    mistakeId: Optional[int] = None


class AIWeaknessRequest(BaseModel):
    mistakes: List[Dict] = []
    mastery: Optional[Dict] = None
    limit: int = 5
    subject: Optional[str] = None


class AIStudyPlanRequest(BaseModel):
    goal: str
    subjects: List[str]
    hours_per_week: int
    weak_topics: Optional[List[str]] = None
    days_until_exam: Optional[int] = None
    target_score: Optional[str] = None
    study_style: Optional[str] = None
    exam_type: Optional[str] = "jamb"
    exam_date: Optional[str] = None


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
# 1. AI EXPLANATION
# ============================================================

@router.post("/explain")
async def get_ai_explanation(
    request: AIExplanationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    AI explanation for a question.
    Cached per mistake_id if provided — never regenerates for the same mistake.
    """

    # If mistake_id given and cached, return cached
    if request.mistakeId:
        existing = (
            db.query(MistakeExplanation)
            .filter_by(mistake_id=request.mistakeId, user_id=current_user.id)
            .first()
        )
        if existing:
            return {**existing.explanation_json, "from_cache": True}

    question_data = {
        "question_text": request.question,
        "options": request.options or [],
        "correct_answer": request.correctAnswer or "Unknown",
    }

    # Run under daily limit
    result = await call_ai_with_limit(
        db,
        current_user.id,
        ai_service.get_explanation,
        question=question_data,
        user_answer=request.userAnswer,
    )

    # Save explanation to cache if tied to a mistake
    if request.mistakeId:
        try:
            db.add(MistakeExplanation(
                mistake_id=request.mistakeId,
                user_id=current_user.id,
                explanation_json=result,
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"⚠️ Failed to cache explanation: {e}")

    result["question"] = request.question
    result["user_answer"] = request.userAnswer
    if request.correctAnswer:
        result["correct_answer"] = request.correctAnswer
    result["from_cache"] = False

    return result


# ============================================================
# 2. AI WEAKNESS ANALYSIS
# ============================================================

@router.post("/weakness")
async def get_weakness_analysis(
    request: AIWeaknessRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    AI weakness analysis. Saves a snapshot to weakness_snapshots.
    """
    mistakes_data = request.mistakes
    mastery_data = request.mastery or {}

    if not mistakes_data:
        query = db.query(Mistake).filter(
            Mistake.user_id == current_user.id,
            Mistake.is_resolved == False,
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
                "topicsAnalyzed": 0,
            }

        mistakes_data = [
            {
                "topic": m.topic,
                "subject": m.subject,
                "user_answer": m.user_answer,
                "correct_answer": m.correct_answer,
                "question_id": m.question_id,
            }
            for m in db_mistakes
        ]

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
                    "accuracy": (m.correct / m.total * 100) if m.total > 0 else 0,
                }
                for m in db_mastery
            }

    # Run under daily limit
    result = await call_ai_with_limit(
        db,
        current_user.id,
        ai_service.get_weakness_analysis,
        mistakes=mistakes_data,
        mastery=mastery_data,
    )

    if request.limit and len(result) > request.limit:
        result = result[:request.limit]

    high_priority = [t for t in result if t.get("priority") == "High"]
    summary = f"Found {len(result)} areas to improve. Focus on {len(high_priority)} high-priority topics first."

    # Save snapshot
    try:
        db.add(WeaknessSnapshot(
            user_id=current_user.id,
            snapshot_json=result,
            summary=summary,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ Failed to save weakness snapshot: {e}")

    return {
        "weakTopics": result,
        "summary": summary,
        "createdAt": datetime.utcnow().isoformat(),
        "totalMistakes": len(mistakes_data),
        "topicsAnalyzed": len(result),
    }


# ============================================================
# 3. AI STUDY PLAN (Legacy v1)
# ============================================================

@router.post("/study-plan")
async def generate_study_plan_v1(
    request: AIStudyPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    weak_topics = request.weak_topics or []
    if not weak_topics:
        mistakes = db.query(Mistake).filter(
            Mistake.user_id == current_user.id,
            Mistake.is_resolved == False,
        ).limit(50).all()
        weak_topics = list(set([m.topic for m in mistakes if m.topic]))

    result = await call_ai_with_limit(
        db,
        current_user.id,
        ai_service.generate_study_plan,
        goal=request.goal,
        subjects=request.subjects,
        hours_per_week=request.hours_per_week,
        weak_topics=weak_topics,
        days_until_exam=request.days_until_exam,
        target_score=request.target_score,
        study_style=request.study_style,
    )

    return {"plan": result}


# ============================================================
# 4. AI STUDY PLAN V2 (Premium)
# ============================================================

@router.post("/study-plan-v2")
async def generate_study_plan_v2(
    request: AIStudyPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Premium study plan generation. Also persists to study_plans.
    Blocks regeneration while an active plan exists.
    """

    # Check for existing active plan
    existing = (
        db.query(StudyPlan)
        .filter_by(user_id=current_user.id, status="active")
        .first()
    )
    if existing:
        return {
            "success": True,
            "plan": existing.plan_json,
            "from_cache": True,
            "message": "You already have an active study plan. Reset it first to generate a new one.",
        }

    mistakes = db.query(Mistake).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False,
    ).limit(100).all()
    weak_topics = list(set([m.topic for m in mistakes if m.topic]))

    mastery_data = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id
    ).all()
    mastery_dict = {
        m.topic: (m.correct / m.total) if m.total > 0 else 0.5
        for m in mastery_data
    }

    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    exam_type = request.exam_type or "jamb"

    user_data = {
        "subjects": request.subjects,
        "hours_per_week": request.hours_per_week,
        "target_score": request.target_score or "300+",
        "study_style": request.study_style or "balanced",
        "days_until_exam": request.days_until_exam or 30,
        "goal": request.goal,
    }

    # 1. Build the plan skeleton (no AI)
    generator = StudyPlanGenerator(
        user_data=user_data,
        weak_topics=weak_topics,
        exam_type=exam_type,
        mastery_data=mastery_dict,
    )
    plan = generator.generate_plan()

    # 2. AI enhancement — this is the only AI call
    ai_insights = await call_ai_with_limit(
        db,
        current_user.id,
        ai_service.enhance_study_plan,
        plan=plan,
        user_data=user_data,
        weak_topics=weak_topics,
    )

    # 3. Persist as active plan
    exam_date_val = None
    if request.exam_date:
        try:
            from datetime import date as date_cls
            exam_date_val = date_cls.fromisoformat(request.exam_date)
        except Exception:
            exam_date_val = None

    new_plan = StudyPlan(
        user_id=current_user.id,
        plan_json=plan,
        exam_type=exam_type,
        exam_date=exam_date_val,
        target_score=request.target_score,
        goal=request.goal,
        subjects=request.subjects,
        study_style=request.study_style,
        hours_per_week=request.hours_per_week,
        status="active",
    )
    db.add(new_plan)
    db.commit()

    return {
        "success": True,
        "plan": plan,
        "ai_insights": ai_insights,
        "user_stats": {
            "xp": stats.xp if stats else 0,
            "level": stats.level if stats else 1,
            "streak": stats.streak if stats else 0,
            "total_sessions": stats.total_sessions if stats else 0,
            "accuracy": stats.accuracy if stats else 0,
        },
        "exam_info": {
            "exam_type": exam_type.upper(),
            "subjects": request.subjects,
            "days_remaining": user_data["days_until_exam"],
            "target_score": user_data["target_score"],
            "exam_date": request.exam_date,
        },
        "generated_at": datetime.utcnow().isoformat(),
        "from_cache": False,
    }


# ============================================================
# 5. AI QUESTION GENERATOR
# ============================================================

@router.post("/generate-questions")
async def generate_questions(
    request: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    questions = await call_ai_with_limit(
        db,
        current_user.id,
        ai_service.generate_questions,
        topic=request.topic,
        count=request.count,
        difficulty=request.difficulty,
    )

    return {
        "topic": request.topic,
        "count": len(questions),
        "difficulty": request.difficulty or "mixed",
        "questions": questions,
    }


# ============================================================
# 6. SYLLABUS — not AI
# ============================================================

@router.get("/syllabus")
async def get_syllabus_data(
    exam_type: str = Query("jamb", regex="^(jamb|waec|neco|ssce|pre-university)$"),
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    syllabus = get_cached_syllabus(exam_type)

    if subject:
        subject_data = syllabus.get(subject, {})
        return {
            "exam_type": exam_type.upper(),
            "subject": subject,
            "topics": subject_data.get("topics", {}),
            "total_topics": subject_data.get("total_topics", 0),
            "is_complete": subject_data.get("is_complete", False),
        }

    return {"exam_type": exam_type.upper(), "subjects": syllabus}


# ============================================================
# 7. STUDY PLAN PRESETS — not AI
# ============================================================

@router.get("/study-plan-presets")
async def get_study_plan_presets(
    current_user: User = Depends(get_current_user),
):
    from services.study_plan import get_preset_plans
    return get_preset_plans()


# ============================================================
# 8. AI USAGE STATS
# ============================================================

@router.get("/usage")
async def get_ai_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_ai_usage_today(db, current_user.id)


# ============================================================
# 9. COURSE FINDER
# ============================================================

@router.post("/course-finder")
async def course_finder_check(
    request: CourseFinderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await call_ai_with_limit(
        db,
        current_user.id,
        ai_service.course_finder_check,
        university=request.university,
        country=request.country,
        course=request.course,
        score=request.score,
        score_type=request.score_type,
        subjects=request.subjects,
    )

    # Persist to career_checks
    try:
        db.add(CareerCheck(
            user_id=current_user.id,
            university=request.university,
            country=request.country,
            course=request.course,
            score=request.score,
            score_type=request.score_type,
            subjects=request.subjects,
            status=result.get("status"),
            chance_percentage=(result.get("result") or {}).get("chance_percentage"),
            result_json=result,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ Failed to save career check: {e}")

    return result


# ============================================================
# 10. AI TEST
# ============================================================

@router.get("/test")
async def test_ai(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from config import settings

    gemini_status = "❌ Not initialized"
    groq_status = "❌ Not initialized"

    if ai_service.gemini:
        try:
            test_response = ai_service.gemini.generate_content("Say 'Hello' in one word.")
            gemini_status = "✅ Working" if test_response and test_response.text else "⚠️ Responded but no content"
        except Exception as e:
            gemini_status = f"❌ Error: {str(e)[:50]}..."

    if ai_service.groq:
        try:
            test_response = ai_service.groq.chat.completions.create(
                model=ai_service.groq_model,
                messages=[{"role": "user", "content": "Say 'Hello' in one word."}],
                max_tokens=10,
            )
            groq_status = "✅ Working" if test_response and test_response.choices else "⚠️ Responded but no content"
        except Exception as e:
            groq_status = f"❌ Error: {str(e)[:50]}..."

    return {
        "gemini": gemini_status,
        "groq": groq_status,
        "gemini_api_key_set": bool(settings.GEMINI_API_KEY),
        "groq_api_key_set": bool(settings.GROQ_API_KEY),
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
    }
