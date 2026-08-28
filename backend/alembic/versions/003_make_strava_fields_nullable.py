"""Make Strava fields nullable for non-Strava users

Revision ID: 003
Revises: 002
Create Date: 2026-01-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_make_strava_fields_nullable'
down_revision = '002_add_max_hr'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make Strava-specific fields nullable for users who don't use Strava OAuth
    op.alter_column('users', 'strava_athlete_id',
                    existing_type=sa.BigInteger(),
                    nullable=True)
    op.alter_column('users', 'access_token',
                    existing_type=sa.String(500),
                    nullable=True)
    op.alter_column('users', 'refresh_token',
                    existing_type=sa.String(500),
                    nullable=True)
    op.alter_column('users', 'token_expires_at',
                    existing_type=sa.DateTime(),
                    nullable=True)


def downgrade() -> None:
    # Revert to NOT NULL if we ever go back to Strava-only auth
    op.alter_column('users', 'token_expires_at',
                    existing_type=sa.DateTime(),
                    nullable=False)
    op.alter_column('users', 'refresh_token',
                    existing_type=sa.String(500),
                    nullable=False)
    op.alter_column('users', 'access_token',
                    existing_type=sa.String(500),
                    nullable=False)
    op.alter_column('users', 'strava_athlete_id',
                    existing_type=sa.BigInteger(),
                    nullable=False)
