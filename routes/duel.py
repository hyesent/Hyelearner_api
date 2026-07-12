from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import random

from database import get_db
from models import User, Duel, Question, UserStats
from schemas import DuelCreate, DuelJoin, DuelSubmit, DuelResponse
from dependencies import get_current_user

router = APIRouter()


@router.post("/create")
async def create_duel(
    data: DuelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new duel challenge"""
    # Check opponent exists
    opponent = db.query(User).filter(User.id == data.opponent_id).first()
    if not opponent:
        raise HTTPException(status_code=404, detail="Opponent not found")
    
    if opponent.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot duel yourself")
    
    # Get questions
    query = db.query(Question).filter(Question.subject.ilike(data.subject))
    if data.topic:
        query = query.filter(Question.topic.ilike(data.topic))
    
    questions = query.all()
    if len(questions) < data.count:
        raise HTTPException(status_code=400, detail="Not enough questions available")
    
    # Select random questions
    selected_questions = random.sample(questions, data.count)
    
    # Create duel
    duel = Duel(
        challenger_id=current_user.id,
        opponent_id=data.opponent_id,
        subject=data.subject,
        topic=data.topic,
        question_ids=[q.id for q in selected_questions],
        status="pending",
        time_limit=data.time_limit,
        challenger_score=0,
        opponent_score=0
    )
    db.add(duel)
    db.commit()
    db.refresh(duel)
    
    return {
        "duel_id": duel.id,
        "message": "Duel created successfully",
        "challenger": current_user.username,
        "opponent": opponent.username,
        "subject": duel.subject,
        "questions_count": len(selected_questions),
        "time_limit": duel.time_limit,
        "status": duel.status
    }


@router.post("/join")
async def join_duel(
    data: DuelJoin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a pending duel"""
    duel = db.query(Duel).filter(Duel.id == data.duel_id).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    if duel.status != "pending":
        raise HTTPException(status_code=400, detail="Duel already started or completed")
    
    if duel.challenger_id == current_user.id:
        raise HTTPException(status_code=400, detail="You already created this duel")
    
    if duel.opponent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the opponent")
    
    # Get questions
    questions = db.query(Question).filter(Question.id.in_(duel.question_ids)).all()
    
    # Format questions for response
    questions_data = [
        {
            "id": q.id,
            "question": q.question,
            "options": q.options,
            "type": q.type,
            "difficulty": q.difficulty.value if hasattr(q.difficulty, 'value') else q.difficulty,
            "topic": q.topic,
            "subject": q.subject
        }
        for q in questions
    ]
    
    duel.status = "active"
    db.commit()
    
    return {
        "duel_id": duel.id,
        "subject": duel.subject,
        "topic": duel.topic,
        "questions": questions_data,
        "time_limit": duel.time_limit,
        "challenger": db.query(User).filter(User.id == duel.challenger_id).first().username,
        "opponent": db.query(User).filter(User.id == duel.opponent_id).first().username
    }


@router.post("/submit")
async def submit_duel(
    data: DuelSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit answers for a duel"""
    duel = db.query(Duel).filter(Duel.id == data.duel_id).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    if duel.status != "active":
        raise HTTPException(status_code=400, detail="Duel not active")
    
    # Determine if user is challenger or opponent
    is_challenger = duel.challenger_id == current_user.id
    is_opponent = duel.opponent_id == current_user.id
    
    if not is_challenger and not is_opponent:
        raise HTTPException(status_code=403, detail="You are not part of this duel")
    
    # Get questions for scoring
    questions = db.query(Question).filter(Question.id.in_(duel.question_ids)).all()
    question_map = {q.id: q for q in questions}
    
    # Calculate score
    correct = 0
    for q_id in duel.question_ids:
        user_answer = data.answers.get(q_id)
        q = question_map.get(q_id)
        if q and user_answer == q.answer:
            correct += 1
    
    # Store answers and score
    if is_challenger:
        duel.challenger_answers = data.answers
        duel.challenger_score = correct
    else:
        duel.opponent_answers = data.answers
        duel.opponent_score = correct
    
    # Check if both players have submitted
    if duel.challenger_answers and duel.opponent_answers:
        duel.status = "completed"
        duel.completed_at = datetime.utcnow()
        
        # Determine winner
        if duel.challenger_score > duel.opponent_score:
            duel.winner_id = duel.challenger_id
        elif duel.opponent_score > duel.challenger_score:
            duel.winner_id = duel.opponent_id
        else:
            duel.winner_id = None  # Draw
        
        # Award XP (simplified)
        if duel.winner_id:
            winner_stats = db.query(UserStats).filter(UserStats.user_id == duel.winner_id).first()
            if winner_stats:
                winner_stats.xp += 50
                winner_stats.level = min(winner_stats.xp // 100 + 1, 20)
    
    db.commit()
    
    # Return current submission status
    return {
        "duel_id": duel.id,
        "submitted": True,
        "your_score": correct,
        "status": duel.status,
        "challenger_score": duel.challenger_score if duel.challenger_answers else None,
        "opponent_score": duel.opponent_score if duel.opponent_answers else None,
        "winner": db.query(User).filter(User.id == duel.winner_id).first().username if duel.winner_id else None
    }


@router.get("/history")
async def get_duel_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100)
):
    """Get user's duel history"""
    duels = db.query(Duel).filter(
        (Duel.challenger_id == current_user.id) | (Duel.opponent_id == current_user.id),
        Duel.status == "completed"
    ).order_by(Duel.completed_at.desc()).limit(limit).all()
    
    history = []
    for duel in duels:
        challenger = db.query(User).filter(User.id == duel.challenger_id).first()
        opponent = db.query(User).filter(User.id == duel.opponent_id).first()
        
        history.append({
            "id": duel.id,
            "challenger": challenger.username,
            "opponent": opponent.username,
            "challenger_score": duel.challenger_score,
            "opponent_score": duel.opponent_score,
            "winner": challenger.username if duel.winner_id == duel.challenger_id else opponent.username if duel.winner_id else "Draw",
            "subject": duel.subject,
            "completed_at": duel.completed_at
        })
    
    return history


@router.get("/{duel_id}")
async def get_duel_status(
    duel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get duel status"""
    duel = db.query(Duel).filter(Duel.id == duel_id).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    challenger = db.query(User).filter(User.id == duel.challenger_id).first()
    opponent = db.query(User).filter(User.id == duel.opponent_id).first()
    
    return {
        "id": duel.id,
        "challenger": challenger.username,
        "opponent": opponent.username if opponent else "Waiting for opponent",
        "subject": duel.subject,
        "topic": duel.topic,
        "status": duel.status,
        "challenger_score": duel.challenger_score,
        "opponent_score": duel.opponent_score,
        "winner": challenger.username if duel.winner_id == duel.challenger_id else opponent.username if duel.winner_id else "Draw",
        "created_at": duel.created_at,
        "completed_at": duel.completed_at
    }