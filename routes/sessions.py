from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import random

from database import get_db
from models import Session, User, UserStats, TopicMastery, Mistake, Question
from schemas import (
    SessionStart, SessionStartResponse, SessionSubmit, SessionSubmitResponse,
    SessionHistoryResponse, SessionQuestionResponse
)
from dependencies import get_current_user

router = APIRouter()


@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    data: SessionStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a new practice session"""
    # Get questions
    query = db.query(Question).filter(Question.subject.ilike(data.subject))
    
    if data.topic:
        query = query.filter(Question.topic.ilike(data.topic))
    if data.difficulty:
        query = query.filter(Question.difficulty == data.difficulty)
    
    questions = query.all()
    
    if len(questions) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No questions found for subject: {data.subject}"
        )
    
    # Select random questions
    selected = random.sample(questions, min(data.count, len(questions)))
    
    # Create session
    session = Session(
        user_id=current_user.id,
        subject=data.subject,
        topic=data.topic,
        total_questions=len(selected),
        question_ids=[q.id for q in selected],
        started_at=datetime.utcnow(),
        is_completed=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Format questions for response
    question_responses = []
    for q in selected:
        question_responses.append(
            SessionQuestionResponse(
                id=q.id,
                question=q.question,
                options=q.options,
                type=q.type,
                difficulty=q.difficulty.value if hasattr(q.difficulty, 'value') else q.difficulty,
                topic=q.topic,
                subject=q.subject
            )
        )
    
    return SessionStartResponse(
        id=session.id,
        subject=session.subject,
        topic=session.topic,
        total_questions=session.total_questions,
        questions=question_responses,
        is_timed=data.is_timed,
        time_limit=data.time_limit,
        started_at=session.started_at
    )


@router.post("/submit", response_model=SessionSubmitResponse)
async def submit_session(
    data: SessionSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit answers and calculate results"""
    session = db.query(Session).filter(
        Session.id == data.session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.is_completed:
        raise HTTPException(status_code=400, detail="Session already completed")
    
    # Get questions
    questions = db.query(Question).filter(Question.id.in_(session.question_ids)).all()
    question_map = {q.id: q for q in questions}
    
    # Calculate results
    correct = 0
    wrong = 0
    skipped = 0
    
    for q_id in session.question_ids:
        user_answer = data.answers.get(q_id)
        q = question_map.get(q_id)
        
        if not user_answer:
            skipped += 1
        elif q and user_answer == q.answer:
            correct += 1
        else:
            wrong += 1
            
            # Save mistake
            if q:
                mistake = Mistake(
                    user_id=current_user.id,
                    question_id=q_id,
                    user_answer=user_answer or "",
                    correct_answer=q.answer,
                    subject=q.subject,
                    topic=q.topic,
                    is_resolved=False
                )
                db.add(mistake)
    
    # Update session
    session.correct_answers = correct
    session.wrong_answers = wrong
    session.skipped = skipped
    session.accuracy = (correct / session.total_questions * 100) if session.total_questions > 0 else 0
    session.answers = data.answers
    session.time_taken = data.time_taken or 0
    session.is_completed = True
    session.completed_at = datetime.utcnow()
    
    # Update user stats
    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    if stats:
        stats.total_sessions += 1
        stats.total_questions += session.total_questions
        stats.total_correct += correct
        stats.accuracy = (stats.total_correct / stats.total_questions * 100) if stats.total_questions > 0 else 0
        stats.last_activity = datetime.utcnow()
        
        # Update streak
        if stats.last_activity:
            days_diff = (datetime.utcnow() - stats.last_activity).days
            if days_diff <= 1:
                stats.streak += 1
            else:
                stats.streak = 0
    
    # Calculate XP
    xp_earned = correct * 10 + (5 if session.accuracy >= 70 else 0) + (10 if session.accuracy >= 90 else 0)
    
    if stats:
        stats.xp += xp_earned
        stats.level = min(stats.xp // 100 + 1, 20)
    
    # ✅ UPDATE TOPIC MASTERY (with mastery_score)
    for q_id in session.question_ids:
        q = question_map.get(q_id)
        if not q:
            continue
        
        mastery = db.query(TopicMastery).filter(
            TopicMastery.user_id == current_user.id,
            TopicMastery.topic == q.topic,
            TopicMastery.subject == q.subject
        ).first()
        
        if not mastery:
            mastery = TopicMastery(
                user_id=current_user.id,
                subject=q.subject,
                topic=q.topic,
                correct=0,
                total=0,
                mastery_score=0.0
            )
            db.add(mastery)
        
        mastery.total += 1
        user_answer = data.answers.get(q_id)
        if user_answer and q and user_answer == q.answer:
            mastery.correct += 1
        
        # Calculate mastery score (0-100)
        if mastery.total > 0:
            mastery.mastery_score = (mastery.correct / mastery.total) * 100
        
        mastery.updated_at = datetime.utcnow()
    
    db.commit()
    
    return SessionSubmitResponse(
        session_id=session.id,
        score=correct,
        total=session.total_questions,
        correct=correct,
        wrong=wrong,
        skipped=skipped,
        accuracy=session.accuracy,
        xp_earned=xp_earned,
        completed_at=session.completed_at
    )


@router.get("/history", response_model=List[SessionHistoryResponse])
async def get_session_history(
    subject: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's session history"""
    query = db.query(Session).filter(
        Session.user_id == current_user.id,
        Session.is_completed == True
    )
    
    if subject:
        query = query.filter(Session.subject.ilike(subject))
    
    sessions = query.order_by(Session.completed_at.desc()).offset(offset).limit(limit).all()
    
    return sessions


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific session"""
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session
