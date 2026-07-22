# ============================================================
# routes/hyetutor.py — HyeTutor API Endpoints
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import json
import uuid
import random

from database import get_db
from models import User, HyetutorCache, Mission, Reflection, UserStats
from dependencies import get_current_user
from services.hyetutor import hyetutor_service

router = APIRouter()


# ============================================================
# 1. ANALYZE — Full AI Analysis
# ============================================================

@router.post("/analyze")
async def analyze_hyetutor(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Full AI analysis with bundled data from frontend.
    Generates daily missions, insights, confidence scores, and more.
    """
    
    # Extract data from request
    data = request.get("data", {})
    exam_date = request.get("exam_date")
    difficulty_preference = request.get("difficulty_preference", "balanced")
    
    # Build AI prompt
    prompt = hyetutor_service.build_ai_prompt(data, exam_date)
    
    # Get AI response (Gemini primary, Groq fallback)
    try:
        from services.ai import ai_service
        
        # Try Gemini first
        response_text = await ai_service._generate_gemini(prompt)
        if not response_text:
            # Fallback to Groq
            response_text = await ai_service._generate_groq(prompt, max_tokens=2500)
        
        # Parse response
        parsed_data = hyetutor_service.parse_ai_response(response_text)
        
    except Exception as e:
        print(f"❌ AI analysis failed: {e}")
        parsed_data = hyetutor_service._get_fallback_response()
    
    # Add metadata
    parsed_data["success"] = True
    parsed_data["user_id"] = str(current_user.id)
    parsed_data["generated_at"] = datetime.utcnow().isoformat()
    parsed_data["date"] = date.today().isoformat()
    
    # Save to cache
    cache = HyetutorCache(
        user_id=current_user.id,
        date=date.today(),
        data=parsed_data,
        generated_at=datetime.utcnow()
    )
    
    # Delete old cache for today if exists
    old_cache = db.query(HyetutorCache).filter(
        HyetutorCache.user_id == current_user.id,
        HyetutorCache.date == date.today()
    ).first()
    if old_cache:
        db.delete(old_cache)
    
    db.add(cache)
    
    # Save missions to database
    for mission_data in parsed_data.get("missions", []):
        # Check if mission already exists for today
        existing = db.query(Mission).filter(
            Mission.user_id == current_user.id,
            Mission.date == date.today(),
            Mission.text == mission_data.get("text", "")
        ).first()
        
        if not existing:
            mission = Mission(
                user_id=current_user.id,
                date=date.today(),
                text=mission_data.get("text", ""),
                reason=mission_data.get("reason", ""),
                priority=mission_data.get("priority", "medium"),
                xp_reward=mission_data.get("xp_reward", 25),
                estimated_time=mission_data.get("estimated_time", 30),
                completed=False,
                order=mission_data.get("order", 0)
            )
            db.add(mission)
    
    db.commit()
    
    return parsed_data


# ============================================================
# 2. CACHED — Get Cached Results
# ============================================================

@router.get("/cached")
async def get_cached_hyetutor(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get cached HyeTutor results (no AI call).
    Returns cached data if available for today.
    """
    
    cache = db.query(HyetutorCache).filter(
        HyetutorCache.user_id == current_user.id,
        HyetutorCache.date == date.today()
    ).first()
    
    if cache:
        return {
            "cached": True,
            "date": cache.date.isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "data": cache.data
        }
    
    # No cache found
    return {
        "cached": False,
        "date": date.today().isoformat(),
        "expires_at": datetime.utcnow().isoformat(),
        "data": None
    }


# ============================================================
# 3. MISSION COMPLETE — Mark Mission as Done
# ============================================================

@router.post("/mission/{mission_id}/complete")
async def complete_mission(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a mission as complete.
    Awards XP to the user.
    """
    
    # Find the mission
    mission = db.query(Mission).filter(
        Mission.id == mission_id,
        Mission.user_id == current_user.id
    ).first()
    
    if not mission:
        raise HTTPException(404, "Mission not found")
    
    if mission.completed:
        raise HTTPException(400, "Mission already completed")
    
    # Mark as complete
    mission.completed = True
    mission.completed_at = datetime.utcnow()
    
    # Award XP
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    xp_earned = mission.xp_reward
    
    if not stats:
        stats = UserStats(user_id=current_user.id)
        db.add(stats)
    
    stats.xp += xp_earned
    stats.level = stats.xp // 100 + 1
    stats.total_sessions = (stats.total_sessions or 0) + 1
    
    db.commit()
    
    # Check for badge unlocks (simplified)
    badge_unlocked = None
    if stats.xp >= 500 and "xp_collector" not in (stats.badges or []):
        badge_unlocked = "XP Collector"
        badges = stats.badges or []
        badges.append("xp_collector")
        stats.badges = badges
    
    if stats.xp >= 1000 and "xp_master" not in (stats.badges or []):
        badge_unlocked = "XP Master"
        badges = stats.badges or []
        badges.append("xp_master")
        stats.badges = badges
    
    db.commit()
    
    # Update cache with new mission status
    cache = db.query(HyetutorCache).filter(
        HyetutorCache.user_id == current_user.id,
        HyetutorCache.date == date.today()
    ).first()
    
    if cache and cache.data:
        cache_data = cache.data
        for m in cache_data.get("missions", []):
            if m.get("id") == str(mission_id) or m.get("id") == mission_id:
                m["completed"] = True
                break
        
        # Update progress
        total_missions = len(cache_data.get("missions", []))
        completed_missions = sum(1 for m in cache_data.get("missions", []) if m.get("completed", False))
        cache_data["missions_progress"] = int((completed_missions / total_missions) * 100) if total_missions > 0 else 0
        
        cache.data = cache_data
        db.commit()
    
    return {
        "success": True,
        "mission": {
            "id": str(mission.id),
            "completed": True,
            "xp_earned": xp_earned,
            "total_xp": stats.xp
        },
        "xp_updated": stats.xp,
        "level_updated": stats.level,
        "badge_unlocked": badge_unlocked
    }


# ============================================================
# 4. MISSIONS — Get Today's Missions
# ============================================================

@router.get("/missions")
async def get_today_missions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get today's missions from cache or database.
    """
    
    # Try cache first
    cache = db.query(HyetutorCache).filter(
        HyetutorCache.user_id == current_user.id,
        HyetutorCache.date == date.today()
    ).first()
    
    if cache and cache.data and cache.data.get("missions"):
        return {
            "missions": cache.data.get("missions", []),
            "total_xp": sum(m.get("xp_reward", 0) for m in cache.data.get("missions", []) if not m.get("completed", False)),
            "completed_count": sum(1 for m in cache.data.get("missions", []) if m.get("completed", False)),
            "progress": cache.data.get("missions_progress", 0)
        }
    
    # Fallback to database
    missions = db.query(Mission).filter(
        Mission.user_id == current_user.id,
        Mission.date == date.today()
    ).order_by(Mission.order).all()
    
    return {
        "missions": [
            {
                "id": str(m.id),
                "text": m.text,
                "reason": m.reason,
                "priority": m.priority,
                "xp_reward": m.xp_reward,
                "estimated_time": m.estimated_time,
                "completed": m.completed,
                "order": m.order
            }
            for m in missions
        ],
        "total_xp": sum(m.xp_reward for m in missions if not m.completed),
        "completed_count": sum(1 for m in missions if m.completed),
        "progress": int((sum(1 for m in missions if m.completed) / len(missions)) * 100) if missions else 0
    }


# ============================================================
# 5. REFLECTION — Submit Daily Reflection
# ============================================================

@router.post("/reflection")
async def submit_reflection(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit daily reflection.
    AI adjusts the study plan based on the reflection.
    """
    
    # Extract data
    reflection_date = request.get("date", date.today().isoformat())
    mood = request.get("mood", "okay")
    notes = request.get("notes")
    time_taken = request.get("time_taken", 0)
    sessions_completed = request.get("sessions_completed", 0)
    distractions = request.get("distractions")
    
    # Save reflection
    reflection = Reflection(
        user_id=current_user.id,
        date=date.fromisoformat(reflection_date),
        mood=mood,
        notes=notes,
        time_taken=time_taken,
        sessions_completed=sessions_completed,
        distractions=distractions
    )
    db.add(reflection)
    db.commit()
    
    # Generate adjustments based on reflection
    adjustments = {
        "workload_reduced": False,
        "physics_increased": False,
        "new_topics_blocked": False,
        "new_load": 2.5,
        "recommendation": ""
    }
    
    if mood == "difficult":
        adjustments["workload_reduced"] = True
        adjustments["new_load"] = max(1.5, time_taken - 0.5)
        adjustments["recommendation"] = "Tomorrow's workload reduced to help you recover."
    elif mood == "great":
        adjustments["new_load"] = min(4, time_taken + 0.5)
        adjustments["recommendation"] = "You're doing great! Maintain this momentum."
    else:
        adjustments["new_load"] = time_taken
        adjustments["recommendation"] = "Keep up the consistent effort."
    
    # If notes mention a specific subject, adjust
    if notes and "physics" in notes.lower():
        adjustments["physics_increased"] = True
    
    return {
        "success": True,
        "adjustments": adjustments,
        "new_schedule": {
            "date": date.today().isoformat(),
            "tasks": [
                {"text": "Review yesterday's weak topics", "duration": 30},
                {"text": "Practice new concepts", "duration": 45}
            ],
            "total_hours": adjustments["new_load"]
        }
    }


# ============================================================
# 6. CHAT — AI Chat with Context
# ============================================================

@router.post("/chat")
async def hyetutor_chat(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI chat with context from the student's data.
    """
    
    question = request.get("question", "")
    context = request.get("context", {})
    
    if not question:
        raise HTTPException(400, "Question is required")
    
    # Get cached data for context
    cache = db.query(HyetutorCache).filter(
        HyetutorCache.user_id == current_user.id,
        HyetutorCache.date == date.today()
    ).first()
    
    # Build prompt with context
    context_text = ""
    if cache and cache.data:
        cache_data = cache.data
        context_text = f"""
Student's latest data:
- Subjects: {', '.join([s.get('name', '') for s in cache_data.get('subjects', [])])}
- Weak topics: {', '.join([s.get('name', '') for s in cache_data.get('subjects', []) if s.get('priority') == 'critical'])}
- Exam readiness: {cache_data.get('performance', {}).get('exam_readiness', 0)}%
- Streak: {cache_data.get('momentum', {}).get('streak', 0)} days
- Motivation: {cache_data.get('motivation', '')}
"""

    prompt = f"""
You are HyeTutor, an AI study coach for the Hyelearner platform.

{context_text}

Student question: {question}

Provide a helpful, actionable response. Be specific and encouraging.
If the student is struggling, suggest concrete steps.
If they're doing well, reinforce positive habits.

Keep your response clear, concise, and supportive.
"""

    try:
        from services.ai import ai_service
        
        # Try Gemini first
        response_text = await ai_service._generate_gemini(prompt)
        if not response_text:
            # Fallback to Groq
            response_text = await ai_service._generate_groq(prompt, max_tokens=800)
    except Exception as e:
        print(f"❌ Chat error: {e}")
        response_text = "I'm having trouble connecting. Please try again in a moment."
    
    return {
        "success": True,
        "answer": response_text or "I couldn't generate a response. Please try again.",
        "confidence": 85,
        "suggested_actions": [
            {"action": "Review your weak topics", "duration": 30},
            {"action": "Practice daily", "duration": 45}
        ],
        "related_insights": [
            "Consistency is key to improvement.",
            "Focus on one subject at a time."
        ]
    }


# ============================================================
# 7. DIFFICULTY — Update Plan Difficulty
# ============================================================

@router.get("/difficulty/options")
async def get_difficulty_options(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get available difficulty options for the study plan.
    """
    
    return {
        "current": "balanced",
        "options": [
            {"value": "easy", "label": "Easy", "hours_per_day": 1.5, "intensity": "low"},
            {"value": "balanced", "label": "Balanced", "hours_per_day": 2.5, "intensity": "medium"},
            {"value": "aggressive", "label": "Aggressive", "hours_per_day": 4.0, "intensity": "high"}
        ]
    }


@router.post("/difficulty")
async def update_difficulty(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the student's study plan difficulty.
    """
    
    difficulty = request.get("difficulty", "balanced")
    
    # TODO: Store preference in UserSettings or User table
    # For now, just return success
    
    return {
        "success": True,
        "difficulty": difficulty,
        "message": f"Plan difficulty updated to {difficulty}",
        "updated_at": datetime.utcnow().isoformat()
    }


# ============================================================
# 8. MISSION HISTORY — Get Past Missions
# ============================================================

@router.get("/missions/history")
async def get_mission_history(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get mission history for the past N days.
    """
    
    start_date = date.today() - timedelta(days=days)
    
    missions = db.query(Mission).filter(
        Mission.user_id == current_user.id,
        Mission.date >= start_date
    ).order_by(Mission.date.desc(), Mission.order).all()
    
    return {
        "missions": [
            {
                "id": str(m.id),
                "date": m.date.isoformat(),
                "text": m.text,
                "completed": m.completed,
                "xp_reward": m.xp_reward
            }
            for m in missions
        ],
        "total": len(missions),
        "completed": sum(1 for m in missions if m.completed),
        "total_xp_earned": sum(m.xp_reward for m in missions if m.completed)
    }


# ============================================================
# 9. REFLECTION HISTORY
# ============================================================

@router.get("/reflection/history")
async def get_reflection_history(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get reflection history for the past N days.
    """
    
    start_date = date.today() - timedelta(days=days)
    
    reflections = db.query(Reflection).filter(
        Reflection.user_id == current_user.id,
        Reflection.date >= start_date
    ).order_by(Reflection.date.desc()).all()
    
    return {
        "reflections": [
            {
                "id": str(r.id),
                "date": r.date.isoformat(),
                "mood": r.mood,
                "notes": r.notes,
                "time_taken": r.time_taken,
                "sessions_completed": r.sessions_completed
            }
            for r in reflections
        ]
    }


# ============================================================
# 10. REWARDS — Get Available Rewards
# ============================================================

@router.get("/rewards")
async def get_rewards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get available and earned rewards.
    """
    
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    badges = stats.badges if stats else []
    
    # Define all possible rewards
    all_rewards = [
        {"id": "week_1", "label": "Week 1 Complete", "xp": 100, "badge": "Week Warrior"},
        {"id": "week_2", "label": "Week 2 Complete", "xp": 200, "badge": "Week Warrior"},
        {"id": "week_3", "label": "Week 3 Complete", "xp": 300, "badge": "Week Warrior"},
        {"id": "week_4", "label": "Week 4 Complete", "xp": 400, "badge": "Week Warrior"},
        {"id": "streak_7", "label": "7-Day Streak", "xp": 150, "badge": "Streak Starter"},
        {"id": "streak_14", "label": "14-Day Streak", "xp": 300, "badge": "Streak Master"},
        {"id": "streak_30", "label": "30-Day Streak", "xp": 500, "badge": "Streak Legend"},
        {"id": "questions_100", "label": "100 Questions", "xp": 100, "badge": "Question Solver"},
        {"id": "questions_500", "label": "500 Questions", "xp": 300, "badge": "Question Master"},
        {"id": "questions_1000", "label": "1000 Questions", "xp": 500, "badge": "Question Legend"},
        {"id": "level_5", "label": "Level 5", "xp": 100, "badge": "Level Up"},
        {"id": "level_10", "label": "Level 10", "xp": 200, "badge": "Level Master"},
        {"id": "level_20", "label": "Level 20", "xp": 500, "badge": "Level Legend"},
    ]
    
    # Determine which are unlocked
    earned = []
    available = []
    
    for reward in all_rewards:
        is_unlocked = reward["id"] in badges
        if is_unlocked:
            earned.append({**reward, "claimed": True})
        else:
            available.append(reward)
    
    return {
        "earned": earned,
        "available": available[:5]  # Show top 5 available
    }


# ============================================================
# 11. EMERGENCY — Emergency Mode Status
# ============================================================

@router.get("/emergency")
async def get_emergency_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if emergency mode should activate.
    """
    
    # Get exam date from user's planner
    planner = db.query(RevisionPlanner).filter(
        RevisionPlanner.user_id == current_user.id
    ).first()
    
    days_to_exam = 0
    if planner and planner.exam_date:
        days_to_exam = (planner.exam_date.date() - date.today()).days
    
    # Check if emergency mode should activate
    active = False
    reason = None
    
    if days_to_exam <= 7:
        active = True
        reason = f"Exam is in {days_to_exam} days"
    elif days_to_exam <= 14:
        # Check if too many topics remaining
        cache = db.query(HyetutorCache).filter(
            HyetutorCache.user_id == current_user.id,
            HyetutorCache.date == date.today()
        ).first()
        
        if cache and cache.data:
            topics_remaining = cache.data.get("quick_stats", {}).get("topics_remaining", 0)
            if topics_remaining > days_to_exam * 2:
                active = True
                reason = f"{topics_remaining} topics remaining with {days_to_exam} days left"
    
    return {
        "active": active,
        "reason": reason,
        "days_to_exam": days_to_exam,
        "intensity": "high" if active else "normal",
        "mode": {
            "no_new_lessons": active,
            "revision_only": active,
            "high_weight_topics_only": active,
            "daily_hours": 4 if active else 2
        },
        "recommendations": [
            "Focus on high-weight topics only." if active else "Continue your current pace.",
            "No new lessons — revision only." if active else "Keep learning new topics.",
            f"Study {4 if active else 2} hours per day until exam."
        ]
    }


# ============================================================
# 12. FORECAST — Study Forecast
# ============================================================

@router.get("/forecast")
async def get_forecast(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get study forecast and pace analysis.
    """
    
    # Get cached data
    cache = db.query(HyetutorCache).filter(
        HyetutorCache.user_id == current_user.id,
        HyetutorCache.date == date.today()
    ).first()
    
    if cache and cache.data:
        return cache.data.get("forecast", {})
    
    # Fallback
    return {
        "days_remaining": 0,
        "topics_remaining": 0,
        "topics_per_day_needed": 0,
        "current_pace": 0,
        "pace_status": "on_track",
        "estimated_completion": "",
        "days_behind": 0,
        "completion_probability": 50,
        "needs_adjustment": False,
        "recommendation": "Keep studying consistently.",
        "daily_target": 2
    }


# ============================================================
# 13. INSIGHTS — Get AI Insights
# ============================================================

@router.get("/insights")
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-generated study insights.
    """
    
    # Get cached data
    cache = db.query(HyetutorCache).filter(
        HyetutorCache.user_id == current_user.id,
        HyetutorCache.date == date.today()
    ).first()
    
    if cache and cache.data:
        return cache.data.get("insights", [])
    
    # Fallback
    return [
        {
            "type": "positive",
            "message": "Keep up the good work! Consistency is key.",
            "action": None,
            "priority": "medium",
            "suggestion": None
        }
    ]
