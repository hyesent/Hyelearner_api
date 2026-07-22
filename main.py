from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from database import engine, Base
from config import settings
from dependencies import get_current_user
from models import User

# Import routers
from routes import (
    auth, user, questions, sessions, mistakes, bookmarks,
    lessons, heatmap, gamification, ai, subscriptions,
    parent, duel, leaderboard, referrals, admin, study_plan, career,
    hyetutor  # ✅ ADD THIS
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: Cleanup


app = FastAPI(
    title="Hyelearner Foundation API",
    description="API for Hyelearner Foundation - SSCE/JAMB/WAEC/NECO Exam Prep",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "hyelearner-foundation"}

@app.get("/")
async def root():
    return {
        "message": "Hyelearner Foundation API",
        "version": "1.0.0",
        "status": "running"
    }

# ============================================================
# PING ENDPOINTS
# ============================================================

@app.get("/ping")
async def ping():
    """Public ping - check if API is alive"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/ping/auth")
async def ping_auth(current_user: User = Depends(get_current_user)):
    """Authenticated ping - checks if user is logged in"""
    return {
        "status": "ok",
        "authenticated": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# ============================================================
# SHARED ROUTES
# ============================================================

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])

# ============================================================
# FOUNDATION ROUTES
# ============================================================

app.include_router(questions.router, prefix="/questions", tags=["Questions"])
app.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
app.include_router(mistakes.router, prefix="/mistakes", tags=["Mistakes"])
app.include_router(bookmarks.router, prefix="/bookmarks", tags=["Bookmarks"])
app.include_router(lessons.router, prefix="/lessons", tags=["Lessons"])
app.include_router(heatmap.router, prefix="/heatmap", tags=["Heatmap"])
app.include_router(gamification.router, prefix="/gamification", tags=["Gamification"])
app.include_router(parent.router, prefix="/parent", tags=["Parent"])
app.include_router(duel.router, prefix="/duel", tags=["Duel"])
app.include_router(leaderboard.router, prefix="/leaderboard", tags=["Leaderboard"])
app.include_router(referrals.router, prefix="/referral", tags=["Referrals"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(study_plan.router, prefix="/study-plan", tags=["Study Plan"]) 
app.include_router(career.router, prefix="/career", tags=["Career"])

# ============================================================
# HYETUTOR ROUTES
# ============================================================

app.include_router(hyetutor.router, prefix="/hyetutor", tags=["HyeTutor"])  # ✅ ADD THIS


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
