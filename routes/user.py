from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date as SQLDate
from typing import List, Optional
from datetime import datetime, date, timedelta
import base64

from database import get_db
from models import User, UserSettings, UserStats, Session as PracticeSession, UserDailyStats
from schemas import (
    UserResponse, UserUpdate, UserSettingsResponse, UserSettingsUpdate,
    GamificationResponse, UserStatsResponse, UserStatsUpdate, UserStatsRangeResponse
)
from dependencies import get_current_user, get_ai_usage_today
from auth import get_password_hash, verify_password

router = APIRouter()


# ============================================================
# LEVEL HELPER
# ============================================================

def compute_level_from_xp(xp: int) -> int:
    if xp < 1000:
        return xp // 100 + 1
    return 10 + (xp - 1000) // 200


# ============================================================
# PROFILE
# ============================================================

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    for key, value in user_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(current_user, key, value)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    ext = file.filename.split('.')[-1] if file.filename else 'png'
    avatar_data = base64.b64encode(contents).decode('utf-8')
    avatar_url = f"data:image/{ext};base64,{avatar_data}"

    current_user.avatar_url = avatar_url
    db.commit()

    return {"avatar_url": avatar_url}


# ============================================================
# SETTINGS
# ============================================================

@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.put("/settings", response_model=UserSettingsResponse)
async def update_settings(
    settings_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    for key, value in settings_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(settings, key, value)

    db.commit()
    db.refresh(settings)
    return settings


# ============================================================
# SUBJECTS
# ============================================================

@router.get("/subjects", response_model=List[str])
async def get_subjects(
    current_user: User = Depends(get_current_user)
):
    return ["Mathematics", "English", "Physics", "Chemistry"]


@router.put("/subjects")
async def update_subjects(
    subjects: List[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {"message": "Subjects updated", "subjects": subjects}


# ============================================================
# PASSWORD
# ============================================================

@router.put("/password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 6 characters"
        )

    current_user.hashed_password = get_password_hash(new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Password updated successfully"}


# ============================================================
# DAILY STATS — GET TODAY'S STATS
# ============================================================

@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = date.today()

    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date == today
    ).first()

    if stats:
        return {
            "date": stats.date.isoformat(),
            "xp": stats.xp,
            "level": stats.level,
            "streak": stats.streak,
            "accuracy": stats.accuracy,
            "sessions": stats.sessions,
            "totalQuestions": stats.total_questions,
            "correct": stats.correct,
            "wrong": stats.wrong,
            "studyTime": stats.study_time_minutes,
            "fromCache": True,
            "cachedAt": stats.updated_at.isoformat() if stats.updated_at else None
        }

    return await compute_user_stats(current_user.id, db)


async def compute_user_stats(user_id: int, db: Session):
    today = date.today()

    sessions = db.query(PracticeSession).filter(
        PracticeSession.user_id == user_id,
        PracticeSession.is_completed == True
    ).all()

    gamification = db.query(UserStats).filter(
        UserStats.user_id == user_id
    ).first()

    total_questions = sum(s.total_questions or 0 for s in sessions)
    correct = sum(s.correct_answers or 0 for s in sessions)
    wrong = sum(s.wrong_answers or 0 for s in sessions)
    accuracy = (correct / total_questions * 100) if total_questions > 0 else 0

    today_sessions = [
        s for s in sessions
        if s.completed_at and s.completed_at.date() == today
    ]

    study_time_minutes = sum(
        (s.time_taken or 0) for s in today_sessions
    ) // 60

    result = {
        "date": today.isoformat(),
        "xp": gamification.xp if gamification else 0,
        "level": gamification.level if gamification else 1,
        "streak": gamification.streak if gamification else 0,
        "accuracy": round(accuracy, 1),
        "sessions": len(today_sessions),
        "totalQuestions": total_questions,
        "correct": correct,
        "wrong": wrong,
        "studyTime": study_time_minutes,
        "fromCache": False
    }

    await save_daily_stats(user_id, result, db)

    return result


# ============================================================
# ⭐ DAILY STATS — SAVE (now delta-aware + updates user_stats)
# ============================================================

@router.post("/stats")
async def save_user_stats(
    stats_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accepts either:
      - delta form:  { xp_delta, sessions_delta, questions_delta,
                       correct_delta, wrong_delta, minutes_delta, streak }
      - absolute form (legacy): { xp, level, streak, accuracy, sessions,
                                   totalQuestions, correct, wrong, studyTime }

    Delta form increments UserStats + UserDailyStats (source of truth for leaderboard).
    Absolute form is treated as a full overwrite of today's UserDailyStats only.
    """
    today = date.today()

    has_delta = any(
        k in stats_data for k in (
            "xp_delta", "sessions_delta", "questions_delta",
            "correct_delta", "wrong_delta", "minutes_delta"
        )
    )

    # ── DELTA MODE ──
    if has_delta:
        xp_delta = int(stats_data.get("xp_delta", 0) or 0)
        sessions_delta = int(stats_data.get("sessions_delta", 0) or 0)
        questions_delta = int(stats_data.get("questions_delta", 0) or 0)
        correct_delta = int(stats_data.get("correct_delta", 0) or 0)
        wrong_delta = int(stats_data.get("wrong_delta", 0) or 0)
        minutes_delta = int(stats_data.get("minutes_delta", 0) or 0)
        streak_value = stats_data.get("streak", None)

        # UserStats — lifetime totals
        stats = db.query(UserStats).filter_by(user_id=current_user.id).first()
        if not stats:
            stats = UserStats(user_id=current_user.id)
            db.add(stats)
            db.flush()

        stats.xp = (stats.xp or 0) + xp_delta
        stats.level = compute_level_from_xp(stats.xp)
        stats.total_sessions = (stats.total_sessions or 0) + sessions_delta
        stats.total_questions = (stats.total_questions or 0) + questions_delta
        stats.total_correct = (stats.total_correct or 0) + correct_delta
        if stats.total_questions > 0:
            stats.accuracy = round((stats.total_correct / stats.total_questions) * 100, 2)
        if streak_value is not None:
            stats.streak = int(streak_value)
        stats.last_activity = datetime.utcnow()

        # UserDailyStats — today
        daily = db.query(UserDailyStats).filter_by(
            user_id=current_user.id, date=today
        ).first()
        if not daily:
            daily = UserDailyStats(user_id=current_user.id, date=today)
            db.add(daily)
            db.flush()

        daily.xp = (daily.xp or 0) + xp_delta
        daily.sessions = (daily.sessions or 0) + sessions_delta
        daily.total_questions = (daily.total_questions or 0) + questions_delta
        daily.correct = (daily.correct or 0) + correct_delta
        daily.wrong = (daily.wrong or 0) + wrong_delta
        daily.study_time_minutes = (daily.study_time_minutes or 0) + minutes_delta
        daily.level = stats.level
        if streak_value is not None:
            daily.streak = int(streak_value)
        if daily.total_questions > 0:
            daily.accuracy = round((daily.correct / daily.total_questions) * 100, 2)
        daily.updated_at = datetime.utcnow()

        db.commit()

        return {
            "success": True,
            "date": today.isoformat(),
            "saved": True,
            "mode": "delta",
            "xp": stats.xp,
            "level": stats.level,
            "accuracy": stats.accuracy,
        }

    # ── ABSOLUTE MODE (legacy) — overwrite today's UserDailyStats ──
    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date == today
    ).first()

    if stats:
        stats.xp = stats_data.get("xp", stats.xp)
        stats.level = stats_data.get("level", stats.level)
        stats.streak = stats_data.get("streak", stats.streak)
        stats.accuracy = stats_data.get("accuracy", stats.accuracy)
        stats.sessions = stats_data.get("sessions", stats.sessions)
        stats.total_questions = stats_data.get("totalQuestions", stats.total_questions)
        stats.correct = stats_data.get("correct", stats.correct)
        stats.wrong = stats_data.get("wrong", stats.wrong)
        stats.study_time_minutes = stats_data.get("studyTime", stats.study_time_minutes)
        stats.updated_at = datetime.utcnow()
    else:
        stats = UserDailyStats(
            user_id=current_user.id,
            date=today,
            xp=stats_data.get("xp", 0),
            level=stats_data.get("level", 1),
            streak=stats_data.get("streak", 0),
            accuracy=stats_data.get("accuracy", 0),
            sessions=stats_data.get("sessions", 0),
            total_questions=stats_data.get("totalQuestions", 0),
            correct=stats_data.get("correct", 0),
            wrong=stats_data.get("wrong", 0),
            study_time_minutes=stats_data.get("studyTime", 0)
        )
        db.add(stats)

    db.commit()

    return {
        "success": True,
        "date": today.isoformat(),
        "saved": True,
        "mode": "absolute",
    }


async def save_daily_stats(user_id: int, stats_data: dict, db: Session):
    today = date.today()

    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == user_id,
        UserDailyStats.date == today
    ).first()

    if stats:
        stats.xp = stats_data.get("xp", stats.xp)
        stats.level = stats_data.get("level", stats.level)
        stats.streak = stats_data.get("streak", stats.streak)
        stats.accuracy = stats_data.get("accuracy", stats.accuracy)
        stats.sessions = stats_data.get("sessions", stats.sessions)
        stats.total_questions = stats_data.get("totalQuestions", stats.total_questions)
        stats.correct = stats_data.get("correct", stats.correct)
        stats.wrong = stats_data.get("wrong", stats.wrong)
        stats.study_time_minutes = stats_data.get("studyTime", stats.study_time_minutes)
        stats.updated_at = datetime.utcnow()
    else:
        stats = UserDailyStats(
            user_id=user_id,
            date=today,
            xp=stats_data.get("xp", 0),
            level=stats_data.get("level", 1),
            streak=stats_data.get("streak", 0),
            accuracy=stats_data.get("accuracy", 0),
            sessions=stats_data.get("sessions", 0),
            total_questions=stats_data.get("totalQuestions", 0),
            correct=stats_data.get("correct", 0),
            wrong=stats_data.get("wrong", 0),
            study_time_minutes=stats_data.get("studyTime", 0)
        )
        db.add(stats)

    db.commit()


# ============================================================
# DAILY STATS — GET RANGE
# ============================================================

@router.get("/stats/range")
async def get_stats_range(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    start_date = date.today() - timedelta(days=days)

    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date >= start_date
    ).order_by(UserDailyStats.date).all()

    return {
        "range": f"Last {days} days",
        "start": start_date.isoformat(),
        "end": date.today().isoformat(),
        "stats": [
            {
                "date": s.date.isoformat(),
                "xp": s.xp,
                "level": s.level,
                "streak": s.streak,
                "accuracy": s.accuracy,
                "sessions": s.sessions,
                "studyTime": s.study_time_minutes
            }
            for s in stats
        ],
        "total": len(stats)
    }


# ============================================================
# DAILY STATS — TODAY'S PROGRESS
# ============================================================

@router.get("/stats/today")
async def get_today_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = date.today()

    session_count = db.query(PracticeSession).filter(
        PracticeSession.user_id == current_user.id,
        func.date(PracticeSession.completed_at) == today,
        PracticeSession.is_completed == True
    ).count()

    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date == today
    ).first()

    gamification = db.query(UserStats).filter(
        UserStats.user_id == current_user.id
    ).first()

    return {
        "sessions_today": session_count,
        "goal": 5,
        "remaining": max(0, 5 - session_count),
        "xp_today": stats.xp if stats else 0,
        "streak": gamification.streak if gamification else 0,
        "accuracy": stats.accuracy if stats else 0
    }


# ============================================================
# DAILY STATS — WEEKLY
# ============================================================

@router.get("/stats/weekly")
async def get_weekly_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    start_date = date.today() - timedelta(days=7)

    stats = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date >= start_date
    ).all()

    if not stats:
        sessions = db.query(PracticeSession).filter(
            PracticeSession.user_id == current_user.id,
            func.date(PracticeSession.completed_at) >= start_date,
            PracticeSession.is_completed == True
        ).all()

        daily_data = {}
        for s in sessions:
            if s.completed_at:
                day = s.completed_at.date().isoformat()
                if day not in daily_data:
                    daily_data[day] = {"sessions": 0, "xp": 0, "accuracy": 0, "correct": 0, "total": 0}
                daily_data[day]["sessions"] += 1
                daily_data[day]["correct"] += s.correct_answers or 0
                daily_data[day]["total"] += s.total_questions or 0

        weekly_data = []
        for day, data in daily_data.items():
            acc = (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0
            weekly_data.append({
                "day": day,
                "sessions": data["sessions"],
                "accuracy": round(acc, 1),
                "xp": data["sessions"] * 10
            })

        return {
            "range": "Last 7 days",
            "start": start_date.isoformat(),
            "end": date.today().isoformat(),
            "stats": weekly_data,
            "total_sessions": sum(d["sessions"] for d in weekly_data),
            "avg_accuracy": round(sum(d["accuracy"] for d in weekly_data) / len(weekly_data), 1) if weekly_data else 0
        }

    return {
        "range": "Last 7 days",
        "start": start_date.isoformat(),
        "end": date.today().isoformat(),
        "stats": [
            {
                "day": s.date.isoformat(),
                "sessions": s.sessions,
                "accuracy": s.accuracy,
                "xp": s.xp
            }
            for s in stats
        ],
        "total_sessions": sum(s.sessions for s in stats),
        "avg_accuracy": round(sum(s.accuracy for s in stats) / len(stats), 1) if stats else 0
    }


# ============================================================
# DAILY STATS — CLEANUP
# ============================================================

@router.delete("/stats/old")
async def cleanup_old_stats(
    days_to_keep: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cutoff = date.today() - timedelta(days=days_to_keep)

    deleted = db.query(UserDailyStats).filter(
        UserDailyStats.user_id == current_user.id,
        UserDailyStats.date < cutoff
    ).delete()

    db.commit()

    return {
        "success": True,
        "deleted": deleted,
        "days_kept": days_to_keep,
        "cutoff_date": cutoff.isoformat()
    }


# ============================================================
# ⭐ NEW — AI USAGE
# ============================================================

@router.get("/ai-usage")
async def get_ai_usage_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_ai_usage_today(db, current_user.id)


# ============================================================
# ⭐ NEW — HYDRATE
# ============================================================

@router.get("/hydrate")
async def hydrate(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from models import (
        StudyPlan,
        DailyTutorSession, DailyTutorLesson, DailyTutorQuiz,
        HyetutorCache, Mistake, DictionaryFavorite, WeaknessSnapshot,
    )

    today = date.today()

    user_resp = {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "avatar_url": current_user.avatar_url,
        "role": current_user.role.value if hasattr(current_user.role, "value") else current_user.role,
        "tier": current_user.tier.value if hasattr(current_user.tier, "value") else current_user.tier,
        "school": current_user.school,
        "country": current_user.country,
        "exam": current_user.exam,
        "bio": current_user.bio,
        "goal": current_user.goal,
        "subscription_expires": current_user.subscription_expires.isoformat() if current_user.subscription_expires else None,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }

    usage = get_ai_usage_today(db, current_user.id)

    plan = db.query(StudyPlan).filter_by(user_id=current_user.id, status="active").first()
    study_plan = None
    if plan:
        study_plan = {
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
            "exam_info": {
                "exam_type": plan.exam_type,
                "exam_date": plan.exam_date.isoformat() if plan.exam_date else None,
            },
            "plan": plan.plan_json,
        }

    session = db.query(DailyTutorSession).filter_by(user_id=current_user.id, date=today).first()
    daily_tutor_today = None
    if session:
        lesson = db.query(DailyTutorLesson).filter_by(user_id=current_user.id, date=today).first()
        quiz = db.query(DailyTutorQuiz).filter_by(user_id=current_user.id, date=today).first()
        daily_tutor_today = {
            "id": session.id,
            "date": session.date.isoformat(),
            "subject": session.subject,
            "topic": session.topic,
            "status": session.status,
            "currentStep": session.current_step,
            "answers": session.answers,
            "result": session.result,
            "reflection": session.reflection,
            "lesson": lesson.lesson_json if lesson else None,
            "quiz": quiz.quiz_json if quiz else None,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        }

    recent_rows = (
        db.query(DailyTutorSession)
        .filter_by(user_id=current_user.id, status="completed")
        .order_by(DailyTutorSession.date.desc())
        .limit(7)
        .all()
    )
    daily_tutor_recent = [
        {
            "id": r.id,
            "date": r.date.isoformat(),
            "subject": r.subject,
            "topic": r.topic,
            "accuracy": (r.result or {}).get("accuracy") if r.result else None,
            "status": r.status,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in recent_rows
    ]

    ht = db.query(HyetutorCache).filter_by(user_id=current_user.id, date=today).first()
    hyetutor_cache = ht.data if ht else None

    stats = db.query(UserStats).filter_by(user_id=current_user.id).first()
    gamification = {
        "xp": stats.xp if stats else 0,
        "total_xp": stats.xp if stats else 0,
        "level": stats.level if stats else 1,
        "streak": stats.streak if stats else 0,
        "longest_streak": stats.streak if stats else 0,
        "badges": stats.badges if stats and stats.badges else [],
    }

    mistakes_count = db.query(Mistake).filter_by(user_id=current_user.id, is_resolved=False).count()
    favs = db.query(DictionaryFavorite).filter_by(user_id=current_user.id).all()
    favorites = [f.word for f in favs]

    # ⭐ Today's weakness snapshot
    weakness_row = (
        db.query(WeaknessSnapshot)
        .filter(
            WeaknessSnapshot.user_id == current_user.id,
            cast(WeaknessSnapshot.generated_at, SQLDate) == today,
        )
        .order_by(WeaknessSnapshot.generated_at.desc())
        .first()
    )
    weakness_today = None
    if weakness_row:
        raw_snap = weakness_row.snapshot_json
        snap_list = raw_snap if isinstance(raw_snap, list) else []
        weakness_today = {
            "weakTopics": snap_list,
            "summary": weakness_row.summary or "",
            "generatedAt": weakness_row.generated_at.isoformat() if weakness_row.generated_at else None,
        }

    return {
        "user": user_resp,
        "ai_usage": usage,
        "study_plan": study_plan,
        "daily_tutor_today": daily_tutor_today,
        "daily_tutor_recent": daily_tutor_recent,
        "hyetutor_cache": hyetutor_cache,
        "gamification": gamification,
        "mistakes_count": mistakes_count,
        "favorites": favorites,
        "weakness_today": weakness_today,
    }
