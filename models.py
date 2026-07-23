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
    
    # ============================================================
    # HYETUTOR RELATIONSHIPS
    # ============================================================
    hyetutor_caches = relationship("HyetutorCache", back_populates="user", cascade="all, delete-orphan")
    missions = relationship("Mission", back_populates="user", cascade="all, delete-orphan")
    reflections = relationship("Reflection", back_populates="user", cascade="all, delete-orphan")

    # ============================================================
    # SOCIAL RELATIONSHIPS
    # ============================================================
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

    # ============================================================
    # FEEDBACK & CONTRIBUTIONS RELATIONSHIPS (FIXED)
    # ============================================================
    feedback = relationship("Feedback", foreign_keys="Feedback.user_id", back_populates="user", cascade="all, delete-orphan")
    contributions = relationship("Contribution", foreign_keys="Contribution.user_id", back_populates="user", cascade="all, delete-orphan")


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
    status = Column(String(20), default="pending")  
    expires_at = Column(DateTime(timezone=True), nullable=True)  
    is_approved = Column(Boolean, default=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
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
    
    # Relationships
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
    
    # Relationships
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
    status = Column(String(20), default="pending")  # pending, accepted, rejected
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="friend_requests_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="friend_requests_received")
    
    __table_args__ = (
        Index('idx_friend_requests_sender', 'sender_id'),
        Index('idx_friend_requests_receiver', 'receiver_id'),
        Index('idx_friend_requests_status', 'status'),
    )
    
    def __repr__(self):
        return f"<FriendRequest sender={self.sender_id} receiver={self.receiver_id} status={self.status}>"


class Friendship(Base):
    __tablename__ = "friendships"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="friendships")
    friend_user = relationship("User", foreign_keys=[friend_id], back_populates="friends")
    
    __table_args__ = (
        Index('idx_friendships_user', 'user_id'),
        Index('idx_friendships_friend', 'friend_id'),
        Index('idx_friendships_user_friend', 'user_id', 'friend_id', unique=True),
    )
    
    def __repr__(self):
        return f"<Friendship user={self.user_id} friend={self.friend_id}>"


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
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="messages_received")
    parent = relationship("Message", remote_side=[id], foreign_keys=[parent_message_id])
    
    __table_args__ = (
        Index('idx_messages_sender', 'sender_id'),
        Index('idx_messages_receiver', 'receiver_id'),
        Index('idx_messages_conversation', 'sender_id', 'receiver_id'),
        Index('idx_messages_read', 'is_read'),
    )
    
    def __repr__(self):
        return f"<Message sender={self.sender_id} receiver={self.receiver_id} read={self.is_read}>"


class DuelInvite(Base):
    __tablename__ = "duel_invites"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String(100), nullable=False)
    topic = Column(String(100), nullable=True)
    question_count = Column(Integer, default=10)
    time_limit = Column(Integer, default=300)
    status = Column(String(20), default="pending")  # pending, accepted, rejected, expired
    duel_id = Column(Integer, ForeignKey("duels.id", ondelete="SET NULL"), nullable=True)
    invited_at = Column(DateTime(timezone=True), default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="duel_invites_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="duel_invites_received")
    duel = relationship("Duel", foreign_keys=[duel_id])
    
    __table_args__ = (
        Index('idx_duel_invites_sender', 'sender_id'),
        Index('idx_duel_invites_receiver', 'receiver_id'),
        Index('idx_duel_invites_status', 'status'),
    )
    
    def __repr__(self):
        return f"<DuelInvite sender={self.sender_id} receiver={self.receiver_id} status={self.status}>"


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
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="groups_created")
    members = relationship("StudyGroupMember", back_populates="group", cascade="all, delete-orphan")
    messages = relationship("StudyGroupMessage", back_populates="group", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_study_groups_subject', 'subject'),
        Index('idx_study_groups_invite_code', 'invite_code'),
    )
    
    def __repr__(self):
        return f"<StudyGroup id={self.id} name={self.name} members={len(self.members)}>"


class StudyGroupMember(Base):
    __tablename__ = "study_group_members"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="member")  # admin, moderator, member
    joined_at = Column(DateTime(timezone=True), default=func.now())
    last_read_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    group = relationship("StudyGroup", back_populates="members")
    user = relationship("User", back_populates="group_memberships")
    
    __table_args__ = (
        Index('idx_group_members_group', 'group_id'),
        Index('idx_group_members_user', 'user_id'),
        Index('idx_group_members_group_user', 'group_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<StudyGroupMember group={self.group_id} user={self.user_id} role={self.role}>"


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
    
    # Relationships
    group = relationship("StudyGroup", back_populates="messages")
    sender = relationship("User", back_populates="group_messages")
    parent = relationship("StudyGroupMessage", remote_side=[id], foreign_keys=[parent_message_id])
    
    __table_args__ = (
        Index('idx_group_messages_group', 'group_id'),
        Index('idx_group_messages_pinned', 'is_pinned'),
        Index('idx_group_messages_announcement', 'is_announcement'),
    )
    
    def __repr__(self):
        return f"<StudyGroupMessage group={self.group_id} sender={self.sender_id} pinned={self.is_pinned}>"


class Challenge(Base):
    __tablename__ = "challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)  # streak, questions, accuracy, xp
    duration = Column(Integer, default=7)  # days
    stake = Column(String(50), nullable=True)
    status = Column(String(20), default="active")  # active, completed, cancelled
    starts_at = Column(DateTime(timezone=True), default=func.now())
    ends_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", foreign_keys=[creator_id], back_populates="challenges_created")
    participants = relationship("ChallengeParticipant", back_populates="challenge", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_challenges_type', 'type'),
        Index('idx_challenges_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Challenge id={self.id} type={self.type} status={self.status}>"


class ChallengeParticipant(Base):
    __tablename__ = "challenge_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    challenge = relationship("Challenge", back_populates="participants")
    user = relationship("User", back_populates="challenge_participants")
    
    __table_args__ = (
        Index('idx_challenge_participants_challenge', 'challenge_id'),
        Index('idx_challenge_participants_user', 'user_id'),
        Index('idx_challenge_participants_challenge_user', 'challenge_id', 'user_id', unique=True),
    )
    
    def __repr__(self):
        return f"<ChallengeParticipant challenge={self.challenge_id} user={self.user_id}>"


class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)  # session, streak, level_up, duel, message, group, challenge
    message = Column(String(255), nullable=True)
    data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="activities")
    
    __table_args__ = (
        Index('idx_activities_user', 'user_id'),
        Index('idx_activities_type', 'type'),
        Index('idx_activities_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Activity user={self.user_id} type={self.type}>"


# ============================================================
# FEEDBACK & CONTRIBUTIONS TABLES
# ============================================================

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    type = Column(String(20), default="general")  # general, bug, feature, improvement
    message = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5
    email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="feedback")
    
    __table_args__ = (
        Index('idx_feedback_user', 'user_id'),
        Index('idx_feedback_type', 'type'),
        Index('idx_feedback_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Feedback id={self.id} type={self.type} user={self.user_id}>"


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
    
    # Relationships
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
    
    def __repr__(self):
        return f"<Contribution id={self.id} university={self.university} course={self.course} status={self.status}>"  # ✅ FIXED
