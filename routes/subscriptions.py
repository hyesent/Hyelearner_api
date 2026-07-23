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
    "test@example.com",
    "admin@hyesent.com",
]

PREMIUM_DEV_IDS = [1, 2, 3]


# ============================================================
# 1. INITIALIZE SUBSCRIPTION
# ============================================================

@router.post("/init")
async def initialize_subscription(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initialize Paystack payment for subscription.
    Accepts: plan OR tier (case insensitive)
    """
    
    # Get plan from either 'plan' or 'tier' and normalize to lowercase
    plan = data.get("plan") or data.get("tier")
    plan = plan.lower() if plan else None
    currency = data.get("currency", "NGN")
    
    if not plan:
        raise HTTPException(status_code=400, detail="plan or tier is required")
    
    # Check if dev user — bypass payment
    if current_user.email in PREMIUM_DEV_USERS or current_user.id in PREMIUM_DEV_IDS:
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
        
        # ✅ DEV USER — Return mock URL
        return {
            "authorizationUrl": f"{settings.FRONTEND_URL}/subscriptions/verify?reference=dev_{current_user.id}",
            "reference": f"dev_{current_user.id}"
        }
    
    # Validate plan
    if plan not in ["foundation", "premium"]:
        raise HTTPException(status_code=400, detail="Invalid plan. Choose 'foundation' or 'premium'")
    
    # Check if already subscribed
    existing = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You already have an active subscription")
    
    # Initialize Paystack transaction
    amount = 1500 if plan == "foundation" else 5000
    
    try:
        result = await paystack_service.initialize_transaction(
            email=current_user.email,
            amount=amount,
            metadata={
                "user_id": current_user.id,
                "plan": plan,
                "source": "hyelearner"
            }
        )
        
        print(f"🔍 Paystack response: {result}")
        
        if not result or not result.get("status"):
            error_msg = result.get("message", "Payment initialization failed") if result else "No response from Paystack"
            print(f"❌ Paystack error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # ✅ SUCCESS — Return ONLY what frontend expects
        return {
            "authorizationUrl": result["data"]["authorization_url"],
            "reference": result["data"]["reference"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Paystack exception: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Payment initialization failed: {str(e)}")


# ============================================================
# 2. VERIFY PAYMENT
# ============================================================

@router.get("/verify")
async def verify_payment(
    reference: str = Query(...),
    db: Session = Depends(get_db)
):
    """Verify Paystack payment after user returns from Paystack."""
    
    # Check if dev reference
    if reference.startswith("dev_"):
        user_id = int(reference.split("_")[1])
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if subscription and subscription.is_active:
            return {
                "success": True,
                "data": {
                    "status": "success",
                    "tier": "foundation",
                    "amount": 1500,
                    "reference": reference,
                    "verifiedAt": datetime.utcnow().isoformat()
                }
            }
    
    try:
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
            
            amount = data.get("amount", 0) / 100  # Convert kobo to NGN
            
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
                "success": True,
                "data": {
                    "status": "success",
                    "tier": "foundation",
                    "amount": amount,
                    "reference": reference,
                    "verifiedAt": datetime.utcnow().isoformat()
                }
            }
        
        raise HTTPException(status_code=400, detail="Payment not successful")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")


# ============================================================
# 3. GET SUBSCRIPTION STATUS
# ============================================================

@router.get("/status")
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription status."""
    
    # Check hardcoded dev users
    is_hardcoded = current_user.email in PREMIUM_DEV_USERS or current_user.id in PREMIUM_DEV_IDS
    
    if is_hardcoded:
        return {
            "success": True,
            "data": {
                "isActive": True,
                "tier": "pro",
                "plan": "Pro",
                "expiresAt": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                "daysRemaining": 365,
                "autoRenew": True,
                "isHardcoded": True
            }
        }
    
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription or not subscription.is_active:
        return {
            "success": True,
            "data": {
                "isActive": False,
                "tier": "free",
                "plan": "Free",
                "expiresAt": None,
                "daysRemaining": 0,
                "autoRenew": False,
                "isHardcoded": False
            }
        }
    
    if subscription.end_date and subscription.end_date < datetime.utcnow():
        subscription.is_active = False
        db.commit()
        return {
            "success": True,
            "data": {
                "isActive": False,
                "tier": "free",
                "plan": "Free",
                "expiresAt": subscription.end_date.isoformat(),
                "daysRemaining": 0,
                "autoRenew": False,
                "isHardcoded": False
            }
        }
    
    days_remaining = (subscription.end_date - datetime.utcnow()).days if subscription.end_date else 0
    
    # Tier to display name mapping
    tier_names = {
        "foundation": "Foundation",
        "premium": "Premium",
        "pro": "Pro"
    }
    
    plan_display = tier_names.get(subscription.plan, subscription.plan.capitalize())
    
    return {
        "success": True,
        "data": {
            "isActive": True,
            "tier": subscription.plan,
            "plan": plan_display,
            "expiresAt": subscription.end_date.isoformat() if subscription.end_date else None,
            "daysRemaining": max(0, days_remaining),
            "autoRenew": True,
            "isHardcoded": False
        }
    }


# ============================================================
# 4. CANCEL SUBSCRIPTION
# ============================================================

@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel active subscription."""
    
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
        "message": "Subscription cancelled.",
        "data": {
            "expiresAt": datetime.utcnow().isoformat()
        }
    }


# ============================================================
# 5. UPGRADE SUBSCRIPTION
# ============================================================

@router.post("/upgrade")
async def upgrade_subscription(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upgrade subscription to a higher tier."""
    
    tier = data.get("tier")
    
    if not tier:
        raise HTTPException(status_code=400, detail="tier is required")
    
    if tier not in ["foundation", "premium", "pro"]:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    # Check if dev user — bypass payment
    if current_user.email in PREMIUM_DEV_USERS or current_user.id in PREMIUM_DEV_IDS:
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            subscription = Subscription(
                user_id=current_user.id,
                plan=tier,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=365),
                is_active=True
            )
            db.add(subscription)
        else:
            subscription.plan = tier
            subscription.is_active = True
            subscription.start_date = datetime.utcnow()
            subscription.end_date = datetime.utcnow() + timedelta(days=365)
        
        db.commit()
        
        return {
            "success": True,
            "data": {
                "tier": tier,
                "expiresAt": subscription.end_date.isoformat()
            }
        }
    
    # For non-dev users, redirect to payment
    return {
        "success": True,
        "message": f"Upgrade to {tier} requires payment. Please use /subscriptions/init",
        "data": {
            "tier": tier,
            "requiresPayment": True
        }
    }


