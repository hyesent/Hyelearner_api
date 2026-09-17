from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey, Enum, Index, Date, Numeric, BigInteger, UniqueConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
import uuid
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB


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
    FOUNDATION = "foundation"

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

    # HYETUTOR
    hyetutor_caches = relationship("HyetutorCache", back_populates="user", cascade="all, delete-orphan")
    missions = relationship("Mission", back_populates="user", cascade="all, delete-orphan")
    reflections = relationship("Reflection", back_populates="user", cascade="all, delete-orphan")

    # SOCIAL
    friend_requests_sent = relationship("FriendRequest", foreign_keys="FriendRequest.sender_id", back_populates="sender")
    friend_requests_received = relationship("FriendRequest", foreign_keys="FriendRequest.receiver_id", back_populates="receiver")
    friendships = relationship("Friendship", foreign_keys="Friendship.user_id", back_populates="user")
    friends = relationship("Friendship", foreign_keys="Friendship.friend_id", back_populates="friend_user")
    messages_sent = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    messages_received = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")
    duel_invites_sent = relationship("DuelInvite", foreign_keys="DuelInvite.sender_id", back_populates="sender")
    duel_invites_received = relationship("DuelInvite", foreign_keys="DuelInvite.receiver_id", back_populates="receiver")
    group_memberships = relationship("StudyGroupMember", back_populates="user")
    group_messages = relationship("StudyGroupMessage", back_populates="sender")
    groups_created = relationship("StudyGroup", back_populates="creator")
    activities = relationship("Activity", back_populates="user")
    challenges_created = relationship("Challenge", back_populates="creator")
    challenge_participants = relationship("ChallengeParticipant", back_populates="user")

    # FEEDBACK & CONTRIBUTIONS
    feedback = relationship("Feedback", foreign_keys="Feedback.user_id", back_populates="user", cascade="all, delete-orphan")
    contributions = relationship("Contribution", foreign_keys="Contribution.user_id", back_populates="user", cascade="all, delete-orphan")

    # DAILY STATS
    daily_stats = relationship("UserDailyStats", back_populates="user", cascade="all, delete-orphan")

    # NEW RELATIONSHIPS
    ai_usage = relationship("AIUsage", back_populates="user", cascade="all, delete-orphan")
    daily_tutor_lessons = relationship("DailyTutorLesson", back_populates="user", cascade="all, delete-orphan")
    daily_tutor_quizzes = relationship("DailyTutorQuiz", back_populates="user", cascade="all, delete-orphan")
    daily_tutor_sessions = relationship("DailyTutorSession", back_populates="user", cascade="all, delete-orphan")
    career_checks = relationship("CareerCheck", back_populates="user", cascade="all, delete-orphan")
    study_plans = relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")
    weakness_snapshots = relationship("WeaknessSnapshot", back_populates="user", cascade="all, delete-orphan")
    hyetutor_chats = relationship("HyetutorChat", back_populates="user", cascade="all, delete-orphan")
    dictionary_favorites = relationship("DictionaryFavorite", back_populates="user", cascade="all, delete-orphan")
    dictionary_recent = relationship("DictionaryRecent", back_populates="user", cascade="all, delete-orphan")


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

    explanation_record = relationship(
        "MistakeExplanation",
        back_populates="mistake",
        uselist=False,
        cascade="all, delete-orphan",
    )

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
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    child_id = Column(Integer, ForeignKey("users.id"))
    code = Column(String, unique=True, index=True, nullable=False)
    status = Column(String(20), default="pending")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_approved = Column(Boolean, default=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    last_viewed_at = Column(DateTime(timezone=True), nullable=True)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

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

    user = relationship("User", back_populates="hyetutor_caches")

    __table_args__ = (
        Index('idx_hyetutor_cache_user_date', 'user_id', 'date'),
        UniqueConstraint('user_id', 'date', name='uq_hyetutor_cache_user_date'),
    )

    def __repr__(self):
        return f"<HyetutorCache user={self.user_id} date={self.date}>"


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    mission_code = Column(String(50), nullable=True)
    text = Column(String(255), nullable=False)
    reason = Column(String(255), nullable=True)
    priority = Column(String(20), default="medium")
    xp_reward = Column(Integer, default=25)
    estimated_time = Column(Integer, nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="missions")

    __table_args__ = (
        Index('idx_mission_user_date', 'user_id', 'date'),
        Index('idx_mission_code', 'mission_code'),
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

    user = relationship("User", back_populates="reflections")

    __table_args__ = (
        Index('idx_reflection_user_date', 'user_id', 'date'),
    )

    def __repr__(self):
        return f"<Reflection user={self.user_id} date={self.date} mood={self.mood}>"


# ============================================================
# SOCIAL TABLES
# ============================================================

class FriendRequest(Base):
    __tablename__ = "friend_requests"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sender = relationship("User", foreign_keys=[sender_id], back_populates="friend_requests_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="friend_requests_received")

    __table_args__ = (
        Index('idx_friend_requests_sender', 'sender_id'),
        Index('idx_friend_requests_receiver', 'receiver_id'),
        Index('idx_friend_requests_status', 'status'),
    )


class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="friendships")
    friend_user = relationship("User", foreign_keys=[friend_id], back_populates="friends")

    __table_args__ = (
        Index('idx_friendships_user', 'user_id'),
        Index('idx_friendships_friend', 'friend_id'),
        Index('idx_friendships_user_friend', 'user_id', 'friend_id', unique=True),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    parent_message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="messages_received")
    parent = relationship("Message", remote_side=[id], foreign_keys=[parent_message_id])

    __table_args__ = (
        Index('idx_messages_sender', 'sender_id'),
        Index('idx_messages_receiver', 'receiver_id'),
        Index('idx_messages_conversation', 'sender_id', 'receiver_id'),
        Index('idx_messages_read', 'is_read'),
    )


class DuelInvite(Base):
    __tablename__ = "duel_invites"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String(100), nullable=False)
    topic = Column(String(100), nullable=True)
    question_count = Column(Integer, default=10)
    time_limit = Column(Integer, default=300)
    status = Column(String(20), default="pending")
    duel_id = Column(Integer, ForeignKey("duels.id", ondelete="SET NULL"), nullable=True)
    invited_at = Column(DateTime(timezone=True), default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sender = relationship("User", foreign_keys=[sender_id], back_populates="duel_invites_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="duel_invites_received")
    duel = relationship("Duel", foreign_keys=[duel_id])

    __table_args__ = (
        Index('idx_duel_invites_sender', 'sender_id'),
        Index('idx_duel_invites_receiver', 'receiver_id'),
        Index('idx_duel_invites_status', 'status'),
    )


class StudyGroup(Base):
    __tablename__ = "study_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    subject = Column(String(50), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invite_code = Column(String(20), unique=True, index=True, nullable=True)
    max_members = Column(Integer, default=20)
    is_private = Column(Boolean, default=False)
    pinned_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", foreign_keys=[created_by], back_populates="groups_created")
    members = relationship("StudyGroupMember", back_populates="group", cascade="all, delete-orphan")
    messages = relationship("StudyGroupMessage", back_populates="group", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_study_groups_subject', 'subject'),
        Index('idx_study_groups_invite_code', 'invite_code'),
    )


class StudyGroupMember(Base):
    __tablename__ = "study_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="member")
    joined_at = Column(DateTime(timezone=True), default=func.now())
    last_read_at = Column(DateTime(timezone=True), default=func.now())

    group = relationship("StudyGroup", back_populates="members")
    user = relationship("User", back_populates="group_memberships")

    __table_args__ = (
        Index('idx_group_members_group', 'group_id'),
        Index('idx_group_members_user', 'user_id'),
        Index('idx_group_members_group_user', 'group_id', 'user_id', unique=True),
    )


class StudyGroupMessage(Base):
    __tablename__ = "study_group_messages"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=False)
    is_announcement = Column(Boolean, default=False)
    parent_message_id = Column(Integer, ForeignKey("study_group_messages.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    group = relationship("StudyGroup", back_populates="messages")
    sender = relationship("User", back_populates="group_messages")
    parent = relationship("StudyGroupMessage", remote_side=[id], foreign_keys=[parent_message_id])

    __table_args__ = (
        Index('idx_group_messages_group', 'group_id'),
        Index('idx_group_messages_pinned', 'is_pinned'),
        Index('idx_group_messages_announcement', 'is_announcement'),
    )


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)
    duration = Column(Integer, default=7)
    stake = Column(String(50), nullable=True)
    status = Column(String(20), default="active")
    starts_at = Column(DateTime(timezone=True), default=func.now())
    ends_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    creator = relationship("User", foreign_keys=[creator_id], back_populates="challenges_created")
    participants = relationship("ChallengeParticipant", back_populates="challenge", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_challenges_type', 'type'),
        Index('idx_challenges_status', 'status'),
    )


class ChallengeParticipant(Base):
    __tablename__ = "challenge_participants"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime(timezone=True), default=func.now())

    challenge = relationship("Challenge", back_populates="participants")
    user = relationship("User", back_populates="challenge_participants")

    __table_args__ = (
        Index('idx_challenge_participants_challenge', 'challenge_id'),
        Index('idx_challenge_participants_user', 'user_id'),
        Index('idx_challenge_participants_challenge_user', 'challenge_id', 'user_id', unique=True),
    )


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)
    message = Column(String(255), nullable=True)
    data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="activities")

    __table_args__ = (
        Index('idx_activities_user', 'user_id'),
        Index('idx_activities_type', 'type'),
        Index('idx_activities_created', 'created_at'),
    )


