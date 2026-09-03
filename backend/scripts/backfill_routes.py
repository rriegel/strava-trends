#!/usr/bin/env python3
"""
One-shot backfill: build Route rows from existing activities' latlng
streams. Run this once after deploying the route service.

Usage (from backend/, with the venv active):
    python scripts/backfill_routes.py

Idempotent — safe to run repeatedly. Activities already linked to a
route are counted as matched, not re-processed.
"""
import sys
import os

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import SessionLocal
from services.route_service import backfill_routes


def backfill():
    db = SessionLocal()
    try:
        stats = backfill_routes(db)
        print("Route backfill complete:")
        print(f"  activities scanned : {stats['activities_scanned']}")
        print(f"  routes created     : {stats['routes_created']}")
        print(f"  routes matched     : {stats['routes_matched']}")
        print(f"  skipped (no track) : {stats['skipped']}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill()
