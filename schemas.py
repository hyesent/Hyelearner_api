from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
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
    plan: Optional[str] = None
    tier: Optional[str] = None
    currency: str = "NGN"
    
    @field_validator('plan', 'tier')
    @classmethod
    def normalize_plan(cls, v):
        return v.lower() if v else None

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
    question: str
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
    questions: List[Dict] = Field(default_factory=list)

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


# ============================================================
# HYETUTOR — ANALYZE REQUEST (Bundled Data from Frontend)
# ============================================================

class StudyPlanExamInfo(BaseModel):
    exam_type: str = "jamb"
    exam_date: str

class StudyPlanSummary(BaseModel):
    days_remaining: int
    total_topics: int
    completed_topics: int
    total_hours: int
    completion_percentage: int
    weak_areas: List[str]

class WeeklyTopic(BaseModel):
    subject: str
    topic: str
    hours: float

class WeeklyScheduleItem(BaseModel):
    day: str
    topics: List[WeeklyTopic]
    total_hours: float
    completed: bool

class StudyPlanToday(BaseModel):
    topics: List[str]
    completed: int
    remaining: int
    hours_completed: float
    hours_remaining: float

class StudyPlanData(BaseModel):
    exam_info: StudyPlanExamInfo
    summary: StudyPlanSummary
    weekly_schedule: List[WeeklyScheduleItem]
    today: StudyPlanToday


class MasteryTopic(BaseModel):
    accuracy: int
    attempts: int
    last_updated: str


class SessionItem(BaseModel):
    id: str
    date: str
    subject: str
    topic: str
    mode: str
    score: int
    total: int
    correct: int
    wrong: int
    accuracy: int
    time_taken: int
    difficulty: str
    is_mock: bool


class MistakeItem(BaseModel):
    id: str
    question: str
    user_answer: str
    correct_answer: str
    topic: str
    subject: str
    created_at: str


class WeakTopicItem(BaseModel):
    topic: str
    accuracy: int
    priority: str
    mistake_count: int


class GamificationData(BaseModel):
    xp: int
    level: int
    streak: int
    longest_streak: int
    badges: List[str]
    total_sessions: int
    total_xp: int


class RevisionTask(BaseModel):
    id: str
    title: str
    completed: bool
    estimatedTime: int


class RevisionPlannerData(BaseModel):
    tasks: List[RevisionTask]
    tasks_completed_today: int
    tasks_total_today: int
    time_studied_today: int
    streak: int


class PreferencesData(BaseModel):
    study_style: str
    target_score: str
    hours_per_week: int
    study_hours_start: str
    study_hours_end: str


class ProfileData(BaseModel):
    name: str
    school: str
    exam: str
    country: str
    subjects: List[str]


class ConsistencyData(BaseModel):
    study_days: int
    missed_days: int
    total_days: int
    avg_sessions_per_day: float
    day_breakdown: Dict[str, int]
    session_times: List[str]


class HyeTutorDataBundle(BaseModel):
    study_plan: StudyPlanData
    mastery: Dict[str, MasteryTopic]
    sessions: List[SessionItem]
    mistakes: List[MistakeItem]
    weak_topics: List[WeakTopicItem]
    gamification: GamificationData
    revision_planner: RevisionPlannerData
    preferences: PreferencesData
    profile: ProfileData
    consistency: ConsistencyData


class HyeTutorAnalyzeRequest(BaseModel):
    user_id: str
    date: str
    exam_date: str
    difficulty_preference: str = "balanced"
    data: HyeTutorDataBundle


# ============================================================
# HYETUTOR — ANALYZE RESPONSE (All 18 Sections)
# ============================================================

class MissionResponse(BaseModel):
    id: str
    text: str
    reason: str
    priority: str
    xp_reward: int
    estimated_time: int
    completed: bool
    order: int


class NextSessionResponse(BaseModel):
    time: str
    subject: str
    topic: str
    duration: int
    difficulty: str
    priority: str
    reason: str


class TimeBudgetResponse(BaseModel):
    total: float
    completed: float
    remaining: float
    unit: str


class WeeklyGoalResponse(BaseModel):
    total: int
    completed: int
    remaining: int
    percentage: int
    unit: str


class PerformanceResponse(BaseModel):
    exam_readiness: int
    confidence: int
    consistency: int
    focus: int
    burnout_risk: str
    burnout_signs: List[str]


class SubjectConfidenceResponse(BaseModel):
    name: str
    mastery: int
    confidence: int
    status: str
    trend: str
    trend_amount: int
    priority: str


class ForecastResponse(BaseModel):
    days_remaining: int
    topics_remaining: int
    topics_per_day_needed: float
    current_pace: float
    pace_status: str
    estimated_completion: str
    days_behind: int
    completion_probability: int
    needs_adjustment: bool
    recommendation: str
    daily_target: float


class InsightResponse(BaseModel):
    id: str
    type: str
    message: str
    action: Optional[str] = None
    priority: str
    suggestion: Optional[str] = None


