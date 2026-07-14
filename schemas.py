from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================
# ENUMS (for validation)
# ============================================================

class UserRole(str, Enum):
    STUDENT = "student"
    PARENT = "parent"
    ADMIN = "admin"

class UserTier(str, Enum):
    FOUNDATION = "foundation"
    CAMPUS = "campus"
    CAREER = "career"
    PRO = "pro"
    PRO_CAMPUS = "pro_campus"

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class DuelStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ============================================================
# USER SCHEMAS (MUST COME BEFORE TokenResponse)
# ============================================================

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str]
    role: str
    tier: str
    school: Optional[str]
    country: Optional[str]
    exam: Optional[str]
    bio: Optional[str]
    goal: Optional[str]
    subscription_expires: Optional[datetime]
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    school: Optional[str] = None
    country: Optional[str] = None
    exam: Optional[str] = None
    bio: Optional[str] = None
    goal: Optional[str] = None


# ============================================================
# AUTH SCHEMAS
# ============================================================

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    school: Optional[str] = None
    country: Optional[str] = None
    exam: Optional[str] = None
    referral_code: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


# ============================================================
# USER SETTINGS SCHEMAS
# ============================================================

class UserSettingsResponse(BaseModel):
    dark_mode: bool
    notifications: bool
    study_reminders: bool
    reminder_time: str
    sound_effects: bool
    auto_sync: bool
    ai_daily_limit: int
    ai_used_today: int
    ai_used_month: int

    model_config = ConfigDict(from_attributes=True)

class UserSettingsUpdate(BaseModel):
    dark_mode: Optional[bool] = None
    notifications: Optional[bool] = None
    study_reminders: Optional[bool] = None
    reminder_time: Optional[str] = None
    sound_effects: Optional[bool] = None
    auto_sync: Optional[bool] = None


# ============================================================
# QUESTION SCHEMAS
# ============================================================

class QuestionResponse(BaseModel):
    id: str
    type: str
    question: str
    options: List[str]
    answer: str
    explanation: Optional[str]
    difficulty: str
    topic: str
    subject: str
    platform: str
    year: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class QuestionListResponse(BaseModel):
    items: List[QuestionResponse]
    total: int
    limit: int
    offset: int


# ============================================================
# SESSION SCHEMAS
# ============================================================

class SessionStart(BaseModel):
    subject: str
    topic: Optional[str] = None
    count: int = Field(30, ge=1, le=50)
    difficulty: Optional[str] = None
    is_timed: bool = False
    time_limit: Optional[int] = Field(600, ge=60, le=3600)

class SessionQuestionResponse(BaseModel):
    id: str
    question: str
    options: List[str]
    type: str
    difficulty: str
    topic: str
    subject: str

class SessionStartResponse(BaseModel):
    id: int
    subject: str
    topic: Optional[str]
    total_questions: int
    questions: List[SessionQuestionResponse]
    is_timed: bool
    time_limit: Optional[int]
    started_at: datetime

class SessionSubmit(BaseModel):
    session_id: int
    answers: Dict[str, str]
    time_taken: Optional[int] = 0

class SessionSubmitResponse(BaseModel):
    session_id: int
    score: int
    total: int
    correct: int
    wrong: int
    skipped: int
    accuracy: float
    xp_earned: int
    completed_at: datetime

class SessionHistoryResponse(BaseModel):
    id: int
    subject: str
    topic: Optional[str]
    score: int
    total: int
    accuracy: float
    xp_earned: int
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# MISTAKE SCHEMAS
# ============================================================

class MistakeResponse(BaseModel):
    id: int
    question_id: str
    user_answer: str
    correct_answer: str
    subject: str
    topic: str
    explanation: Optional[str]
    is_resolved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MistakeExplanationResponse(BaseModel):
    explanation: str
    key_concept: Optional[str]
    tips: List[str] = []
    wrong_explanations: Optional[Dict[str, str]]


# ============================================================
# BOOKMARK SCHEMAS
# ============================================================

class BookmarkCreate(BaseModel):
    question_id: str
    note: Optional[str] = None

class BookmarkResponse(BaseModel):
    id: int
    question_id: str
    note: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# LESSON SCHEMAS
# ============================================================

class LessonResponse(BaseModel):
    id: str
    subject: str
    topic: str
    title: str
    content: str
    reading_time: Optional[int]
    order: int

    model_config = ConfigDict(from_attributes=True)

class LessonProgressResponse(BaseModel):
    total: int
    completed: int
    progress: int


# ============================================================
# GAMIFICATION SCHEMAS
# ============================================================

class GamificationResponse(BaseModel):
    xp: int
    level: int
    streak: int
    badges: List[str]
    total_sessions: int
    total_questions: int
    accuracy: float

    model_config = ConfigDict(from_attributes=True)

class XPAddRequest(BaseModel):
    amount: int
    source: str


# ============================================================
# HEATMAP / MASTERY SCHEMAS
# ============================================================

class MasteryItem(BaseModel):
    accuracy: float
    attempts: int
    subject: str

