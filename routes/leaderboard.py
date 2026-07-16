from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, case
from typing import Optional
from datetime import datetime, timedelta

from database import get_db
from models import User, UserStats, Duel
from dependencies import get_current_user

router = APIRouter()


# ============================================================
# GLOBAL LEADERBOARD
# ============================================================

@router.get("/global")
async def get_global_duel_leaderboard(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Global duel leaderboard - ranked by duel performance"""
    
    results = db.query(
        User.id,
        User.username,
        User.avatar_url,
        User.school,
        UserStats.xp,
        UserStats.level,
        # ✅ REMOVED: current_streak, longest_streak
        func.count(Duel.id).label("total_duels"),
        func.sum(
            case(
                (Duel.winner_id == User.id, 1),
                else_=0
            )
        ).label("wins"),
        func.sum(
            case(
                (and_(Duel.winner_id != User.id, Duel.winner_id.isnot(None)), 1),
                else_=0
            )
        ).label("losses"),
        func.sum(
            case(
                (Duel.winner_id.is_(None), 1),
                else_=0
            )
        ).label("draws"),
        func.coalesce(
            func.sum(
                case(
                    (Duel.winner_id == User.id, 1),
                    else_=0
                )
            ) * 100.0 / 
            func.nullif(func.count(Duel.id), 0),
            0
        ).label("win_rate")
    ).join(
        UserStats, User.id == UserStats.user_id, isouter=True
    ).outerjoin(
        Duel,
        and_(
            Duel.status == "completed",
            (Duel.challenger_id == User.id) | (Duel.opponent_id == User.id)
        )
    ).filter(
        User.is_active == True
    ).group_by(
        User.id, UserStats.id
    ).order_by(
        desc("wins"),
        desc("win_rate"),
        desc(UserStats.xp)
        # ✅ REMOVED: desc(UserStats.current_streak)
    ).offset(offset).limit(limit).all()
    
    leaderboard = []
    for idx, row in enumerate(results, start=offset + 1):
        total_duels = row.total_duels or 0
        wins = row.wins or 0
        losses = row.losses or 0
        draws = row.draws or 0
        win_rate = round(row.win_rate or 0, 1)
        
        leaderboard.append({
            "rank": idx,
            "user_id": row.id,
            "username": row.username,
            "avatar": row.avatar_url,
            "school": row.school or "Unknown",
            "xp": row.xp or 0,
            "level": row.level or 1,
            "streak": 0,  # ✅ Default to 0 if no streak field
            "total_duels": total_duels,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate": win_rate
        })
    
    total_count = db.query(User).filter(User.is_active == True).count()
    
    return {
        "leaderboard": leaderboard,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "next": offset + limit < total_count
    }


# ============================================================
# SCHOOL LEADERBOARD
# ============================================================

@router.get("/school")
async def get_school_duel_leaderboard(
    db: Session = Depends(get_db),
    school: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get duel leaderboard filtered by school"""
    
    if not school:
        school = current_user.school
        if not school:
            raise HTTPException(400, "No school specified and user has no school set")
    
    results = db.query(
        User.id,
        User.username,
        User.avatar_url,
        User.school,
        UserStats.xp,
        UserStats.level,
        # ✅ REMOVED: current_streak
        func.count(Duel.id).label("total_duels"),
        func.sum(
            case(
                (Duel.winner_id == User.id, 1),
                else_=0
            )
        ).label("wins"),
        func.coalesce(
            func.sum(
                case(
                    (Duel.winner_id == User.id, 1),
                    else_=0
                )
            ) * 100.0 / 
            func.nullif(func.count(Duel.id), 0),
            0
        ).label("win_rate")
    ).join(
        UserStats, User.id == UserStats.user_id, isouter=True
    ).outerjoin(
        Duel,
        and_(
            Duel.status == "completed",
            (Duel.challenger_id == User.id) | (Duel.opponent_id == User.id)
        )
    ).filter(
        User.is_active == True,
        User.school.ilike(f"%{school}%")
    ).group_by(
        User.id, UserStats.id
    ).order_by(
        desc("wins"),
        desc("win_rate"),
        desc(UserStats.xp)
    ).limit(limit).all()
    
    leaderboard = []
    for idx, row in enumerate(results, start=1):
        total_duels = row.total_duels or 0
        wins = row.wins or 0
        win_rate = round(row.win_rate or 0, 1)
        
        leaderboard.append({
            "rank": idx,
            "user_id": row.id,
            "username": row.username,
            "avatar": row.avatar_url,
            "school": row.school or "Unknown",
            "xp": row.xp or 0,
            "level": row.level or 1,
            "streak": 0,  # ✅ Default to 0
            "total_duels": total_duels,
            "wins": wins,
            "win_rate": win_rate
        })
    
    return leaderboard


# ============================================================
# FRIENDS LEADERBOARD
# ============================================================

@router.get("/friends")
async def get_friends_duel_leaderboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=50)
):
    """Get duel leaderboard for user's friends/connections"""
    
    friends = db.query(User).filter(
        User.is_active == True,
        User.school == current_user.school,
        User.id != current_user.id
    ).limit(limit).all()
    
    friend_ids = [f.id for f in friends]
    friend_ids.append(current_user.id)
    
    results = db.query(
        User.id,
        User.username,
        User.avatar_url,
        User.school,
        UserStats.xp,
        UserStats.level,
        # ✅ REMOVED: current_streak
        func.count(Duel.id).label("total_duels"),
        func.sum(
            case(
                (Duel.winner_id == User.id, 1),
                else_=0
            )
        ).label("wins"),
        func.coalesce(
            func.sum(
                case(
                    (Duel.winner_id == User.id, 1),
                    else_=0
                )
            ) * 100.0 / 
            func.nullif(func.count(Duel.id), 0),
            0
        ).label("win_rate")
    ).join(
        UserStats, User.id == UserStats.user_id, isouter=True
    ).outerjoin(
        Duel,
        and_(
            Duel.status == "completed",
            (Duel.challenger_id == User.id) | (Duel.opponent_id == User.id)
        )
    ).filter(
        User.id.in_(friend_ids)
    ).group_by(
        User.id, UserStats.id
    ).order_by(
        desc("wins"),
        desc("win_rate")
    ).all()
    
    leaderboard = []
    for idx, row in enumerate(results, start=1):
        is_current = row.id == current_user.id
        total_duels = row.total_duels or 0
        wins = row.wins or 0
        win_rate = round(row.win_rate or 0, 1)
        
        leaderboard.append({
            "rank": idx,
            "user_id": row.id,
            "username": row.username,
            "avatar": row.avatar_url,
            "school": row.school or "Unknown",
            "xp": row.xp or 0,
            "level": row.level or 1,
            "streak": 0,  # ✅ Default to 0
            "total_duels": total_duels,
            "wins": wins,
            "win_rate": win_rate,
            "is_current_user": is_current
        })
    
    return leaderboard


