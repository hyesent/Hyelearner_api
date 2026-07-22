from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey, Enum, Index, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
import uuid
from sqlalchemy.dialects.postgresql import UUID as PGUUID


# ============================================================
# ENUMS
# ============================================================

class UserRole(str, enum.Enum):
    STUDENT = "student"
    PARENT = "parent"
    ADMIN = "admin"

class UserTier(str, enum.Enum):
    FOUNDATION = "foundation"
    CAMPUS = "campus"
    CAREER = "career"
    PRO = "pro"
    PRO_CAMPUS = "pro_campus"

class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    PREMIUM = "premium"

class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class DuelStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ============================================================
# SHARED TABLES
# ============================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.STUDENT)
    tier = Column(Enum(UserTier), default=UserTier.FOUNDATION)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    school = Column(String, nullable=True)
    country = Column(String, nullable=True)
    exam = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    goal = Column(String, nullable=True)
    subscription_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_study_plan_update = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    stats = relationship("UserStats", back_populates="user", uselist=False)
    subscriptions = relationship("Subscription", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    mistakes = relationship("Mistake", back_populates="user")
    bookmarks = relationship("Bookmark", back_populates="user")
    lesson_progress = relationship("LessonProgress", back_populates="user")
    topic_mastery = relationship("TopicMastery", back_populates="user")
    planner = relationship("RevisionPlanner", back_populates="user", uselist=False)
    parent_links = relationship("ParentLink", foreign_keys="ParentLink.child_id")
    parent_of = relationship("ParentLink", foreign_keys="ParentLink.parent_id")
    referral_code = relationship("ReferralCode", back_populates="user", uselist=False)
    referrals_made = relationship("Referral", foreign_keys="Referral.referrer_id")
    referrals_received = relationship("Referral", foreign_keys="Referral.referred_id")
    duels_challenged = relationship("Duel", foreign_keys="Duel.challenger_id")
    duels_opponent = relationship("Duel", foreign_keys="Duel.opponent_id")
    
    # ============================================================
    # HYETUTOR RELATIONSHIPS
    # ============================================================
    hyetutor_caches = relationship("HyetutorCache", back_populates="user", cascade="all, delete-orphan")
    missions = relationship("Mission", back_populates="user", cascade="all, delete-orphan")
    reflections = relationship("Reflection", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    dark_mode = Column(Boolean, default=False)
    notifications = Column(Boolean, default=True)
    study_reminders = Column(Boolean, default=True)
    reminder_time = Column(String, default="09:00")
    sound_effects = Column(Boolean, default=True)
    auto_sync = Column(Boolean, default=True)
    ai_daily_limit = Column(Integer, default=10)
    ai_used_today = Column(Integer, default=0)
    ai_used_month = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="settings")


class UserStats(Base):
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    streak = Column(Integer, default=0)
    badges = Column(JSON, default=[])
    total_sessions = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="stats")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan = Column(Enum(SubscriptionPlan), default=SubscriptionPlan.FREE)
    paystack_subscription_code = Column(String, unique=True, nullable=True)
    paystack_customer_code = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="subscriptions")


# ============================================================
# FOUNDATION TABLES
# ============================================================

class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, index=True)
    type = Column(String, default="multiple_choice")
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)
    answer = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    difficulty = Column(Enum(Difficulty), default=Difficulty.MEDIUM)
    topic = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    platform = Column(String, default="hyelearner")
    year = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_question_subject', 'subject'),
        Index('idx_question_topic', 'topic'),
        Index('idx_question_difficulty', 'difficulty'),
        Index('idx_question_subject_topic', 'subject', 'topic'),
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(String, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    reading_time = Column(Integer, nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_lesson_subject', 'subject'),
        Index('idx_lesson_topic', 'topic'),
    )


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    lesson_id = Column(String, ForeignKey("lessons.id"))
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="lesson_progress")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=True)
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    wrong_answers = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    question_ids = Column(JSON, default=[])
    answers = Column(JSON, default={})
    time_taken = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")


class Mistake(Base):
    __tablename__ = "mistakes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(String, nullable=False)
    user_answer = Column(String, nullable=False)
    correct_answer = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="mistakes")

    __table_args__ = (
        Index('idx_mistake_user', 'user_id'),
        Index('idx_mistake_subject', 'subject'),
        Index('idx_mistake_resolved', 'is_resolved'),
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="bookmarks")


class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    correct = Column(Integer, default=0)
    total = Column(Integer, default=0)
    mastery_score = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="topic_mastery")

    __table_args__ = (
        Index('idx_mastery_user', 'user_id'),
        Index('idx_mastery_subject_topic', 'subject', 'topic'),
    )


class RevisionPlanner(Base):
    __tablename__ = "revision_planners"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    exam_date = Column(DateTime(timezone=True), nullable=False)
    daily_hours = Column(Float, default=3.0)
    schedule = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="planner")


class ParentLink(Base):
    __tablename__ = "parent_links"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("users.id"))
    child_id = Column(Integer, ForeignKey("users.id"))
    code = Column(String, unique=True, index=True, nullable=False)
    is_approved = Column(Boolean, default=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("User", foreign_keys=[parent_id])
    child = relationship("User", foreign_keys=[child_id])


class Duel(Base):
    __tablename__ = "duels"

    id = Column(Integer, primary_key=True, index=True)
    challenger_id = Column(Integer, ForeignKey("users.id"))
    opponent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    code = Column(String, unique=True, index=True, nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=True)
    question_ids = Column(JSON, default=[])
    status = Column(String, default="waiting")
    is_public = Column(Boolean, default=False)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    challenger_score = Column(Integer, default=0)
    opponent_score = Column(Integer, default=0)
    challenger_answers = Column(JSON, nullable=True)
    opponent_answers = Column(JSON, nullable=True)
    time_limit = Column(Integer, default=300)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    questions_data = Column(JSON, default=[])

    challenger = relationship("User", foreign_keys=[challenger_id])
    opponent = relationship("User", foreign_keys=[opponent_id])
    winner = relationship("User", foreign_keys=[winner_id])

    __table_args__ = (
        Index('idx_duel_status', 'status'),
        Index('idx_duel_challenger', 'challenger_id'),
        Index('idx_duel_opponent', 'opponent_id'),
    )


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    code = Column(String, unique=True, index=True, nullable=False)
    clicks = Column(Integer, default=0)
    signups = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="referral_code")


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id"))
    referred_id = Column(Integer, ForeignKey("users.id"), unique=True)
    referral_code = Column(String, ForeignKey("referral_codes.code"))
    reward_given = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    referrer = relationship("User", foreign_keys=[referrer_id])
    referred = relationship("User", foreign_keys=[referred_id])


# ============================================================
# HYETUTOR TABLES
# ============================================================

class HyetutorCache(Base):
    __tablename__ = "hyetutor_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    data = Column(JSON, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="hyetutor_caches")
    
    __table_args__ = (
        Index('idx_hyetutor_cache_user_date', 'user_id', 'date'),
    )
    
    def __repr__(self):
        return f"<HyetutorCache user={self.user_id} date={self.date}>"


class Mission(Base):
    __tablename__ = "missions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    mission_code = Column(String(50), nullable=True)  # ✅ ADDED
    text = Column(String(255), nullable=False)
    reason = Column(String(255), nullable=True)
    priority = Column(String(20), default="medium")
    xp_reward = Column(Integer, default=25)
    estimated_time = Column(Integer, nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="missions")
    
    __table_args__ = (
        Index('idx_mission_user_date', 'user_id', 'date'),
        Index('idx_mission_code', 'mission_code'),  # ✅ ADDED
        Index('idx_mission_completed', 'completed'),
    )
    
    def __repr__(self):
        return f"<Mission user={self.user_id} date={self.date} completed={self.completed}>"


class Reflection(Base):
    __tablename__ = "reflections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    mood = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    time_taken = Column(Float, nullable=True)
    sessions_completed = Column(Integer, default=0)
    distractions = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="reflections")
    
    __table_args__ = (
        Index('idx_reflection_user_date', 'user_id', 'date'),
    )
    
    def __repr__(self):
        return f"<Reflection user={self.user_id} date={self.date} mood={self.mood}>"
