"""add sync_states table

Revision ID: 004_add_sync_states
Revises: 003_make_strava_fields_nullable
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "004_add_sync_states"
down_revision = "003_make_strava_fields_nullable"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sync_states",
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column("source", sa.String(length=50), primary_key=True),
        sa.Column("last_synced_activity_start", sa.DateTime(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_sync_states_user_id", "sync_states", ["user_id"]
    )


def downgrade():
    op.drop_table("sync_states")
