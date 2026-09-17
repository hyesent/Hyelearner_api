# ============================================================
# HYELEARNER: ROUTES — HYETUTOR
# Built by Hyesent.dev
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta

from database import get_db
from models import User, HyetutorCache, Mission, Reflection, UserStats, HyetutorChat
from dependencies import get_current_user, call_ai_with_limit
from services.hyetutor import hyetutor_service
from services.ai import ai_service

router = APIRouter()


# ============================================================
# 1. POST /analyze
# ============================================================

@router.post("/analyze")
async def analyze_hyetutor(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = request.get("data", {})
    exam_date = request.get("exam_date")

    # Bundle the AI call via the limit wrapper
    parsed_data = await call_ai_with_limit(
        db,
        current_user.id,
        hyetutor_service.generate_daily_digest,
        data,
        exam_date,
    )

    parsed_data["success"] = True
    parsed_data["user_id"] = str(current_user.id)
    parsed_data["generated_at"] = datetime.utcnow().isoformat()
    parsed_data["date"] = date.today().isoformat()

    # Replace today's cache
    existing = (
        db.query(HyetutorCache)
        .filter_by(user_id=current_user.id, date=date.today())
        .first()
    )
    if existing:
        db.delete(existing)

    db.add(HyetutorCache(
        user_id=current_user.id,
        date=date.today(),
        data=parsed_data,
        generated_at=datetime.utcnow(),
    ))

    # Clear today's missions and re-insert
    db.query(Mission).filter_by(
        user_id=current_user.id, date=date.today()
    ).delete()

    for m in parsed_data.get("missions", []):
        db.add(Mission(
            user_id=current_user.id,
            date=date.today(),
            mission_code=m.get("id"),
            text=m.get("text", ""),
            reason=m.get("reason", ""),
            priority=m.get("priority", "medium"),
            xp_reward=m.get("xp_reward", 25),
            estimated_time=m.get("estimated_time", 30),
            completed=False,
            order=m.get("order", 0),
        ))

    db.commit()
    return parsed_data


# ============================================================
# 2. GET /cached
# ============================================================

@router.get("/cached")
async def get_cached_hyetutor(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cache = (
        db.query(HyetutorCache)
        .filter_by(user_id=current_user.id, date=date.today())
        .first()
    )
    if not cache:
        raise HTTPException(404, "No cached data for today")

    return {
        "cached": True,
        "date": cache.date.isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "data": cache.data,
    }


# ============================================================
# 3. POST /mission/{id}/complete — pure DB, no AI
# ============================================================

@router.post("/mission/{mission_id}/complete")
async def complete_mission(
    mission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mission = (
        db.query(Mission)
        .filter_by(user_id=current_user.id, mission_code=mission_id)
        .first()
    )
    if not mission:
        raise HTTPException(404, f"Mission '{mission_id}' not found")
    if mission.completed:
        raise HTTPException(400, "Mission already completed")

    mission.completed = True
    mission.completed_at = datetime.utcnow()

    stats = db.query(UserStats).filter_by(user_id=current_user.id).first()
    if not stats:
        stats = UserStats(user_id=current_user.id)
        db.add(stats)

    stats.xp += mission.xp_reward
    stats.level = stats.xp // 100 + 1

    db.commit()

    return {
        "success": True,
        "mission": {
            "id": mission.mission_code,
            "completed": True,
            "xp_earned": mission.xp_reward,
        },
        "xp_updated": stats.xp,
        "level_updated": stats.level,
    }


# ============================================================
# 4. POST /reflection — pure DB, no AI
# ============================================================

@router.post("/reflection")
async def submit_reflection(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reflection = Reflection(
        user_id=current_user.id,
        date=date.fromisoformat(request.get("date", date.today().isoformat())),
        mood=request.get("mood", "okay"),
        notes=request.get("notes"),
        time_taken=request.get("time_taken", 0),
        sessions_completed=request.get("sessions_completed", 0),
        distractions=request.get("distractions"),
    )
    db.add(reflection)
    db.commit()

    adjustments = {"workload_reduced": False, "new_load": 2.5}
    mood = request.get("mood")
    if mood == "difficult":
        adjustments["workload_reduced"] = True
        adjustments["new_load"] = max(1.5, request.get("time_taken", 2) - 0.5)
    elif mood == "great":
        adjustments["new_load"] = min(4, request.get("time_taken", 2) + 0.5)

    return {
        "success": True,
        "adjustments": adjustments,
        "new_schedule": {
            "date": date.today().isoformat(),
            "total_hours": adjustments["new_load"],
        },
    }


# ============================================================
# 5. POST /chat — AI
# ============================================================

@router.post("/chat")
async def hyetutor_chat(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = request.get("question")
    if not question:
        raise HTTPException(400, "Question is required")

    cache = (
        db.query(HyetutorCache)
        .filter_by(user_id=current_user.id, date=date.today())
        .first()
    )

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

    prompt = f"""You are HyeTutor, an AI study coach.

{context}

Student question: {question}

Provide a helpful, actionable response. Be concise and supportive."""

    # Wrapper expects an awaitable that returns a string or dict.
    async def _chat_call():
        text = None
        if ai_service.gemini:
            try:
                r = ai_service.gemini.generate_content(prompt)
                text = r.text
            except Exception as e:
                print(f"❌ Gemini chat error: {e}")
        if not text and ai_service.groq:
            try:
                r = ai_service.groq.chat.completions.create(
                    model=ai_service.groq_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                    temperature=0.7,
                )
                text = r.choices[0].message.content
            except Exception as e:
                print(f"❌ Groq chat error: {e}")
        if not text:
            return {"success": False, "error": "AI unavailable"}
        return {"success": True, "answer": text}

    result = await call_ai_with_limit(db, current_user.id, _chat_call)

    answer = result.get("answer") if isinstance(result, dict) else str(result)

    # Save chat history
    try:
        db.add(HyetutorChat(
            user_id=current_user.id,
            question=question,
            answer=answer,
            confidence=85,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ Failed to save chat: {e}")

    return {
        "success": True,
        "answer": answer or "Could not generate response.",
        "confidence": 85,
        "suggested_actions": [
            {"action": "Review your weak topics", "duration": 30},
            {"action": "Practice daily", "duration": 45},
        ],
    }


# ============================================================
# 6. GET /chat/history
# ============================================================

@router.get("/chat/history")
def get_chat_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(HyetutorChat)
        .filter_by(user_id=current_user.id)
        .order_by(HyetutorChat.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "messages": [
            {
                "id": r.id,
                "question": r.question,
                "answer": r.answer,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }
