from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jose import JWTError
from typing import Optional, Callable, Any
from datetime import date, datetime

from database import get_db
from models import User, AIUsage
from auth import decode_token

# ✅ Global config — change here to adjust the limit everywhere
AI_DAILY_LIMIT = 10


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ============================================================
# AUTH DEPENDENCIES
# ============================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception

        user_id = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception

    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return current_user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def get_current_parent_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Parent privileges required",
        )
    return current_user


# ============================================================
# ⭐ AI USAGE — LIMIT CHECK + INCREMENT
# ============================================================

def get_or_create_usage_today(
    db: Session,
    user_id: int,
    lock: bool = False,
) -> AIUsage:
    """
    Fetch the AIUsage row for (user_id, today), creating it if missing.
    If `lock=True`, uses SELECT ... FOR UPDATE to serialize concurrent
    requests for the same user.
    """
    today = date.today()

    query = db.query(AIUsage).filter(
        AIUsage.user_id == user_id,
        AIUsage.date == today,
    )
    if lock:
        query = query.with_for_update()

    usage = query.first()

    if usage is None:
        usage = AIUsage(user_id=user_id, date=today, count=0)
        db.add(usage)
        try:
            db.flush()
        except IntegrityError:
            # Another request just created it — re-fetch under lock
            db.rollback()
            usage = (
                db.query(AIUsage)
                .filter(AIUsage.user_id == user_id, AIUsage.date == today)
                .with_for_update()
                .first()
            )
            if usage is None:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to initialize AI usage tracker",
                )

    return usage


async def call_ai_with_limit(
    db: Session,
    user_id: int,
    ai_fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Executes an AI call under the daily limit.

    Flow:
      1. Lock the (user_id, today) AIUsage row.
      2. If count >= AI_DAILY_LIMIT → 429 before touching the AI.
      3. Call `ai_fn(*args, **kwargs)`.
      4. On success → count += 1.
      5. On failure → failed_count += 1, raise 502.

    The lock serializes concurrent requests for the same user,
    so two parallel calls can't both pass the check when count == 9.
    """
    usage = get_or_create_usage_today(db, user_id, lock=True)

    if usage.count >= AI_DAILY_LIMIT:
        db.rollback()
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily AI limit reached ({AI_DAILY_LIMIT}/day). "
                "Try again tomorrow."
            ),
        )

    # Call the AI — still holding the row lock
    try:
        result = await ai_fn(*args, **kwargs)
    except Exception as e:
        # AI threw → don't count toward the limit
        usage.failed_count = (usage.failed_count or 0) + 1
        usage.last_attempt_at = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"AI unavailable: {str(e)}",
        )

    # AI returned but flagged a failure internally
    if isinstance(result, dict) and result.get("success") is False:
        usage.failed_count = (usage.failed_count or 0) + 1
        usage.last_attempt_at = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=result.get("error") or "AI returned an invalid response",
        )

    # Success → increment
    usage.count = (usage.count or 0) + 1
    usage.last_attempt_at = datetime.utcnow()
    db.commit()

    return result


def get_ai_usage_today(db: Session, user_id: int) -> dict:
    """Read-only snapshot for /user/ai-usage and /user/hydrate."""
    usage = get_or_create_usage_today(db, user_id, lock=False)
    today = date.today()
    reset_at = datetime.combine(
        today,
        datetime.min.time(),
    ).replace(hour=0, minute=0, second=0, microsecond=0)

    # reset_at = tomorrow midnight
    from datetime import timedelta
    reset_at = datetime.combine(today + timedelta(days=1), datetime.min.time())

    return {
        "used": usage.count or 0,
        "limit": AI_DAILY_LIMIT,
        "failed": usage.failed_count or 0,
        "reset_at": reset_at.isoformat(),
    }
