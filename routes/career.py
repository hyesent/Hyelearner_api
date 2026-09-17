# ============================================================
# HYELEARNER: ROUTES — CAREER
# Built by Hyesent.dev
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import User, CareerCheck
from dependencies import get_current_user, call_ai_with_limit
from services.ai import ai_service
from schemas import CareerHistoryItem, CareerHistoryResponse, CareerCheckResponse

router = APIRouter()


# ============================================================
# CHECK ADMISSION
# ============================================================

@router.post("/check")
async def check_admission(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    university = (data.get("university") or "").strip()
    country = data.get("country", "")
    course = (data.get("course") or "").strip()
    score = data.get("score")
    score_type = data.get("score_type", "percentage")
    subjects = data.get("subjects", [])

    if not university:
        raise HTTPException(400, "University name required")
    if not course:
        raise HTTPException(400, "Course name required")
    if score is None:
        raise HTTPException(400, "Score required")

    if not score_type or score_type == "percentage":
        score_type = detect_score_type(country)

    # Call AI under limit
    result = await call_ai_with_limit(
        db,
        current_user.id,
        ai_service.course_finder_check,
        university=university,
        country=country,
        course=course,
        score=score,
        score_type=score_type,
        subjects=subjects,
    )

    # Persist
    try:
        db.add(CareerCheck(
            user_id=current_user.id,
            university=university,
            country=country,
            course=course,
            score=score,
            score_type=score_type,
            subjects=subjects,
            status=result.get("status"),
            chance_percentage=(result.get("result") or {}).get("chance_percentage"),
            result_json=result,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ Failed to save career check: {e}")

    return result


# ============================================================
# HISTORY
# ============================================================

@router.get("/history", response_model=CareerHistoryResponse)
def get_history(
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(CareerCheck)
        .filter_by(user_id=current_user.id)
        .order_by(CareerCheck.created_at.desc())
        .limit(limit)
        .all()
    )

    items = [
        CareerHistoryItem(
            id=r.id,
            university=r.university,
            course=r.course,
            status=r.status,
            chance_percentage=r.chance_percentage,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return {"checks": items}


# ============================================================
# GET SINGLE CHECK
# ============================================================

@router.get("/check/{check_id}", response_model=CareerCheckResponse)
def get_check(
    check_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(CareerCheck)
        .filter_by(id=check_id, user_id=current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Check not found")
    return row


# ============================================================
# HELPERS
# ============================================================

def detect_score_type(country: str) -> str:
    c = (country or "").lower()
    if any(x in c for x in ["nigeria", "ghana", "kenya"]):
        return "jamb"
    if c in ["usa", "united states", "canada"]:
        return "sat"
    if c in ["uk", "united kingdom"]:
        return "a-level"
    return "percentage"