class MasteryResponse(BaseModel):
    mastery: Dict[str, MasteryItem]

class MasteryUpdate(BaseModel):
    topic: str
    accuracy: float = Field(..., ge=0, le=100)
    subject: str


# ============================================================
# SUBSCRIPTION SCHEMAS
# ============================================================

class SubscriptionInit(BaseModel):
    plan: str  # "foundation", "campus", "pro", etc.

class SubscriptionInitResponse(BaseModel):
    authorization_url: str
    reference: str
    access_code: str

class SubscriptionVerifyResponse(BaseModel):
    status: str
    plan: str
    message: str

class SubscriptionStatusResponse(BaseModel):
    is_active: bool
    plan: str
    expires_at: Optional[datetime]
    days_remaining: int
    auto_renew: bool


# ============================================================
# AI SCHEMAS
# ============================================================

class AIExplanationRequest(BaseModel):
    question_id: str
    user_answer: str

class AIExplanationResponse(BaseModel):
    explanation: str
    key_concept: Optional[str]
    tips: List[str] = []
    wrong_explanations: Optional[Dict[str, str]]

class AIWeaknessRequest(BaseModel):
    subject: Optional[str] = None
    limit: int = Field(5, ge=1, le=10)

class AIWeaknessItem(BaseModel):
    topic: str
    accuracy: int
    priority: str
    recommendations: Optional[str]

class AIWeaknessResponse(BaseModel):
    weak_topics: List[AIWeaknessItem]
    summary: str
    created_at: datetime

class AIStudyPlanRequest(BaseModel):
    goal: str
    subjects: List[str]
    hours_per_week: int
    weak_topics: Optional[List[str]] = None
    days_until_exam: Optional[int] = None
    target_score: Optional[str] = None
    study_style: Optional[str] = None
    exam_type: Optional[str] = "jamb"

class AIStudyPlanResponse(BaseModel):
    plan: Dict[str, Any]


# ============================================================
# PARENT SCHEMAS
# ============================================================

class ParentLinkRequest(BaseModel):
    code: str

class ParentLinkResponse(BaseModel):
    success: bool
    linked_at: datetime

class ParentCodeResponse(BaseModel):
    code: str
    expires_at: datetime

class ParentStatusResponse(BaseModel):
    linked: bool
    children: List[Dict[str, Any]] = []

class ChildAnalyticsResponse(BaseModel):
    student: Dict[str, Any]


# ============================================================
# DUEL SCHEMAS
# ============================================================

class DuelCreate(BaseModel):
    subject: str
    topic: Optional[str] = None
    count: int = Field(10, ge=5, le=20)
    time_limit: int = Field(300, ge=60, le=600)
    is_public: bool = False
    questions: List[Dict] = Field(default_factory=list)  # ✅ Fixed indentation

class DuelJoin(BaseModel):
    code: str

class DuelSubmit(BaseModel):
    duel_id: int
    answers: Dict[str, str]

class DuelResponse(BaseModel):
    id: int
    challenger: Dict[str, Any]
    opponent: Optional[Dict[str, Any]]
    subject: str
    topic: Optional[str]
    status: str
    challenger_score: int
    opponent_score: int
    winner: Optional[Dict[str, Any]]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# LEADERBOARD SCHEMAS
# ============================================================

class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    avatar_url: Optional[str]
    xp: int
    level: int
    streak: int
    school: Optional[str]

class LeaderboardResponse(BaseModel):
    rankings: List[LeaderboardEntry]
    total_users: int
    filter: str


# ============================================================
# REFERRAL SCHEMAS
# ============================================================

class ReferralCodeResponse(BaseModel):
    code: str
    clicks: int
    signups: int
    rewards: int

class ReferralTrackRequest(BaseModel):
    code: str

class ReferralTrackResponse(BaseModel):
    success: bool
    referrer: str
    reward: int
    message: str


# ============================================================
# ADMIN SCHEMAS
# ============================================================

class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    new_users_today: int
    total_questions: int
    pending_questions: int
    total_revenue: float
    revenue_this_month: float
    total_sessions: int
    sessions_today: int
    subscription_breakdown: Dict[str, int]
    growth: Dict[str, float]

class AdminUserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    tier: str
    status: str
    created_at: datetime
    last_active: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class AdminUserUpdate(BaseModel):
    tier: Optional[str] = None
    status: Optional[str] = None

class AdminQuestionUpdate(BaseModel):
    status: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None


# ============================================================
# SYNC SCHEMAS
# ============================================================

class SyncRequest(BaseModel):
    bookmarks: Optional[List[Dict]] = None
    mistakes: Optional[List[Dict]] = None
    sessions: Optional[List[Dict]] = None
    results: Optional[List[Dict]] = None
    gamification: Optional[Dict] = None
    mastery: Optional[Dict] = None
    lessons: Optional[List[Dict]] = None
    planner: Optional[Dict] = None
    settings: Optional[Dict] = None
    profile: Optional[Dict] = None

class SyncResponse(BaseModel):
    success: bool
    synced_at: datetime
    synced_items: int
    conflicts: Optional[List[Dict]] = None
