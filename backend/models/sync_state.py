from sqlalchemy import Column, BigInteger, DateTime, String, ForeignKeyConstraint
from sqlalchemy.sql import func
from database import Base


class SyncState(Base):
    """Per-user sync cursors for external services (one row per source)."""

    __tablename__ = "sync_states"

    user_id = Column(BigInteger, primary_key=True)
    source = Column(String(50), primary_key=True)  # 'garmin', 'strava', ...

    # Incremental cursor: newest activity start time successfully synced.
    last_synced_activity_start = Column(DateTime, nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
    )

    @classmethod
    def for_user(cls, db, user_id: int, source: str = "garmin") -> "SyncState":
        """Fetch or create (uncommitted) the sync-state row for user+source."""
        row = (
            db.query(cls)
            .filter(cls.user_id == user_id, cls.source == source)
            .first()
        )
        if row is None:
            row = cls(user_id=user_id, source=source)
            db.add(row)
            db.flush()
        return row
