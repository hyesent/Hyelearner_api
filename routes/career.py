from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import httpx

from database import get_db
from models import User
from dependencies import get_current_user
from services.ai import ai_service

router = APIRouter()

UNIVERSITIES_API = "https://universities.hipolabs.com/search"


# ============================================================
# SEARCH UNIVERSITIES (External API)
# ============================================================

@router.get("/search-universities")
async def search_universities(
    query: str = Query(..., min_length=2),
    current_user: User = Depends(get_current_user)
):
    """
    Search universities worldwide.
    User types → API returns results → User selects one.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                UNIVERSITIES_API,
                params={"name": query}
            )
            data = response.json()
        
        results = []
        for uni in data[:20]:
            results.append({
                "name": uni.get("name", ""),
                "country": uni.get("country", ""),
                "state": uni.get("state-province"),
                "web": uni.get("web_pages", [""])[0] if uni.get("web_pages") else "",
                "domains": uni.get("domains", [])
            })
        
        return {
            "query": query,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching universities: {str(e)}")


# ============================================================
# CHECK ADMISSION ELIGIBILITY (AI-Powered)
# ============================================================

@router.post("/check")
async def check_admission(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user qualifies for a course at ANY university in the world.
    Uses AI (Gemini/Groq) to determine admission requirements.
    """
    university = data.get("university", "").strip()
    country = data.get("country", "")
    course = data.get("course", "").strip()
    score = data.get("score")
    score_type = data.get("score_type", "percentage")
    subjects = data.get("subjects", [])
    
    # Validation
    if not university:
        raise HTTPException(status_code=400, detail="University name required")
    if not course:
        raise HTTPException(status_code=400, detail="Course name required")
    if not score:
        raise HTTPException(status_code=400, detail="Score required")
    
    # Auto-detect score type based on country
    if not score_type or score_type == "percentage":
        score_type = detect_score_type(country)
    
    # Call AI service
    result = await ai_service.check_admission_eligibility(
        university=university,
        country=country,
        course=course,
        score=score,
        score_type=score_type,
        subjects=subjects
    )
    
    return result


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def detect_score_type(country: str) -> str:
    """Detect score type based on country"""
    country_lower = country.lower()
    
    if any(c in country_lower for c in ["nigeria", "ghana", "kenya"]):
        return "jamb"
    elif country_lower in ["usa", "united states", "canada"]:
        return "sat"
    elif country_lower in ["uk", "united kingdom"]:
        return "a-level"
    else:
        return "percentage"
