# ============================================================
# routes/parent.py — Parent Linking + Parent Dashboard
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import secrets

from database import get_db
from models import (
    User, ParentLink, UserStats, Subscription, Session as PracticeSession,
    TopicMastery, Mistake, Duel, StudyPlan, UserRole,
)
from schemas import (
    ParentLinkRequest,
    ParentViewRequest,
    ParentViewResponse,
    ParentViewStudent,
    ParentViewSubject,
    ParentViewRecentSession,
    ParentViewStudyPlan,
    ParentViewSubscription,
)
from dependencies import get_current_user

router = APIRouter()

ONLINE_WINDOW_MINUTES = 5


# ============================================================
# HELPERS
# ============================================================

def _is_online(user: User) -> bool:
    if not user or not user.last_login:
        return False
    now = datetime.now(timezone.utc)
    last = user.last_login
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last) < timedelta(minutes=ONLINE_WINDOW_MINUTES)


def _iso(dt) -> Optional[str]:
    if not dt:
        return None
    return dt.isoformat()


def _seconds_to_hours(seconds: int) -> float:
    return round((seconds or 0) / 3600, 1)


def _role_value(user: User) -> str:
    role = user.role
    return role.value if hasattr(role, "value") else str(role)


# ============================================================
# 1. GENERATE CODE — Child App
# ============================================================

@router.post("/generate-code")
async def generate_parent_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Child generates a permanent 6-character code for parent to link.
    Code never expires. If code already exists, return it.
    """
    existing = db.query(ParentLink).filter(
        ParentLink.child_id == current_user.id,
        ParentLink.status.in_(['pending', 'active']),
    ).first()

    if existing:
        return {
            "success": True,
            "data": {
                "code": existing.code,
                "expiresAt": None,
            },
        }

    code = secrets.token_hex(3).upper()
    while db.query(ParentLink).filter(ParentLink.code == code).first():
        code = secrets.token_hex(3).upper()

    link = ParentLink(
        child_id=current_user.id,
        parent_id=None,
        code=code,
        status='pending',
        expires_at=None,  # never expires
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        view_count=0,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return {
        "success": True,
        "data": {
            "code": link.code,
            "expiresAt": None,
        },
    }


# ============================================================
# 2. LINK CHILD — Child App (kept for backward compat)
# ============================================================

@router.post("/link")
async def link_child(
    request: ParentLinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Child enters code from parent to link.
    Note: kept for backward compatibility. Codes never expire now.
    """
    code = (request.code or "").strip().upper()

    link = db.query(ParentLink).filter(
        ParentLink.code == code,
        ParentLink.status.in_(['pending', 'active']),
    ).first()

    if not link:
        raise HTTPException(404, detail="Invalid code")

    # If already linked, treat as success
    if link.status == 'active' and link.child_id == current_user.id:
        stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
        return {
            "success": True,
            "data": {
                "linked": True,
                "linkedAt": _iso(link.updated_at),
                "studentId": current_user.id,
                "student": {
                    "name": f"{current_user.first_name} {current_user.last_name}",
                    "streak": stats.streak if stats else 0,
                    "xp": stats.xp if stats else 0,
                    "accuracy": stats.accuracy if stats else 0,
                },
            },
        }

    # If link belongs to another child, reject
    if link.child_id != current_user.id:
        raise HTTPException(400, detail="Code already used by another child")

    # Activate link. parent_id stays null — parents don't have User rows.
    link.status = 'active'
    link.updated_at = datetime.utcnow()
    db.commit()

    stats = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()

    return {
        "success": True,
        "data": {
            "linked": True,
            "linkedAt": _iso(link.updated_at),
            "studentId": current_user.id,
            "student": {
                "name": f"{current_user.first_name} {current_user.last_name}",
                "streak": stats.streak if stats else 0,
                "xp": stats.xp if stats else 0,
                "accuracy": stats.accuracy if stats else 0,
            },
        },
    }


# ============================================================
# 3. GET STATUS — Child App
# ============================================================