# ============================================================
# FEEDBACK & CONTRIBUTIONS TABLES
# ============================================================

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    type = Column(String(20), default="general")
    message = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="feedback")

    __table_args__ = (
        Index('idx_feedback_user', 'user_id'),
        Index('idx_feedback_type', 'type'),
        Index('idx_feedback_created', 'created_at'),
    )


class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    university = Column(String(100), nullable=False)
    course = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)
    cutoff = Column(Integer, nullable=False)
    exam_type = Column(String(20), nullable=False)
    source = Column(String(200), nullable=True)
    status = Column(String(20), default="pending")
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="contributions")
    approver = relationship("User", foreign_keys=[approved_by])
    rejecter = relationship("User", foreign_keys=[rejected_by])

    __table_args__ = (
        Index('idx_contribution_user', 'user_id'),
        Index('idx_contribution_status', 'status'),
        Index('idx_contribution_university', 'university'),
        Index('idx_contribution_exam_type', 'exam_type'),
        Index('idx_contribution_created', 'created_at'),
    )


# ============================================================
# USER DAILY STATS TABLE
# ============================================================

class UserDailyStats(Base):
    __tablename__ = "user_daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    streak = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    sessions = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    wrong = Column(Integer, default=0)
    study_time_minutes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="daily_stats")

    __table_args__ = (
        Index('idx_user_daily_stats_user_date', 'user_id', 'date'),
        Index('idx_user_daily_stats_date', 'date'),
    )