class HabitResponse(BaseModel):
    icon: str
    text: str
    detail: str


class MomentumWeeklyData(BaseModel):
    day: str
    hours: float


class MomentumResponse(BaseModel):
    hours: float
    average_per_day: float
    best_day: str
    longest_session: str
    missed_days: int
    streak: int
    weekly_data: List[MomentumWeeklyData]


class RevisionQueueItem(BaseModel):
    topic: str
    subject: str
    days_ago: int
    priority: str
    confidence: int


class QuickStatsResponse(BaseModel):
    topics_remaining: int
    lessons_remaining: int
    questions_remaining: int
    days_ahead: int


class PlanAdjustmentItem(BaseModel):
    topic: str
    hours: int
    reason: str


class RescheduleItem(BaseModel):
    topic: str
    from_date: str
    to_date: str
    reason: str


class PlanAdjustmentsResponse(BaseModel):
    add: List[PlanAdjustmentItem]
    remove: List[PlanAdjustmentItem]
    reschedule: List[RescheduleItem]
    new_load: float
    previous_load: float
    adjusted: bool


class EmergencyResponse(BaseModel):
    active: bool
    reason: Optional[str] = None
    days_to_exam: int


class RewardResponse(BaseModel):
    id: str
    label: str
    xp: int
    badge: str
    unlocked: bool
    claimed: bool


class HyeTutorAnalyzeResponse(BaseModel):
    success: bool = True
    generated_at: str
    missions: List[MissionResponse]
    total_xp_reward: int
    missions_progress: int
    next_session: NextSessionResponse
    time_budget: TimeBudgetResponse
    weekly_goal: WeeklyGoalResponse
    performance: PerformanceResponse
    subjects: List[SubjectConfidenceResponse]
    forecast: ForecastResponse
    insights: List[InsightResponse]
    habits: List[HabitResponse]
    momentum: MomentumResponse
    revision_queue: List[RevisionQueueItem]
    quick_stats: QuickStatsResponse
    calendar_days: List[int]
    motivation: str
    plan_adjustments: PlanAdjustmentsResponse
    emergency: EmergencyResponse
    rewards: List[RewardResponse]
    examDays: int


# ============================================================
# HYETUTOR — CHAT Request & Response
# ============================================================

class ChatContext(BaseModel):
    user_id: str
    recent_sessions: List[Dict[str, Any]]
    mastery: Dict[str, int]
    weak_topics: List[Dict[str, Any]]
    mistakes: List[Dict[str, Any]]
    gamification: Dict[str, Any]
    exam_days_remaining: int
    target_score: str


class HyeTutorChatRequest(BaseModel):
    question: str
    context: Optional[ChatContext] = None


class SuggestedAction(BaseModel):
    action: str
    duration: int


class HyeTutorChatResponse(BaseModel):
    success: bool = True
    answer: str
    confidence: int
    suggested_actions: List[SuggestedAction]
    related_insights: List[str]


# ============================================================
# HYETUTOR — MISSION COMPLETE
# ============================================================

class MissionCompleteRequest(BaseModel):
    mission_id: str
    completed_at: Optional[str] = None


class MissionCompleteResponse(BaseModel):
    success: bool = True
    mission: Dict[str, Any]
    xp_updated: int
    level_updated: int
    badge_unlocked: Optional[str] = None


# ============================================================
# HYETUTOR — REFLECTION
# ============================================================

class ReflectionRequest(BaseModel):
    date: str
    mood: str  # great, okay, difficult
    notes: Optional[str] = None
    time_taken: float
    sessions_completed: int
    distractions: Optional[str] = None


class ReflectionAdjustments(BaseModel):
    workload_reduced: bool
    physics_increased: bool
    new_topics_blocked: bool
    new_load: float
    recommendation: str


class ReflectionTask(BaseModel):
    text: str
    duration: int


class ReflectionNewSchedule(BaseModel):
    tasks: List[ReflectionTask]
    total_hours: float


class ReflectionResponse(BaseModel):
    success: bool = True
    adjustments: ReflectionAdjustments
    new_schedule: Dict[str, ReflectionNewSchedule]


# ============================================================
# HYETUTOR — CACHED Response
# ============================================================

class HyeTutorCachedResponse(BaseModel):
    cached: bool = True
    date: str
    expires_at: str
    data: HyeTutorAnalyzeResponse


# ============================================================
# SOCIAL SCHEMAS
# ============================================================

# ============================================================
# USER SEARCH
# ============================================================

class UserSearchResult(BaseModel):
    id: int
    username: str
    firstName: str
    lastName: str
    avatar: Optional[str]
    school: Optional[str]
    exam: Optional[str]
    streak: int
    xp: int
    level: int
    accuracy: float
    isFriend: bool
    friendRequestSent: bool
    isOnline: bool


class UserSearchResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


# ============================================================
# FRIENDS
# ============================================================

