import httpx
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session
from models.activity import Activity
from models.user import User

class StravaSyncService:
    """Sync activities from Strava API"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def sync_user_activities(self, user_id: int) -> Dict:
        """Sync all activities for a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Update sync status
        user.sync_status = "syncing"
        self.db.commit()
        
        try:
            # Fetch activities from Strava
            activities = await self._fetch_activities(user.access_token)
            
            # Process and store activities
            for activity_data in activities:
                self._process_activity(user_id, activity_data)
            
            # Update sync timestamp
            user.last_sync_at = datetime.now()
            user.sync_status = "idle"
            self.db.commit()
            
            return {"status": "success", "synced_count": len(activities)}
        
        except Exception as e:
            user.sync_status = "error"
            self.db.commit()
            raise e
    
    async def _fetch_activities(self, access_token: str) -> List[Dict]:
        """Fetch activities from Strava API"""
        activities = []
        page = 1
        per_page = 100
        
        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    "https://www.strava.com/api/v3/athlete/activities",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"page": page, "per_page": per_page}
                )
                
                if response.status_code != 200:
                    raise Exception(f"Strava API error: {response.status_code}")
                
                page_activities = response.json()
                if not page_activities:
                    break
                
                activities.extend(page_activities)
                page += 1
        
        return activities
    
    def _process_activity(self, user_id: int, activity_data: Dict):
        """Process and store a single activity"""
        # Check if activity already exists
        existing = self.db.query(Activity).filter(
            Activity.user_id == user_id,
            Activity.strava_id == activity_data['id']
        ).first()
        
        if existing:
            # Update existing activity
            for key, value in self._map_activity_fields(activity_data).items():
                setattr(existing, key, value)
        else:
            # Create new activity
            activity = Activity(
                user_id=user_id,
                **self._map_activity_fields(activity_data)
            )
            self.db.add(activity)
        
        self.db.commit()
    
    def _map_activity_fields(self, data: Dict) -> Dict:
        """Map Strava API fields to database fields"""
        return {
            "strava_id": data['id'],
            "name": data.get('name'),
            "type": data.get('type'),
            "sport_type": data.get('sport_type'),
            "start_date": datetime.fromisoformat(data['start_date'].replace('Z', '+00:00')),
            "start_date_local": datetime.fromisoformat(data['start_date_local'].replace('Z', '+00:00')),
            "moving_time": data.get('moving_time'),
            "elapsed_time": data.get('elapsed_time'),
            "distance": data.get('distance'),
            "total_elevation_gain": data.get('total_elevation_gain'),
            "average_speed": data.get('average_speed'),
            "max_speed": data.get('max_speed'),
            "average_heartrate": data.get('average_heartrate'),
            "max_heartrate": data.get('max_heartrate'),
            "has_heartrate": data.get('has_heartrate', False),
            "average_watts": data.get('average_watts'),
            "weighted_average_watts": data.get('weighted_average_watts'),
            "max_watts": data.get('max_watts'),
            "kilojoules": data.get('kilojoules'),
            "average_cadence": data.get('average_cadence'),
            "suffer_score": data.get('suffer_score'),
            "device_name": data.get('device_name'),
            "gear_id": data.get('gear_id')
        }
