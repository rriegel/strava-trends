from fastapi import APIRouter, Request, HTTPException, Header
from config import settings
import hashlib
import hmac
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class StravaWebhookEvent(BaseModel):
    object_type: str
    object_id: int
    aspect_type: str
    owner_id: int
    updates: Optional[dict] = None
    subscription_id: int

@router.post("/strava")
async def strava_webhook(
    request: Request,
    event: StravaWebhookEvent,
    x_hub_signature: str = Header(None, alias="X-Hub-Signature")
):
    """Receive webhook events from Strava"""
    # Validate webhook signature
    if settings.strava_client_secret:
        if not x_hub_signature:
            raise HTTPException(status_code=401, detail="Missing signature")
        
        body = await request.body()
        expected_signature = hmac.new(
            settings.strava_client_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(f"sha256={expected_signature}", x_hub_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process webhook event
    # TODO: Queue sync job for the activity instead of processing synchronously
    print(f"Received webhook: {event.aspect_type} for activity {event.object_id}")
    
    return {"status": "received"}

@router.get("/strava/verify")
async def verify_webhook(
    hub_mode: str,
    hub_challenge: str,
    hub_verify_token: str
):
    """Verify webhook subscription with Strava"""
    # In production, validate hub_verify_token matches your configured secret
    # For now, just return the challenge
    if hub_mode == "subscribe":
        return {"hub.challenge": hub_challenge}
    else:
        raise HTTPException(status_code=400, detail="Invalid mode")