# ============================================================
# USER RANK
# ============================================================

@router.get("/user/{user_id}")
async def get_user_duel_rank(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific user's duel rank and stats"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    
    # Calculate duel stats
    duels = db.query(Duel).filter(
        (Duel.challenger_id == user_id) | (Duel.opponent_id == user_id),
        Duel.status == "completed"
    ).all()
    
    total_duels = len(duels)
    wins = sum(1 for d in duels if d.winner_id == user_id)
    draws = sum(1 for d in duels if d.winner_id is None)
    losses = total_duels - wins - draws
    win_rate = round((wins / total_duels * 100) if total_duels > 0 else 0, 1)
    
    # Calculate rank (by wins)
    rank = db.query(UserStats).filter(
        UserStats.duel_wins > (stats.duel_wins if stats else 0)
    ).count() + 1 if stats else 1
    
    total_users = db.query(User).filter(User.is_active == True).count()
    
    return {
        "user_id": user.id,
        "username": user.username,
        "name": user.username,
        "avatar": user.avatar_url,
        "school": user.school or "Unknown",
        "rank": rank,
        "total_users": total_users,
        "top_percent": round((1 - rank / total_users) * 100, 1) if total_users > 0 else 0,
        "xp": stats.xp if stats else 0,
        "level": stats.level if stats else 1,
        "streak": 0,  # ✅ Default to 0
        "total_duels": total_duels,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": win_rate
    }


# ============================================================
# WEEKLY LEADERBOARD
# ============================================================

@router.get("/weekly")
async def get_weekly_duel_leaderboard(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=50)
):
    """Get weekly duel leaders (most wins in last 7 days)"""
    
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    weekly_results = db.query(
        User.id,
        User.username,
        User.avatar_url,
        User.school,
        func.count(Duel.id).label("weekly_duels"),
        func.sum(
            case(
                (Duel.winner_id == User.id, 1),
                else_=0
            )
        ).label("weekly_wins"),
        func.sum(
            case(
                (Duel.winner_id == User.id, 50),
                (and_(Duel.winner_id.isnot(None), Duel.winner_id != User.id), 15),
                else_=25
            )
        ).label("weekly_xp")
    ).join(
        User, Duel.challenger_id == User.id, isouter=True
    ).filter(
        Duel.status == "completed",
        Duel.completed_at >= week_ago,
        User.is_active == True
    ).group_by(
        User.id
    ).order_by(
        desc("weekly_wins"),
        desc("weekly_xp")
    ).limit(limit).all()
    
    results = []
    for idx, row in enumerate(weekly_results, start=1):
        results.append({
            "rank": idx,
            "user_id": row.id,
            "username": row.username,
            "name": row.username,
            "avatar": row.avatar_url,
            "school": row.school or "Unknown",
            "weekly_duels": row.weekly_duels or 0,
            "weekly_wins": row.weekly_wins or 0,
            "weekly_xp": row.weekly_xp or 0
        })
    
    return results