@router.get("/status")
async def get_parent_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Child checks if they're linked to a parent.
    Parent check is skipped — parents don't have User rows.
    """
    role = _role_value(current_user)

    if role == UserRole.PARENT.value:
        # Legacy path: parent as User — return any links where parent_id matches
        children = db.query(ParentLink).filter(
            ParentLink.parent_id == current_user.id,
            ParentLink.status == 'active',
        ).all()

        child_data = []
        for link in children:
            child = db.query(User).filter(User.id == link.child_id).first()
            if child:
                child_data.append({
                    "id": child.id,
                    "name": f"{child.first_name} {child.last_name}",
                    "linkedAt": _iso(link.created_at),
                })

        return {
            "success": True,
            "data": {
                "linked": len(child_data) > 0,
                "children": child_data,
            },
        }

    # Child path
    link = db.query(ParentLink).filter(
        ParentLink.child_id == current_user.id,
        ParentLink.status == 'active',
    ).first()

    if link:
        return {
            "success": True,
            "data": {
                "linked": True,
                "code": link.code,
                "linkedAt": _iso(link.updated_at),
                "children": [],
            },
        }

    # Not linked yet — maybe a pending code exists
    pending = db.query(ParentLink).filter(
        ParentLink.child_id == current_user.id,
        ParentLink.status == 'pending',
    ).first()

    return {
        "success": True,
        "data": {
            "linked": False,
            "pendingCode": pending.code if pending else None,
            "children": [],
        },
    }


# ============================================================
# 4. GET STUDENT ANALYTICS — legacy child/parent self-view
# ============================================================

@router.get("/analytics/{student_id}")
async def get_student_analytics(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != student_id:
        link = db.query(ParentLink).filter(
            ParentLink.child_id == student_id,
            ParentLink.parent_id == current_user.id,
            ParentLink.status == 'active',
        ).first()
        if not link:
            raise HTTPException(403, detail="Not authorized to view this student")

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(404, detail="Student not found")

    stats = db.query(UserStats).filter(UserStats.user_id == student_id).first()
    subscription = db.query(Subscription).filter(
        Subscription.user_id == student_id,
        Subscription.is_active == True,
    ).first()

    sessions = db.query(PracticeSession).filter(
        PracticeSession.user_id == student_id,
        PracticeSession.is_completed == True,
    ).all()

    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    study_today = sum(s.time_taken or 0 for s in sessions if s.completed_at and s.completed_at.date() == today)
    study_week = sum(s.time_taken or 0 for s in sessions if s.completed_at and s.completed_at.date() >= week_ago)
    study_month = sum(s.time_taken or 0 for s in sessions if s.completed_at and s.completed_at.date() >= month_ago)

    mastery = db.query(TopicMastery).filter(TopicMastery.user_id == student_id).all()

    subjects = {}
    for m in mastery:
        if m.subject not in subjects:
            subjects[m.subject] = {"name": m.subject, "correct": 0, "total": 0}
        subjects[m.subject]["correct"] += m.correct or 0
        subjects[m.subject]["total"] += m.total or 0

    for s in subjects.values():
        s["readiness"] = round((s["correct"] / s["total"]) * 100, 1) if s["total"] > 0 else 50

    return {
        "success": True,
        "data": {
            "student": {
                "id": student.id,
                "name": f"{student.first_name} {student.last_name}",
                "streak": stats.streak if stats else 0,
                "xp": stats.xp if stats else 0,
                "level": stats.level if stats else 1,
                "accuracy": stats.accuracy if stats else 0,
                "school": student.school,
                "exam": student.exam,
                "subscription": {
                    "plan": subscription.plan.value if subscription and hasattr(subscription.plan, "value") else "free",
                    "status": "active" if subscription else "inactive",
                    "expires": _iso(subscription.end_date) if subscription else None,
                },
                "studyTime": {
                    "today": _seconds_to_hours(study_today),
                    "week": _seconds_to_hours(study_week),
                    "month": _seconds_to_hours(study_month),
                },
                "subjects": list(subjects.values()),
            },
        },
    }


# ============================================================
# 5. UNLINK — Child App
# ============================================================

@router.post("/unlink")
async def unlink_parent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    link = db.query(ParentLink).filter(
        ParentLink.child_id == current_user.id,
        ParentLink.status == 'active',
    ).first()

    if not link:
        raise HTTPException(404, detail="No active link found")

    link.status = 'unlinked'
    link.updated_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": "Unlinked successfully"}


# ============================================================
# 6. APPROVE ACTION — Parent App (stub, unchanged)
# ============================================================

@router.post("/approve/{student_id}")
async def approve_action(
    student_id: int,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    action = request.get("action")
    if not action:
        raise HTTPException(400, detail="Action is required")

    link = db.query(ParentLink).filter(
        ParentLink.child_id == student_id,
        ParentLink.parent_id == current_user.id,
        ParentLink.status == 'active',
    ).first()

    if not link:
        raise HTTPException(403, detail="Not authorized")

    return {
        "success": True,
        "approved": True,
        "approvedAt": datetime.utcnow().isoformat(),
        "action": action,
    }


# ============================================================
# 7. GET CHILDREN LIST — legacy parent-as-User
# ============================================================

@router.get("/children")
async def get_children(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if _role_value(current_user) != UserRole.PARENT.value:
        raise HTTPException(403, detail="Parent access required")

    children = db.query(ParentLink).filter(
        ParentLink.parent_id == current_user.id,
        ParentLink.status == 'active',
    ).all()

    child_data = []
    for link in children:
        child = db.query(User).filter(User.id == link.child_id).first()
        if child:
            stats = db.query(UserStats).filter(UserStats.user_id == child.id).first()
            child_data.append({
                "id": child.id,
                "name": f"{child.first_name} {child.last_name}",
                "streak": stats.streak if stats else 0,
                "xp": stats.xp if stats else 0,
                "level": stats.level if stats else 1,
                "linkedAt": _iso(link.created_at),
            })

    return {
        "success": True,
        "data": {
            "children": child_data,
            "total": len(child_data),
        },
    }


# ============================================================
# 8. PARENT VIEW — code-based, no auth required
# ============================================================

@router.post("/view", response_model=ParentViewResponse)
async def parent_view(
    request: ParentViewRequest,
    db: Session = Depends(get_db),
):
    """
    Parent-facing endpoint. The code IS the auth.
    No login, no JWT, no session. Returns child's dashboard snapshot.
    """
    code = (request.code or "").strip().upper()
    if not code:
        raise HTTPException(400, detail="Code is required")

    link = db.query(ParentLink).filter(
        ParentLink.code == code,
        ParentLink.status.in_(['pending', 'active']),
    ).first()

    if not link:
        raise HTTPException(404, detail="Invalid code")

    # First view activates the link + bumps counter
    now = datetime.utcnow()
    link.status = 'active'
    link.last_viewed_at = now
    link.view_count = (link.view_count or 0) + 1
    link.updated_at = now
    db.commit()

    student = db.query(User).filter(User.id == link.child_id).first()
    if not student:
        raise HTTPException(404, detail="Student not found")

    # ── Stats ──
    stats = db.query(UserStats).filter(UserStats.user_id == student.id).first()

    # ── Subscription ──
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == student.id, Subscription.is_active == True)
        .order_by(Subscription.end_date.desc())
        .first()
    )

    # ── Study time ──
    today_date = datetime.utcnow().date()
    week_ago = today_date - timedelta(days=7)
    month_ago = today_date - timedelta(days=30)

    all_sessions = db.query(PracticeSession).filter(
        PracticeSession.user_id == student.id,
        PracticeSession.is_completed == True,
    ).all()

    study_today_sec = sum(
        s.time_taken or 0 for s in all_sessions
        if s.completed_at and s.completed_at.date() == today_date
    )
    study_week_sec = sum(
        s.time_taken or 0 for s in all_sessions
        if s.completed_at and s.completed_at.date() >= week_ago
    )
    study_month_sec = sum(
        s.time_taken or 0 for s in all_sessions
        if s.completed_at and s.completed_at.date() >= month_ago
    )
    has_studied_today = study_today_sec > 0

    # ── Recent sessions (last 5) ──
    recent = (
        db.query(PracticeSession)
        .filter(
            PracticeSession.user_id == student.id,
            PracticeSession.is_completed == True,
        )
        .order_by(desc(PracticeSession.completed_at))
        .limit(5)
        .all()
    )
    recent_sessions = [
        ParentViewRecentSession(
            id=s.id,
            subject=s.subject,
            topic=s.topic,
            score=s.correct_answers,
            total=s.total_questions,
            accuracy=s.accuracy,
            completed_at=_iso(s.completed_at),
        )
        for s in recent
    ]

    # ── Subject readiness ──
    mastery = db.query(TopicMastery).filter(TopicMastery.user_id == student.id).all()

    subj_agg = {}
    for m in mastery:
        if m.subject not in subj_agg:
            subj_agg[m.subject] = {"correct": 0, "total": 0}
        subj_agg[m.subject]["correct"] += m.correct or 0
        subj_agg[m.subject]["total"] += m.total or 0

    subjects_list = []
    weak_subjects = []
    for name, agg in subj_agg.items():
        readiness = round((agg["correct"] / agg["total"]) * 100, 1) if agg["total"] > 0 else 0.0
        subjects_list.append(ParentViewSubject(name=name, readiness=readiness))
        if agg["total"] > 0 and readiness < 50:
            weak_subjects.append(name)

    subjects_list.sort(key=lambda s: s.readiness, reverse=True)

    # ── Mistakes ──
    unresolved_mistakes = db.query(Mistake).filter(
        Mistake.user_id == student.id,
        Mistake.is_resolved == False,
    ).count()

    # ── Duels ──
    duel_wins = db.query(Duel).filter(
        Duel.winner_id == student.id,
        Duel.status == 'completed',
    ).count()

    duel_losses = db.query(Duel).filter(
        or_(Duel.challenger_id == student.id, Duel.opponent_id == student.id),
        Duel.status == 'completed',
        Duel.winner_id.isnot(None),
        Duel.winner_id != student.id,
    ).count()

    # ── Study plan ──
    active_plan = db.query(StudyPlan).filter_by(
        user_id=student.id, status='active'
    ).first()

    plan_resp = None
    if active_plan:
        days_remaining = None
        if active_plan.exam_date:
            delta = active_plan.exam_date - today_date
            days_remaining = max(0, delta.days)

        # On track: studied >= 60% of target hours this week
        weekly_target = active_plan.hours_per_week or 10
        weekly_done = _seconds_to_hours(study_week_sec)
        on_track = weekly_done >= (weekly_target * 0.6)

        plan_resp = ParentViewStudyPlan(
            exam_type=active_plan.exam_type,
            exam_date=active_plan.exam_date.isoformat() if active_plan.exam_date else None,
            days_remaining=days_remaining,
            on_track=on_track,
            weekly_hours_target=weekly_target,
            weekly_hours_done=weekly_done,
        )

    # ── Subscription snapshot ──
    sub_resp = None
    if sub:
        sub_resp = ParentViewSubscription(
            plan=sub.plan.value if hasattr(sub.plan, "value") else str(sub.plan),
            is_active=bool(sub.is_active),
            expires_at=_iso(sub.end_date),
        )

    # ── Badges (top 3) ──
    badges = []
    if stats and stats.badges:
        try:
            badges = list(stats.badges)[:3]
        except Exception:
            badges = []

    student_payload = ParentViewStudent(
        id=student.id,
        name=f"{student.first_name} {student.last_name}",
        first_name=student.first_name,
        school=student.school,
        exam=student.exam,
        is_online=_is_online(student),
        last_login=_iso(student.last_login),
        last_activity=_iso(stats.last_activity) if stats else None,
        level=stats.level if stats else 1,
        streak=stats.streak if stats else 0,
        accuracy=stats.accuracy if stats else 0.0,
        study_today=_seconds_to_hours(study_today_sec),
        study_week=_seconds_to_hours(study_week_sec),
        study_month=_seconds_to_hours(study_month_sec),
        subjects=subjects_list,
        recent_sessions=recent_sessions,
        badges=badges,
        duel_wins=duel_wins,
        duel_losses=duel_losses,
        unresolved_mistakes=unresolved_mistakes,
        has_studied_today=has_studied_today,
        weak_subjects=weak_subjects,
        study_plan=plan_resp,
        subscription=sub_resp,
    )

    return ParentViewResponse(success=True, student=student_payload)
