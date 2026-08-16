from fastapi import APIRouter, Request, HTTPException
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
async def strava_webhook(event: StravaWebhookEvent):
    """Receive webhook events from Strava"""
    # TODO: Validate webhook signature
    # TODO: Queue sync job for the activity
    # TODO: Update activity in database
    
    print(f"Received webhook: {event.aspect_type} for activity {event.object_id}")
    
    return {"status": "received"}

@router.get("/strava/verify")
async def verify_webhook(
    hub_mode: str,
    hub_challenge: str,
    hub_verify_token: str
):
    """Verify webhook subscription with Strava"""
    # TODO: Validate hub_verify_token
    if hub_mode == "subscribe":
        return {"hub.challenge": hub_challenge}
    else:
        raise HTTPException(status_code=400, detail="Invalid mode")
