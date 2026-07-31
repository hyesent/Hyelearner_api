# ============================================================
# services/hyescriptures.py — Hyescriptures Supabase Client
# ============================================================

from supabase import create_client, Client
from config import settings
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class HyescripturesService:
    """Service for interacting with Hyescriptures Supabase project."""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the Supabase client for Hyescriptures."""
        if settings.HYESCRIPTURES_SUPABASE_URL and settings.HYESCRIPTURES_SUPABASE_KEY:
            try:
                self.client = create_client(
                    settings.HYESCRIPTURES_SUPABASE_URL,
                    settings.HYESCRIPTURES_SUPABASE_KEY
                )
                print("✅ Hyescriptures Supabase client initialized")
            except Exception as e:
                print(f"❌ Hyescriptures Supabase client failed: {e}")
                self.client = None
        else:
            print("⚠️ Hyescriptures Supabase credentials not configured")
    
    def is_configured(self) -> bool:
        """Check if Hyescriptures client is configured."""
        return self.client is not None
    
    async def update_subscription(self, email: str, plan: str) -> Dict[str, Any]:
        """
        Update or create a subscription for a Hyescriptures user.
        """
        if not self.client:
            return {
                "success": False,
                "error": "Hyescriptures client not configured"
            }
        
        try:
            # Check if user exists in Hyescriptures
            user_response = self.client.table("users").select("*").eq("email", email).execute()
            user = user_response.data[0] if user_response.data else None
            
            if not user:
                # Create user if doesn't exist
                user_response = self.client.table("users").insert({
                    "email": email,
                    "subscription_plan": plan,
                    "subscription_status": "active",
                    "subscription_starts_at": datetime.utcnow().isoformat(),
                    "subscription_expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
                
                print(f"✅ Hyescriptures user created: {email}")
                
                return {
                    "success": True,
                    "user_id": user_response.data[0]["id"],
                    "plan": plan,
                    "action": "created"
                }
            
            # Update existing user
            self.client.table("users").update({
                "subscription_plan": plan,
                "subscription_status": "active",
                "subscription_starts_at": datetime.utcnow().isoformat(),
                "subscription_expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user["id"]).execute()
            
            print(f"✅ Hyescriptures user updated: {email} → {plan}")
            
            return {
                "success": True,
                "user_id": user["id"],
                "plan": plan,
                "action": "updated"
            }
            
        except Exception as e:
            print(f"❌ Hyescriptures subscription update failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_subscription_status(self, email: str) -> Dict[str, Any]:
        """
        Get subscription status for a Hyescriptures user.
        """
        if not self.client:
            return {
                "active": False,
                "plan": None,
                "expiresAt": None,
                "daysRemaining": 0,
                "error": "Hyescriptures client not configured"
            }
        
        try:
            response = self.client.table("users").select("*").eq("email", email).execute()
            user = response.data[0] if response.data else None
            
            if not user:
                return {
                    "active": False,
                    "plan": None,
                    "expiresAt": None,
                    "daysRemaining": 0
                }
            
            # Check if subscription is active
            is_active = user.get("subscription_status") == "active"
            expires_at = user.get("subscription_expires_at")
            
            days_remaining = 0
            if expires_at:
                try:
                    # Parse ISO format
                    expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    days_remaining = (expiry_date - datetime.utcnow()).days
                except:
                    days_remaining = 0
            
            return {
                "active": is_active,
                "plan": user.get("subscription_plan"),
                "expiresAt": expires_at,
                "daysRemaining": max(0, days_remaining)
            }
            
        except Exception as e:
            print(f"❌ Hyescriptures status check failed: {e}")
            return {
                "active": False,
                "plan": None,
                "expiresAt": None,
                "daysRemaining": 0,
                "error": str(e)
            }
    
    async def cancel_subscription(self, email: str) -> Dict[str, Any]:
        """
        Cancel a Hyescriptures subscription.
        """
        if not self.client:
            return {
                "success": False,
                "error": "Hyescriptures client not configured"
            }
        
        try:
            response = self.client.table("users").select("*").eq("email", email).execute()
            user = response.data[0] if response.data else None
            
            if not user:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            self.client.table("users").update({
                "subscription_status": "cancelled",
                "subscription_expires_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user["id"]).execute()
            
            print(f"✅ Hyescriptures subscription cancelled: {email}")
            
            return {
                "success": True,
                "message": "Subscription cancelled"
            }
            
        except Exception as e:
            print(f"❌ Hyescriptures cancellation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# ============================================================
# INSTANCE
# ============================================================

hyescriptures_service = HyescripturesService()
