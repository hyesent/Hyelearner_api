from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import secrets

from database import get_db
from models import User, Subscription
from schemas import (
    SubscriptionInit, SubscriptionInitResponse,
    SubscriptionVerifyResponse, SubscriptionStatusResponse
)
from dependencies import get_current_user
from services.paystack import paystack_service
from config import settings

router = APIRouter()

# ============================================================
# HARDCODED PREMIUM DEV USERS
# ============================================================
PREMIUM_DEV_USERS = [
    "dev@hyesent.com",
    "test@hyesent.com",
    "admin@hyesent.com",
]

PREMIUM_DEV_IDS = [1, 2, 3]


@router.post("/init", response_model=SubscriptionInitResponse)
async def initialize_subscription(
    data: SubscriptionInit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initialize Paystack payment for subscription"""
    # Check if dev user — bypass payment
    if current_user.email in PREMIUM_DEV_USERS or current_user.id in PREMIUM_DEV_IDS:
        # Create/update subscription directly
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            subscription = Subscription(
                user_id=current_user.id,
                plan="foundation",
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=365),
                is_active=True
            )
            db.add(subscription)
        else:
            subscription.plan = "foundation"
            subscription.is_active = True
            subscription.start_date = datetime.utcnow()
            subscription.end_date = datetime.utcnow() + timedelta(days=365)
        
        db.commit()
        
        return {
            "authorization_url": f"{settings.FRONTEND_URL}/subscriptions/verify?reference=dev_{current_user.id}",
            "reference": f"dev_{current_user.id}",
            "access_code": "dev_access"
        }
    
    # Validate plan
    if data.plan not in ["foundation"]:
        raise HTTPException(status_code=400, detail="Invalid plan. Choose 'foundation'")
    
    # Check if already subscribed
    existing = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You already have an active subscription")
    
    # Initialize Paystack transaction
    amount = 1500
    result = await paystack_service.initialize_transaction(
        email=current_user.email,
        amount=amount,
        metadata={
            "user_id": current_user.id,
            "plan": data.plan,
            "source": "hyelearner"
        }
    )
    
    if not result.get("status"):
        raise HTTPException(status_code=400, detail="Payment initialization failed")
    
    return {
        "authorization_url": result["data"]["authorization_url"],
        "reference": result["data"]["reference"],
        "access_code": result["data"]["access_code"]
    }


@router.get("/verify", response_model=SubscriptionVerifyResponse)
async def verify_payment(
    reference: str = Query(...),
    db: Session = Depends(get_db)
):
    """Verify Paystack payment"""
    # Check if dev reference
    if reference.startswith("dev_"):
        user_id = int(reference.split("_")[1])
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if subscription and subscription.is_active:
            return {
                "status": "success",
                "plan": "foundation",
                "message": "Dev subscription active"
            }
    
    result = await paystack_service.verify_transaction(reference)
    
    if not result.get("status"):
        raise HTTPException(status_code=400, detail="Verification failed")
    
    data = result["data"]
    metadata = data.get("metadata", {})
    user_id = metadata.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in transaction")
    
    if data["status"] == "success":
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if not subscription:
            subscription = Subscription(
                user_id=user_id,
                plan="foundation",
                paystack_subscription_code=data.get("subscription_code"),
                paystack_customer_code=data.get("customer_code"),
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=30),
                is_active=True
            )
            db.add(subscription)
        else:
            subscription.plan = "foundation"
            subscription.is_active = True
            subscription.start_date = datetime.utcnow()
            subscription.end_date = datetime.utcnow() + timedelta(days=30)
        
        db.commit()
        
        return {
            "status": "success",
            "plan": "foundation",
            "message": "Subscription activated successfully"
        }
    
    raise HTTPException(status_code=400, detail="Payment not successful")


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription status"""
    # ============================================================
    # HARDCODE — Check if user is a dev account
    # ============================================================
    if current_user.email in PREMIUM_DEV_USERS or current_user.id in PREMIUM_DEV_IDS:
        return {
            "is_active": True,
            "plan": "foundation",
            "expires_at": datetime.utcnow() + timedelta(days=365),
            "days_remaining": 365,
            "auto_renew": True
        }
    
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription or not subscription.is_active:
        return {
            "is_active": False,
            "plan": "free",
            "expires_at": None,
            "days_remaining": 0,
            "auto_renew": False
        }
    
    if subscription.end_date and subscription.end_date < datetime.utcnow():
        subscription.is_active = False
        db.commit()
        return {
            "is_active": False,
            "plan": "free",
            "expires_at": subscription.end_date,
            "days_remaining": 0,
            "auto_renew": False
        }
    
    days_remaining = (subscription.end_date - datetime.utcnow()).days if subscription.end_date else 0
    
    return {
        "is_active": True,
        "plan": subscription.plan,
        "expires_at": subscription.end_date,
        "days_remaining": max(0, days_remaining),
        "auto_renew": True
    }


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel subscription"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    if subscription.paystack_subscription_code:
        await paystack_service.cancel_subscription(subscription.paystack_subscription_code)
    
    subscription.is_active = False
    subscription.end_date = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Subscription cancelled successfully",
        "expires_at": datetime.utcnow().isoformat()
    }


@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Paystack webhook endpoint"""
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    payload = await request.json()
    event = payload.get("event")
    data = payload.get("data")
    
    if event == "subscription.create":
        pass
    elif event == "subscription.disable":
        pass
    elif event == "subscription.enable":
        pass
    
    return {"status": "received"}