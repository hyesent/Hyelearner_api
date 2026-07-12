import httpx
from typing import Dict, Any, Optional
from config import settings

class PaystackService:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    async def initialize_transaction(self, email: str, amount: int, metadata: Optional[Dict] = None) -> Dict:
        """Initialize a Paystack transaction"""
        async with httpx.AsyncClient() as client:
            payload = {
                "email": email,
                "amount": amount * 100,  # Convert to kobo
                "callback_url": settings.PAYSTACK_CALLBACK_URL,
                "metadata": metadata or {}
            }
            
            response = await client.post(
                f"{self.base_url}/transaction/initialize",
                headers=self.headers,
                json=payload
            )
            return response.json()
    
    async def verify_transaction(self, reference: str) -> Dict:
        """Verify a Paystack transaction"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self.headers
            )
            return response.json()
    
    async def create_subscription(self, email: str, plan_code: str) -> Dict:
        """Create a subscription on Paystack"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/subscription",
                headers=self.headers,
                json={
                    "customer": email,
                    "plan": plan_code,
                    "start_date": "now"
                }
            )
            return response.json()
    
    async def cancel_subscription(self, subscription_code: str) -> Dict:
        """Cancel a subscription"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/subscription/{subscription_code}/disable",
                headers=self.headers
            )
            return response.json()
    
    async def get_subscription_status(self, subscription_code: str) -> Dict:
        """Get subscription status"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/subscription/{subscription_code}",
                headers=self.headers
            )
            return response.json()

paystack_service = PaystackService()