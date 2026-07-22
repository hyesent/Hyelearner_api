# ============================================================
# routes/hyetutor.py — HyeTutor API (5 Core Endpoints)
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import json

from database import get_db
from models import User, HyetutorCache, Mission, Reflection, UserStats
from dependencies import get_current_user
from services.hyetutor import hyetutor_service

router = APIRouter()


# ============================================================
# 1. POST /hyetutor/analyze — Full AI Analysis
# ============================================================

@router.post("/analyze")
async def analyze_hyetutor(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Full AI analysis with bundled data from frontend.
    Returns: missions, subjects, forecast, insights, habits, etc.
    """
    
    data = request.get("data", {})
    exam_date = request.get("exam_date")
    
    # ✅ Use the service method that calls AI properly
    parsed_data = await hyetutor_service.generate_daily_digest(data, exam_date)
    
    # Add metadata
    parsed_data["success"] = True
    parsed_data["user_id"] = str(current_user.id)
    parsed_data["generated_at"] = datetime.utcnow().isoformat()
    parsed_data["date"] = date.today().isoformat()
    
    # Save to cache (replace if exists)
    existing = db.query(HyetutorCache).filter(
        HyetutorCache.user_id == current_user.id,
        HyetutorCache.date == date.today()
    ).first()
    
    if existing:
        db.delete(existing)
    
    cache = HyetutorCache(
        user_id=current_user.id,
        date=date.today(),
        data=parsed_data,
        generated_at=datetime.utcnow()
    )
    db.add(cache)
    
    # ✅ Save missions with mission_code (frontend ID)
    for mission_data in parsed_data.get("missions", []):
        mission = Mission(
            user_id=current_user.id,
            date=date.today(),
            mission_code=mission_data.get("id"),  # ✅ Store frontend ID
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
# 2. GET /hyetutor/cached — Get Cached Results
# ============================================================

@router.get("/cached")
async def get_cached_hyetutor(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cached results (no AI call). Returns 404 if no cache."""
    
    cache = db.query(HyetutorCache).filter(
        HyetutorCache.user_id == current_user.id,
        HyetutorCache.date == date.today()
    ).first()
    
    if not cache:
        raise HTTPException(404, "No cached data for today")
    
    return {
        "cached": True,
        "date": cache.date.isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "data": cache.data
    }


# ============================================================
# 3. POST /hyetutor/mission/{id}/complete — Mark Mission Complete
# ============================================================

@router.post("/mission/{mission_id}/complete")
async def complete_mission(
    mission_id: str,  # ✅ Changed from int to str to match frontend IDs like "mission_001"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a mission as complete and award XP."""
    
    # ✅ Find by mission_code (string ID from frontend)
    mission = db.query(Mission).filter(
        Mission.user_id == current_user.id,
        Mission.mission_code == mission_id
    ).first()
    
    if not mission:
        raise HTTPException(404, f"Mission '{mission_id}' not found")
    
    if mission.completed:
        raise HTTPException(400, "Mission already completed")
    
    # Mark complete
    mission.completed = True
    mission.completed_at = datetime.utcnow()
    
    # Award XP
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    if not stats:
        stats = UserStats(user_id=current_user.id)
        db.add(stats)
    
    stats.xp += mission.xp_reward
    stats.level = stats.xp // 100 + 1
    
    db.commit()
    
    return {
        "success": True,
        "mission": {
            "id": mission.mission_code,  # ✅ Return the frontend ID
            "completed": True,
            "xp_earned": mission.xp_reward
        },
        "xp_updated": stats.xp,
        "level_updated": stats.level
    }


# ============================================================
# 4. POST /hyetutor/reflection — Submit Daily Reflection
# ============================================================

@router.post("/reflection")
async def submit_reflection(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit daily reflection. AI adjusts plan based on mood."""
    
    reflection = Reflection(
        user_id=current_user.id,
        date=date.fromisoformat(request.get("date", date.today().isoformat())),
        mood=request.get("mood", "okay"),
        notes=request.get("notes"),
        time_taken=request.get("time_taken", 0),
        sessions_completed=request.get("sessions_completed", 0),
        distractions=request.get("distractions")
    )
    db.add(reflection)
    db.commit()
    
    # Simple adjustments based on mood
    adjustments = {"workload_reduced": False, "new_load": 2.5}
    
    if request.get("mood") == "difficult":
        adjustments["workload_reduced"] = True
        adjustments["new_load"] = max(1.5, request.get("time_taken", 2) - 0.5)
    elif request.get("mood") == "great":
        adjustments["new_load"] = min(4, request.get("time_taken", 2) + 0.5)
    
    return {
        "success": True,
        "adjustments": adjustments,
        "new_schedule": {
            "date": date.today().isoformat(),
            "total_hours": adjustments["new_load"]
        }
    }


# ============================================================
# 5. POST /hyetutor/chat — AI Chat with Context
# ============================================================

@router.post("/chat")
async def hyetutor_chat(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI chat with context from student's data."""
    
    question = request.get("question")
    if not question:
        raise HTTPException(400, "Question is required")
    
    # Get today's cache for context
    cache = db.query(HyetutorCache).filter(
        HyetutorCache.user_id == current_user.id,
        HyetutorCache.date == date.today()
    ).first()
    
    context = ""
    if cache and cache.data:
        d = cache.data
        context = f"""
Student's data:
- Subjects: {', '.join([s.get('name', '') for s in d.get('subjects', [])])}
- Weak topics: {', '.join([s.get('name', '') for s in d.get('subjects', []) if s.get('priority') == 'critical'])}
- Exam readiness: {d.get('performance', {}).get('exam_readiness', 0)}%
- Streak: {d.get('momentum', {}).get('streak', 0)} days
"""

    prompt = f"""
You are HyeTutor, an AI study coach.

{context}

Student question: {question}

Provide a helpful, actionable response. Be concise and supportive.
"""

    try:
        from services.ai import ai_service
        # ✅ Use proper Gemini call
        response_text = None
        if ai_service.gemini:
            try:
                response = ai_service.gemini.generate_content(prompt)
                response_text = response.text
            except Exception as e:
                print(f"❌ Gemini chat error: {e}")
        
        # ✅ Fallback to Groq
        if not response_text and ai_service.groq:
            try:
                response = ai_service.groq.chat.completions.create(
                    model=ai_service.groq_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                    temperature=0.7
                )
                response_text = response.choices[0].message.content
            except Exception as e:
                print(f"❌ Groq chat error: {e}")
                
    except Exception as e:
        response_text = "I'm having trouble connecting. Please try again."

    return {
        "success": True,
        "answer": response_text or "Could not generate response.",
        "confidence": 85,
        "suggested_actions": [
            {"action": "Review your weak topics", "duration": 30},
            {"action": "Practice daily", "duration": 45}
        ]
    }