class FriendRequestResponse(BaseModel):
    id: int
    fromUser: Dict[str, Any]
    sentAt: datetime


class FriendResponse(BaseModel):
    id: int
    username: str
    firstName: str
    lastName: str
    avatar: Optional[str]
    school: Optional[str]
    exam: Optional[str]
    streak: int
    xp: int
    level: int
    accuracy: float
    isOnline: bool
    lastSeen: Optional[datetime]
    unreadMessages: int
    friendSince: datetime


class FriendsListResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


# ============================================================
# MESSAGES
# ============================================================

class MessageResponse(BaseModel):
    id: int
    senderId: int
    receiverId: int
    message: str
    isRead: bool
    createdAt: datetime


class ConversationResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class SendMessageRequest(BaseModel):
    recipientId: int
    message: str


class UnreadConversation(BaseModel):
    friendId: int
    friendUsername: str
    friendAvatar: Optional[str]
    unreadCount: int
    lastMessage: str
    lastMessageAt: datetime


class UnreadCountResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


# ============================================================
# DUEL INVITES
# ============================================================

class DuelInviteRequest(BaseModel):
    friendId: int
    subject: str
    topic: Optional[str] = None
    questionCount: int = 10
    timeLimit: int = 300


class DuelInviteResponse(BaseModel):
    id: int
    fromUser: Dict[str, Any]
    subject: str
    topic: Optional[str]
    questionCount: int
    timeLimit: int
    status: str
    invitedAt: datetime
    expiresAt: datetime


class DuelInviteListResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class DuelInviteRespondRequest(BaseModel):
    accept: bool


# ============================================================
# STUDY GROUPS
# ============================================================

class StudyGroupCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    subject: Optional[str] = None
    memberIds: List[int] = []


class StudyGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    subject: Optional[str]
    memberCount: int
    isMember: bool
    createdBy: int
    createdAt: datetime
    lastActivity: datetime


class StudyGroupListResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class StudyGroupJoinRequest(BaseModel):
    inviteCode: Optional[str] = None


class StudyGroupJoinResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class StudyGroupMessageResponse(BaseModel):
    id: int
    sender: Dict[str, Any]
    message: str
    isPinned: bool
    isAnnouncement: bool
    createdAt: datetime


class StudyGroupMessagesResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class SendGroupMessageRequest(BaseModel):
    message: str
    isAnnouncement: bool = False


class StudyGroupMemberResponse(BaseModel):
    id: int
    username: str
    firstName: str
    lastName: str
    avatar: Optional[str]
    role: str
    joinedAt: datetime


class StudyGroupMembersResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


# ============================================================
# ACTIVITY FEED
# ============================================================

class ActivityResponse(BaseModel):
    id: int
    type: str
    friend: Dict[str, Any]
    message: str
    details: Dict[str, Any]
    createdAt: datetime


class ActivityFeedResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class GlobalStatsResponse(BaseModel):
    totalUsers: int
    onlineNow: int
    sessionsToday: int


class GlobalActivityResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


# ============================================================
# CHALLENGES
# ============================================================

class ChallengeCreateRequest(BaseModel):
    type: str  # streak, questions, accuracy, xp
    friendIds: List[int]
    duration: int = 7
    stake: Optional[str] = None


class ChallengeResponse(BaseModel):
    id: int
    type: str
    creator: int
    participants: List[Dict[str, Any]]
    status: str
    startsAt: datetime
    endsAt: datetime


class ChallengeListResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class ChallengeStatusResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


# ============================================================
# FEEDBACK & CONTRIBUTIONS SCHEMAS
# ============================================================

# ============================================================
# FEEDBACK SCHEMAS
# ============================================================

class FeedbackCreate(BaseModel):
    type: str = "general"  # general, bug, feature, improvement
    message: str = Field(..., min_length=1)
    rating: Optional[int] = Field(None, ge=1, le=5)
    email: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    type: str
    message: str
    rating: Optional[int]
    email: Optional[str]
    user_id: Optional[int]
    user: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackListResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


# ============================================================
# CONTRIBUTION SCHEMAS
# ============================================================

class ContributionCreate(BaseModel):
    university: str = Field(..., min_length=1)
    course: str = Field(..., min_length=1)
    year: int = Field(..., ge=2000, le=datetime.now().year + 1)
    cutoff: int = Field(..., ge=0, le=400)
    exam_type: str = Field(..., min_length=1)  # jamb, waec, neco, etc.
    source: Optional[str] = None


class ContributionResponse(BaseModel):
    id: int
    university: str
    course: str
    year: int
    cutoff: int
    exam_type: str
    source: Optional[str]
    status: str  # pending, approved, rejected
    user_id: int
    user: Optional[Dict[str, Any]]
    created_at: datetime
    approved_at: Optional[datetime]
    approved_by: Optional[int]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ContributionListResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class ContributionApproveResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class ContributionRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class MyContributionsResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]
