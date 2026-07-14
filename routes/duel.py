from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import random
import secrets

from database import get_db
from models import User, Duel, Question, UserStats
from schemas import DuelCreate, DuelJoin, DuelSubmit, DuelResponse
from dependencies import get_current_user

router = APIRouter()


def get_active_users(db: Session, minutes: int = 5):
    """Get users active in the last X minutes"""
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    active_users = db.query(User).filter(
        User.last_login >= cutoff,
        User.is_active == True
    ).all()
    return active_users


@router.post("/create")
async def create_duel(
    data: DuelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a duel with questions from frontend.
    - Public: Appears in lobby for all users
    - Private: Only accessible via code
    """
    
    # ✅ Use questions from frontend
    if not data.questions or len(data.questions) == 0:
        raise HTTPException(
            status_code=400,
            detail="No questions provided. Please load questions from frontend."
        )
    
    if len(data.questions) < data.count:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough questions. Need {data.count}, got {len(data.questions)}"
        )
    
    # Select random questions from the ones provided
    selected_questions = random.sample(data.questions, data.count)
    question_ids = [q.get('id', f"q_{i}") for i, q in enumerate(selected_questions)]
    
    # Generate unique code
    code = secrets.token_hex(3).upper()
    
    # Get active users count
    active_users = get_active_users(db)
    active_count = len(active_users)
    
    # ✅ Create duel with questions from frontend
    duel = Duel(
        challenger_id=current_user.id,
        opponent_id=None,
        code=code,
        subject=data.subject,
        topic=data.topic,
        question_ids=question_ids,
        questions_data=selected_questions,  # Store full questions
        status="waiting",  # ✅ KEEP 'waiting' (you added it to enum)
        is_public=data.is_public,
        time_limit=data.time_limit,
        challenger_score=0,
        opponent_score=0
    )
    db.add(duel)
    db.commit()
    db.refresh(duel)
    
    active_users_list = [
        {
            "id": u.id,
            "username": u.username,
            "avatar_url": u.avatar_url
        }
        for u in active_users
    ]
    
    return {
        "duel_id": duel.id,
        "code": code,
        "is_public": duel.is_public,
        "message": "Duel created!",
        "challenger": current_user.username,
        "subject": duel.subject,
        "questions_count": len(selected_questions),
        "time_limit": duel.time_limit,
        "active_users": {
            "count": active_count,
            "users": active_users_list
        }
    }


@router.get("/public")
async def get_public_duels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all public duels waiting for opponents."""
    duels = db.query(Duel).filter(
        Duel.is_public == True,
        Duel.status == "waiting",  # ✅ KEEP 'waiting'
        Duel.challenger_id != current_user.id
    ).order_by(Duel.created_at.desc()).all()
    
    active_users = get_active_users(db)
    active_count = len(active_users)
    
    lobby = []
    for duel in duels:
        challenger = db.query(User).filter(User.id == duel.challenger_id).first()
        time_ago = (datetime.utcnow() - duel.created_at).seconds // 60
        
        lobby.append({
            "duel_id": duel.id,
            "code": duel.code,
            "challenger": challenger.username,
            "subject": duel.subject,
            "topic": duel.topic,
            "question_count": len(duel.question_ids),
            "time_limit": duel.time_limit,
            "created_ago": f"{time_ago}m ago",
            "status": duel.status
        })
    
    return {
        "active_users": active_count,
        "duels": lobby,
        "total_public_duels": len(lobby)
    }


@router.get("/active-users")
async def get_active_users_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all currently active users"""
    active_users = get_active_users(db)
    
    return {
        "count": len(active_users),
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "avatar_url": u.avatar_url,
                "last_login": u.last_login.isoformat() if u.last_login else None
            }
            for u in active_users
        ]
    }


@router.post("/join")
async def join_duel(
    data: DuelJoin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a duel using the code."""
    if not data.code:
        raise HTTPException(status_code=400, detail="Code required to join")
    
    duel = db.query(Duel).filter(Duel.code == data.code).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Invalid code. Duel not found.")
    
    if duel.status == "completed":
        raise HTTPException(status_code=400, detail="Duel already completed")
    
    if duel.status == "active":
        raise HTTPException(status_code=400, detail="Duel already has an opponent")
    
    if duel.challenger_id == current_user.id:
        raise HTTPException(status_code=400, detail="You created this duel. Wait for opponent.")
    
    # Set opponent
    duel.opponent_id = current_user.id
    duel.status = "active"
    db.commit()
    
    # ✅ Get questions from duel
    questions_data = duel.questions_data or []
    
    return {
        "duel_id": duel.id,
        "code": duel.code,
        "subject": duel.subject,
        "topic": duel.topic,
        "questions": questions_data,
        "time_limit": duel.time_limit,
        "challenger": db.query(User).filter(User.id == duel.challenger_id).first().username,
        "opponent": current_user.username,
        "status": duel.status
    }


@router.post("/join-public/{duel_id}")
async def join_public_duel(
    duel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a public duel directly from the lobby."""
    duel = db.query(Duel).filter(
        Duel.id == duel_id,
        Duel.is_public == True,
        Duel.status == "waiting"  # ✅ KEEP 'waiting'
    ).first()
    
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found or already taken")
    
    if duel.challenger_id == current_user.id:
        raise HTTPException(status_code=400, detail="You created this duel")
    
    duel.opponent_id = current_user.id
    duel.status = "active"
    db.commit()
    
    questions_data = duel.questions_data or []
    
    return {
        "duel_id": duel.id,
        "subject": duel.subject,
        "topic": duel.topic,
        "questions": questions_data,
        "time_limit": duel.time_limit,
        "challenger": db.query(User).filter(User.id == duel.challenger_id).first().username,
        "opponent": current_user.username,
        "status": duel.status
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
    
    is_challenger = duel.challenger_id == current_user.id
    is_opponent = duel.opponent_id == current_user.id
    
    if not is_challenger and not is_opponent:
        raise HTTPException(status_code=403, detail="You are not part of this duel")
    
    # ✅ Use questions from duel
    questions = duel.questions_data or []
    question_map = {q.get('id'): q for q in questions}
    
    correct = 0
    for q in questions:
        q_id = q.get('id')
        user_answer = data.answers.get(q_id)
        if user_answer and user_answer == q.get('answer'):
            correct += 1
    
    if is_challenger:
        duel.challenger_answers = data.answers
        duel.challenger_score = correct
    else:
        duel.opponent_answers = data.answers
        duel.opponent_score = correct
    
    db.commit()
    
    if duel.challenger_answers and duel.opponent_answers:
        duel.status = "completed"
        duel.completed_at = datetime.utcnow()
        
        if duel.challenger_score > duel.opponent_score:
            duel.winner_id = duel.challenger_id
        elif duel.opponent_score > duel.challenger_score:
            duel.winner_id = duel.opponent_id
        else:
            duel.winner_id = None
        
        if duel.winner_id:
            winner_stats = db.query(UserStats).filter(UserStats.user_id == duel.winner_id).first()
            if winner_stats:
                winner_stats.xp += 50
                winner_stats.level = min(winner_stats.xp // 100 + 1, 20)
        
        db.commit()
        
        winner_name = db.query(User).filter(User.id == duel.winner_id).first().username if duel.winner_id else "Draw"
        
        return {
            "duel_id": duel.id,
            "submitted": True,
            "your_score": correct,
            "status": "completed",
            "challenger_score": duel.challenger_score,
            "opponent_score": duel.opponent_score,
            "winner": winner_name,
            "completed_at": duel.completed_at
        }
    
    return {
        "duel_id": duel.id,
        "submitted": True,
        "your_score": correct,
        "status": duel.status,
        "challenger_score": duel.challenger_score if duel.challenger_answers else None,
        "opponent_score": duel.opponent_score if duel.opponent_answers else None,
        "winner": None
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
            "code": duel.code,
            "challenger": challenger.username,
            "opponent": opponent.username if opponent else "Unknown",
            "challenger_score": duel.challenger_score,
            "opponent_score": duel.opponent_score,
            "winner": challenger.username if duel.winner_id == duel.challenger_id else opponent.username if duel.winner_id else "Draw",
            "subject": duel.subject,
            "is_public": duel.is_public,
            "completed_at": duel.completed_at
        })
    
    return history


@router.get("/{duel_id}")
async def get_duel_status(
    duel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get duel status by ID"""
    duel = db.query(Duel).filter(Duel.id == duel_id).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    challenger = db.query(User).filter(User.id == duel.challenger_id).first()
    opponent = db.query(User).filter(User.id == duel.opponent_id).first()
    
    return {
        "id": duel.id,
        "code": duel.code,
        "challenger": challenger.username,
        "opponent": opponent.username if opponent else "Waiting for opponent",
        "subject": duel.subject,
        "topic": duel.topic,
        "status": duel.status,
        "is_public": duel.is_public,
        "challenger_score": duel.challenger_score,
        "opponent_score": duel.opponent_score,
        "winner": challenger.username if duel.winner_id == duel.challenger_id else opponent.username if duel.winner_id else "Draw",
        "created_at": duel.created_at,
        "completed_at": duel.completed_at
    }


@router.get("/code/{code}")
async def get_duel_by_code(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get duel by code (before joining)"""
    duel = db.query(Duel).filter(Duel.code == code).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Invalid code. Duel not found.")
    
    challenger = db.query(User).filter(User.id == duel.challenger_id).first()
    
    return {
        "duel_id": duel.id,
        "code": duel.code,
        "challenger": challenger.username,
        "subject": duel.subject,
        "topic": duel.topic,
        "status": duel.status,
        "is_public": duel.is_public,
        "questions_count": len(duel.question_ids),
        "time_limit": duel.time_limit,
        "created_at": duel.created_at
    }