# ============================================================
# 6. PAYSTACK WEBHOOK
# ============================================================

@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Paystack webhook endpoint."""
    
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    payload = await request.json()
    event = payload.get("event")
    data = payload.get("data")
    
    if event == "charge.success":
        reference = data.get("reference")
        amount = data.get("amount", 0) / 100
        metadata = data.get("metadata", {})
        user_id = metadata.get("user_id")
        plan = metadata.get("plan", "foundation")
        
        if user_id:
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).first()
            
            if not subscription:
                subscription = Subscription(
                    user_id=user_id,
                    plan=plan,
                    paystack_subscription_code=data.get("subscription_code"),
                    paystack_customer_code=data.get("customer_code"),
                    start_date=datetime.utcnow(),
                    end_date=datetime.utcnow() + timedelta(days=30),
                    is_active=True
                )
                db.add(subscription)
            else:
                subscription.plan = plan
                subscription.is_active = True
                subscription.start_date = datetime.utcnow()
                subscription.end_date = datetime.utcnow() + timedelta(days=30)
            
            db.commit()
    
    elif event == "subscription.disable":
        subscription_code = data.get("subscription_code")
        if subscription_code:
            subscription = db.query(Subscription).filter(
                Subscription.paystack_subscription_code == subscription_code
            ).first()
            if subscription:
                subscription.is_active = False
                subscription.end_date = datetime.utcnow()
                db.commit()
    
    elif event == "subscription.enable":
        subscription_code = data.get("subscription_code")
        if subscription_code:
            subscription = db.query(Subscription).filter(
                Subscription.paystack_subscription_code == subscription_code
            ).first()
            if subscription:
                subscription.is_active = True
                db.commit()
    
    return {"status": "received", "success": True}
