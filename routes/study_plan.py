# routes/study_plan.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database import get_db
from models import User, Mistake, TopicMastery, LessonProgress, UserStats, StudyPlan
from dependencies import get_current_user
from services.study_plan import StudyPlanGenerator
from services.syllabus import get_cached_syllabus

router = APIRouter()


@router.get("/progress")
async def get_study_plan_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    lessons = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.is_completed == True
    ).all()
    completed_lessons = len(lessons)

    mastery_data = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id
    ).all()

    mastered_topics = sum(1 for m in mastery_data if m.correct / m.total >= 0.8)
    total_topics = len(mastery_data)

    mistakes = db.query(Mistake).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False
    ).count()

    weak_topics = db.query(Mistake.topic).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False
    ).group_by(Mistake.topic).all()

    stats = db.query(UserStats).filter(
        UserStats.user_id == current_user.id
    ).first()

    if total_topics > 0:
        progress_percentage = int((mastered_topics / total_topics) * 100)
    else:
        progress_percentage = 0

    return {
        "lessons": {"completed": completed_lessons},
        "mastery": {
            "mastered_topics": mastered_topics,
            "total_topics": total_topics,
            "percentage": progress_percentage
        },
        "mistakes": {"unresolved": mistakes},
        "weak_topics": [w[0] for w in weak_topics],
        "stats": {
            "xp": stats.xp if stats else 0,
            "level": stats.level if stats else 1,
            "streak": stats.streak if stats else 0
        },
        "study_plan": {
            "current_day": 1,
            "total_days": 30,
            "daily_goal": 0.3,
            "weekly_goal": 3.0,
            "progress_percentage": progress_percentage,
            "last_updated": current_user.last_study_plan_update.isoformat() if current_user.last_study_plan_update else None
        }
    }


@router.get("/recommend")
async def get_study_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    mistakes = db.query(Mistake).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False
    ).limit(50).all()

    weak_topics = list(set([m.topic for m in mistakes]))

    mastery_data = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id
    ).all()

    stats = db.query(UserStats).filter(
        UserStats.user_id == current_user.id
    ).first()

    recommendations = []

    if weak_topics:
        recommendations.append({
            "type": "focus",
            "title": "Focus on Weak Topics",
            "description": f"Your weak topics: {', '.join(weak_topics[:3])}",
            "priority": "high",
            "topics": weak_topics[:3]
        })

    if stats and stats.streak < 3:
        recommendations.append({
            "type": "streak",
            "title": "Build Your Streak",
            "description": f"Study daily to build a streak. You're at day {stats.streak}",
            "priority": "medium"
        })

    if mastery_data and len(mastery_data) < 10:
        recommendations.append({
            "type": "practice",
            "title": "More Practice Needed",
            "description": f"You've only mastered {len(mastery_data)} topics. Keep practicing!",
            "priority": "high"
        })

    if stats and stats.total_sessions < 5:
        recommendations.append({
            "type": "session",
            "title": "Start Your First Sessions",
            "description": "Complete 5 sessions to unlock progress tracking",
            "priority": "medium"
        })

    return {
        "recommendations": recommendations,
        "next_action": recommendations[0] if recommendations else None
    }


@router.post("/sync")
async def sync_study_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.utcnow().date()
    last_update = current_user.last_study_plan_update

    if last_update and last_update.date() == today:
        return {
            "status": "cached",
            "message": "Study plan already updated today. Come back tomorrow for a fresh plan.",
            "last_updated": last_update.isoformat(),
            "plan": None
        }

    mistakes = db.query(Mistake).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False
    ).limit(100).all()

    weak_topics = list(set([m.topic for m in mistakes]))

    mastery_data = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id
    ).all()

    mastery_dict = {
        m.topic: (m.correct / m.total) if m.total > 0 else 0.5
        for m in mastery_data
    }

    stats = db.query(UserStats).filter(
        UserStats.user_id == current_user.id
    ).first()

    lessons = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.is_completed == True
    ).count()

    user_data = {
        "subjects": ["Mathematics", "English", "Physics", "Chemistry"],
        "hours_per_week": 15,
        "days_until_exam": 30,
        "target_score": "300+",
        "study_style": "balanced",
        "goal": "Pass exam"
    }

    generator = StudyPlanGenerator(
        user_data=user_data,
        weak_topics=weak_topics,
        exam_type=current_user.exam or "jamb",
        mastery_data=mastery_dict
    )

    plan = generator.generate_plan()

    current_user.last_study_plan_update = datetime.utcnow()
    db.commit()

    return {
        "status": "updated",
        "message": "Study plan updated successfully",
        "last_updated": current_user.last_study_plan_update.isoformat(),
        "plan": plan,
        "stats": {
            "lessons_completed": lessons,
            "topics_mastered": len(mastery_dict),
            "weak_topics": weak_topics,
            "xp": stats.xp if stats else 0,
            "level": stats.level if stats else 1,
            "streak": stats.streak if stats else 0
        },
        "synced_at": datetime.utcnow().isoformat()
    }


# ============================================================
# ⭐ NEW — GET /study-plan/current
# ============================================================

@router.get("/current")
async def get_current_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = (
        db.query(StudyPlan)
        .filter_by(user_id=current_user.id, status="active")
        .first()
    )
    if not plan:
        return {"plan": None}

    return {
        "plan": {
            "id": plan.id,
            "plan_json": plan.plan_json,
            "exam_type": plan.exam_type,
            "exam_date": plan.exam_date.isoformat() if plan.exam_date else None,
            "target_score": plan.target_score,
            "goal": plan.goal,
            "subjects": plan.subjects,
            "study_style": plan.study_style,
            "hours_per_week": plan.hours_per_week,
            "generated_at": plan.generated_at.isoformat() if plan.generated_at else None,
        }
    }


# ============================================================
#  NEW — POST /study-plan/reset
# ============================================================

@router.post("/reset")
async def reset_study_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(StudyPlan).filter_by(
        user_id=current_user.id, status="active"
    ).update({"status": "cancelled"})
    db.commit()
    return {"success": True, "message": "Plan reset. You can now generate a new one."}
