"""add auth fields: password_hash, token_version on users; refresh_tokens table

Revision ID: 005_add_auth_fields
Revises: 004_add_sync_states
Create Date: 2026-11-06
"""
from alembic import op
import sqlalchemy as sa

revision = "005_add_auth_fields"
down_revision = "004_add_sync_states"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("password_hash", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])


def downgrade():
    op.drop_table("refresh_tokens")
    op.drop_column("users", "token_version")
    op.drop_column("users", "password_hash")
