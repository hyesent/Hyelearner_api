# ============================================================
# HYELEARNER: ROUTES — DAILY TUTOR
# Built by Hyesent.dev
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from database import get_db
from dependencies import call_ai_with_limit, get_current_user
from models import User, DailyTutorLesson, DailyTutorQuiz, DailyTutorSession
from schemas import (
    GenerateLessonRequest,
    GenerateLessonResponse,
    GenerateQuizRequest,
    GenerateQuizResponse,
    DailyTutorTodayResponse,
    DailyTutorSessionResponse,
    DailyTutorHistoryResponse,
    DailyTutorHistoryItem,
    DailyTutorSubmitQuizRequest,
    DailyTutorSubmitReflectionRequest,
)
from services.daily_tutor import daily_tutor_service

router = APIRouter(prefix="/daily-tutor", tags=["Daily Tutor"])


# ============================================================
# 1. GENERATE LESSON
# ============================================================

@router.post("/lesson", response_model=GenerateLessonResponse)
async def generate_lesson(
    payload: GenerateLessonRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()

    # One lesson per user per day
    existing = (
        db.query(DailyTutorLesson)
        .filter_by(user_id=user.id, date=today)
        .first()
    )
    if existing:
        return {
            "success": True,
            "generated_at": existing.generated_at.isoformat() if existing.generated_at else None,
            "lesson": existing.lesson_json,
            "from_cache": True,
        }

    # AI call under daily limit
    result = await call_ai_with_limit(
        db,
        user.id,
        daily_tutor_service.generate_lesson,
        payload.model_dump(),
    )

    if not result.get("success") or not result.get("lesson"):
        raise HTTPException(
            status_code=502,
            detail=result.get("error") or "Lesson generation failed",
        )

    lesson = DailyTutorLesson(
        user_id=user.id,
        date=today,
        subject=payload.subject,
        topic=payload.topic,
        lesson_json=result["lesson"],
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    return {
        "success": True,
        "generated_at": result.get("generated_at"),
        "lesson": lesson.lesson_json,
        "from_cache": False,
    }


# ============================================================
# 2. GENERATE QUIZ
# ============================================================

@router.post("/quiz", response_model=GenerateQuizResponse)
async def generate_quiz(
    payload: GenerateQuizRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()

    existing = (
        db.query(DailyTutorQuiz)
        .filter_by(user_id=user.id, date=today)
        .first()
    )
    if existing:
        return {
            "success": True,
            "generated_at": existing.generated_at.isoformat() if existing.generated_at else None,
            "quiz": existing.quiz_json,
            "from_cache": True,
        }

    result = await call_ai_with_limit(
        db,
        user.id,
        daily_tutor_service.generate_quiz,
        payload.model_dump(),
    )

    if not result.get("success") or not result.get("quiz"):
        raise HTTPException(
            status_code=502,
            detail=result.get("error") or "Quiz generation failed",
        )

    lesson = (
        db.query(DailyTutorLesson)
        .filter_by(user_id=user.id, date=today)
        .first()
    )

    quiz = DailyTutorQuiz(
        user_id=user.id,
        date=today,
        lesson_id=lesson.id if lesson else None,
        subject=payload.subject,
        topic=payload.topic,
        quiz_json=result["quiz"],
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    return {
        "success": True,
        "generated_at": result.get("generated_at"),
        "quiz": quiz.quiz_json,
        "from_cache": False,
    }


# ============================================================
# 3. GET TODAY
# ============================================================

@router.get("/today", response_model=DailyTutorTodayResponse)
def get_today(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()

    session = (
        db.query(DailyTutorSession)
        .filter_by(user_id=user.id, date=today)
        .first()
    )

    if not session:
        return {"session": None}

    lesson = db.query(DailyTutorLesson).filter_by(user_id=user.id, date=today).first()
    quiz = db.query(DailyTutorQuiz).filter_by(user_id=user.id, date=today).first()

    data = DailyTutorSessionResponse.model_validate(session).model_dump()
    data["lesson_json"] = lesson.lesson_json if lesson else None
    data["quiz_json"] = quiz.quiz_json if quiz else None

    return {"session": DailyTutorSessionResponse(**data)}


# ============================================================
# 4. GET HISTORY
# ============================================================

@router.get("/history", response_model=DailyTutorHistoryResponse)
def get_history(
    limit: int = 60,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(DailyTutorSession)
        .filter_by(user_id=user.id, status="completed")
        .order_by(DailyTutorSession.date.desc())
        .limit(limit)
        .all()
    )

    items = []
    for s in sessions:
        accuracy = None
        if s.result and isinstance(s.result, dict):
            accuracy = s.result.get("accuracy")
        items.append(DailyTutorHistoryItem(
            id=s.id,
            date=s.date,
            subject=s.subject,
            topic=s.topic,
            accuracy=accuracy,
            status=s.status,
            completed_at=s.completed_at,
        ))

    return {"sessions": items}


# ============================================================
# 5. GET SESSION BY DATE (read-only for past sessions)
# ============================================================

@router.get("/session/{date_key}", response_model=DailyTutorTodayResponse)
def get_session_by_date(
    date_key: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        target_date = date.fromisoformat(date_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (expected YYYY-MM-DD)")

    session = (
        db.query(DailyTutorSession)
        .filter_by(user_id=user.id, date=target_date)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    lesson = db.query(DailyTutorLesson).filter_by(user_id=user.id, date=target_date).first()
    quiz = db.query(DailyTutorQuiz).filter_by(user_id=user.id, date=target_date).first()

    data = DailyTutorSessionResponse.model_validate(session).model_dump()
    data["lesson_json"] = lesson.lesson_json if lesson else None
    data["quiz_json"] = quiz.quiz_json if quiz else None

    return {"session": DailyTutorSessionResponse(**data)}


# ============================================================
# 6. SUBMIT QUIZ
# ============================================================

@router.post("/session/{date_key}/submit", response_model=DailyTutorSessionResponse)
def submit_quiz(
    date_key: str,
    payload: DailyTutorSubmitQuizRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        target_date = date.fromisoformat(date_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    session = (
        db.query(DailyTutorSession)
        .filter_by(user_id=user.id, date=target_date)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    quiz = db.query(DailyTutorQuiz).filter_by(user_id=user.id, date=target_date).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = (quiz.quiz_json or {}).get("questions", [])
    answers = payload.answers or {}

    correct = 0
    wrong = 0
    for q in questions:
        if answers.get(q["id"]) == q["answer"]:
            correct += 1
        else:
            wrong += 1

    total = len(questions)
    accuracy = round((correct / total) * 100) if total else 0
    xp_earned = correct * 10

    result = {
        "correct": correct,
        "wrong": wrong,
        "total": total,
        "accuracy": accuracy,
        "xpEarned": xp_earned,
        "completedAt": date.today().isoformat(),
    }

    session.answers = answers
    session.result = result
    session.status = "completed"
    session.current_step = "reflection"
    db.commit()
    db.refresh(session)

    lesson = db.query(DailyTutorLesson).filter_by(user_id=user.id, date=target_date).first()
    data = DailyTutorSessionResponse.model_validate(session).model_dump()
    data["lesson_json"] = lesson.lesson_json if lesson else None
    data["quiz_json"] = quiz.quiz_json

    return DailyTutorSessionResponse(**data)


# ============================================================
# 7. SUBMIT REFLECTION
# ============================================================

@router.post("/session/{date_key}/reflection", response_model=DailyTutorSessionResponse)
def submit_reflection(
    date_key: str,
    payload: DailyTutorSubmitReflectionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        target_date = date.fromisoformat(date_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    session = (
        db.query(DailyTutorSession)
        .filter_by(user_id=user.id, date=target_date)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.reflection = {
        "feeling": payload.feeling,
        "note": payload.note,
        "submittedAt": date.today().isoformat(),
    }
    session.status = "completed"
    session.current_step = "done"
    db.commit()
    db.refresh(session)

    lesson = db.query(DailyTutorLesson).filter_by(user_id=user.id, date=target_date).first()
    quiz = db.query(DailyTutorQuiz).filter_by(user_id=user.id, date=target_date).first()

    data = DailyTutorSessionResponse.model_validate(session).model_dump()
    data["lesson_json"] = lesson.lesson_json if lesson else None
    data["quiz_json"] = quiz.quiz_json if quiz else None

    return DailyTutorSessionResponse(**data)