# ============================================================
# SUBJECT LEADERBOARD
# ============================================================

@router.get("/subject")
async def get_subject_duel_leaderboard(
    subject: str,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100)
):
    """Get duel leaderboard for a specific subject"""
    
    results = db.query(
        User.id,
        User.username,
        User.avatar_url,
        User.school,
        UserStats.xp,
        UserStats.level,
        func.count(Duel.id).label("total_duels"),
        func.sum(
            case(
                (Duel.winner_id == User.id, 1),
                else_=0
            )
        ).label("wins"),
        func.coalesce(
            func.sum(
                case(
                    (Duel.winner_id == User.id, 1),
                    else_=0
                )
            ) * 100.0 / 
            func.nullif(func.count(Duel.id), 0),
            0
        ).label("win_rate"),
        func.coalesce(
            func.avg(
                case(
                    (Duel.challenger_id == User.id, Duel.challenger_score),
                    (Duel.opponent_id == User.id, Duel.opponent_score),
                    else_=0
                )
            ),
            0
        ).label("avg_score")
    ).join(
        UserStats, User.id == UserStats.user_id, isouter=True
    ).outerjoin(
        Duel,
        and_(
            Duel.status == "completed",
            Duel.subject.ilike(f"%{subject}%"),
            (Duel.challenger_id == User.id) | (Duel.opponent_id == User.id)
        )
    ).filter(
        User.is_active == True
    ).group_by(
        User.id, UserStats.id
    ).having(
        func.count(Duel.id) > 0
    ).order_by(
        desc("wins"),
        desc("win_rate")
    ).limit(limit).all()
    
    leaderboard = []
    for idx, row in enumerate(results, start=1):
        total_duels = row.total_duels or 0
        wins = row.wins or 0
        win_rate = round(row.win_rate or 0, 1)
        avg_score = round(row.avg_score or 0, 1)
        
        leaderboard.append({
            "rank": idx,
            "user_id": row.id,
            "username": row.username,
            "name": row.username,
            "avatar": row.avatar_url,
            "school": row.school or "Unknown",
            "xp": row.xp or 0,
            "level": row.level or 1,
            "streak": 0,  # ✅ Default to 0
            "total_duels": total_duels,
            "wins": wins,
            "win_rate": win_rate,
            "avg_score": avg_score
        })
    
    return leaderboard


# ============================================================
# ✅ MAIN ENDPOINT - MATCHES FRONTEND EXPECTATIONS
# ============================================================

@router.get("")
async def get_duel_leaderboard(
    filter_type: str = Query("global", regex="^(global|school|friends|subject)$"),
    subject: Optional[str] = None,
    school: Optional[str] = None,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    Combined duel leaderboard endpoint - MATCHES FRONTEND EXPECTATIONS
    """
    
    if filter_type == "global":
        data = await get_global_duel_leaderboard(db, limit, 0)
        return {
            "rankings": [
                {
                    "rank": item["rank"],
                    "name": item["username"],
                    "xp": item["xp"],
                    "level": item["level"],
                    "streak": 0,  # ✅ Default to 0
                    "school": item["school"] or "Unknown"
                }
                for item in data["leaderboard"]
            ],
            "totalUsers": data["total"],
            "filter": "global"
        }
    
    elif filter_type == "school":
        data = await get_school_duel_leaderboard(db, school, limit, current_user)
        return {
            "rankings": [
                {
                    "rank": item["rank"],
                    "name": item["username"],
                    "xp": item["xp"],
                    "level": item["level"],
                    "streak": 0,  # ✅ Default to 0
                    "school": item["school"] or "Unknown"
                }
                for item in data
            ],
            "totalUsers": len(data),
            "filter": "school"
        }
    
    elif filter_type == "friends":
        data = await get_friends_duel_leaderboard(current_user, db, limit)
        return {
            "rankings": [
                {
                    "rank": item["rank"],
                    "name": item["username"],
                    "xp": item["xp"],
                    "level": item["level"],
                    "streak": 0,  # ✅ Default to 0
                    "school": item["school"] or "Unknown",
                    "is_current_user": item.get("is_current_user", False)
                }
                for item in data
            ],
            "totalUsers": len(data),
            "filter": "friends"
        }
    
    elif filter_type == "subject":
        if not subject:
            raise HTTPException(400, "Subject is required for subject filter")
        data = await get_subject_duel_leaderboard(subject, db, limit)
        return {
            "rankings": [
                {
                    "rank": item["rank"],
                    "name": item["username"],
                    "xp": item["xp"],
                    "level": item["level"],
                    "streak": 0,  # ✅ Default to 0
                    "school": item["school"] or "Unknown",
                    "avg_score": item.get("avg_score", 0)
                }
                for item in data
            ],
            "totalUsers": len(data),
            "filter": "subject",
            "subject": subject
        }
    
    return {"error": "Invalid filter"}
