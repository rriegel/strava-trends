"""add max_hr to users

Revision ID: 002_add_max_hr
Revises: 001_initial
Create Date: 2026-08-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_max_hr'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('max_hr', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'max_hr')