# ============================================================
# NEW TABLES — AI USAGE, DAILY TUTOR, CAREER, STUDY PLAN, ETC.
# ============================================================

class AIUsage(Base):
    __tablename__ = "ai_usage"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=func.current_date())
    count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="ai_usage")

    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_ai_usage_user_date'),
        Index('idx_ai_usage_user_date', 'user_id', 'date'),
    )


class DailyTutorLesson(Base):
    __tablename__ = "daily_tutor_lessons"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=func.current_date())
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    lesson_json = Column(JSONB, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="daily_tutor_lessons")

    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_daily_tutor_lessons_user_date'),
        Index('idx_daily_tutor_lessons_user_date', 'user_id', 'date'),
    )


class DailyTutorQuiz(Base):
    __tablename__ = "daily_tutor_quizzes"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=func.current_date())
    lesson_id = Column(BigInteger, ForeignKey("daily_tutor_lessons.id", ondelete="CASCADE"), nullable=True)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    quiz_json = Column(JSONB, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="daily_tutor_quizzes")

    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_daily_tutor_quizzes_user_date'),
        Index('idx_daily_tutor_quizzes_user_date', 'user_id', 'date'),
    )


class DailyTutorSession(Base):
    __tablename__ = "daily_tutor_sessions"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=func.current_date())
    lesson_id = Column(BigInteger, ForeignKey("daily_tutor_lessons.id", ondelete="SET NULL"), nullable=True)
    quiz_id = Column(BigInteger, ForeignKey("daily_tutor_quizzes.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    answers = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)
    reflection = Column(JSONB, nullable=True)
    status = Column(String, nullable=False, default="in_progress")
    current_step = Column(String, nullable=False, default="lesson")
    started_at = Column(DateTime(timezone=True), default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="daily_tutor_sessions")

    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_daily_tutor_sessions_user_date'),
        Index('idx_daily_tutor_sessions_user_date', 'user_id', 'date'),
        Index('idx_daily_tutor_sessions_status', 'user_id', 'status'),
    )


class MistakeExplanation(Base):
    __tablename__ = "mistake_explanations"

    id = Column(BigInteger, primary_key=True, index=True)
    mistake_id = Column(Integer, ForeignKey("mistakes.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    explanation_json = Column(JSONB, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=func.now())

    mistake = relationship("Mistake", back_populates="explanation_record")

    __table_args__ = (
        Index('idx_mistake_explanations_user', 'user_id'),
    )


class WeaknessSnapshot(Base):
    __tablename__ = "weakness_snapshots"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    snapshot_json = Column(JSONB, nullable=False)
    summary = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="weakness_snapshots")

    __table_args__ = (
        Index('idx_weakness_snapshots_user_date', 'user_id', 'generated_at'),
    )


class HyetutorChat(Base):
    __tablename__ = "hyetutor_chat"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    confidence = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="hyetutor_chats")

    __table_args__ = (
        Index('idx_hyetutor_chat_user_date', 'user_id', 'created_at'),
    )


class CareerCheck(Base):
    __tablename__ = "career_checks"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    university = Column(String, nullable=False)
    country = Column(String, nullable=False)
    course = Column(String, nullable=False)
    score = Column(Numeric, nullable=True)
    score_type = Column(String, nullable=True)
    subjects = Column(JSONB, nullable=True)
    status = Column(String, nullable=True)
    chance_percentage = Column(Integer, nullable=True)
    result_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="career_checks")

    __table_args__ = (
        Index('idx_career_checks_user_date', 'user_id', 'created_at'),
        Index('idx_career_checks_user_course', 'user_id', 'university', 'course'),
    )


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_json = Column(JSONB, nullable=False)
    exam_type = Column(String, nullable=True)
    exam_date = Column(Date, nullable=True)
    target_score = Column(String, nullable=True)
    goal = Column(Text, nullable=True)
    subjects = Column(JSONB, nullable=True)
    study_style = Column(String, nullable=True)
    hours_per_week = Column(Integer, nullable=True)
    generated_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    status = Column(String, nullable=False, default="active")

    user = relationship("User", back_populates="study_plans")

    __table_args__ = (
       Index('uq_study_plans_one_active','user_id', unique=True,postgresql_where=text("status = 'active'"),),
    )


class DictionaryFavorite(Base):
    __tablename__ = "dictionary_favorites"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="dictionary_favorites")

    __table_args__ = (
        UniqueConstraint('user_id', 'word', name='uq_dictionary_favorites_user_word'),
        Index('idx_dictionary_favorites_user', 'user_id', 'created_at'),
    )


class DictionaryRecent(Base):
    __tablename__ = "dictionary_recent"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word = Column(String, nullable=False)
    searched_at = Column(DateTime(timezone=True), default=func.now())

    user = relationship("User", back_populates="dictionary_recent")

    __table_args__ = (
        Index('idx_dictionary_recent_user_date', 'user_id', 'searched_at'),
    )
