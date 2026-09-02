#!/usr/bin/env python3
"""
Backfill script to compute derived metrics for existing activities.
Run this once after deploying the computed metrics service.
"""
import sys
import os

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import SessionLocal
from models.activity import Activity
from services.computed_metrics_service import ComputedMetricsService


def backfill_computed_metrics():
    """Compute metrics for all existing activities that don't have them yet"""
    db = SessionLocal()
    
    try:
        # Get all running activities with HR data
        activities = db.query(Activity).filter(
            Activity.type.in_(['Run', 'TrailRun', 'VirtualRun']),
            Activity.has_heartrate == True,
            Activity.average_speed.isnot(None),
            Activity.average_heartrate.isnot(None)
        ).all()
        
        print(f"Found {len(activities)} running activities with HR data")
        
        metrics_service = ComputedMetricsService(db)
        total_metrics = 0
        
        for i, activity in enumerate(activities, 1):
            print(f"Processing activity {i}/{len(activities)}: {activity.name}")
            count = metrics_service.compute_metrics_for_activity(activity.id)
            total_metrics += count
            if count > 0:
                print(f"  → Computed {count} metrics")
        
        print(f"\nDone! Computed {total_metrics} total metrics for {len(activities)} activities")
        
    finally:
        db.close()


if __name__ == "__main__":
    backfill_computed_metrics()
