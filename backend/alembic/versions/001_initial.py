"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-08-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('strava_athlete_id', sa.BigInteger(), unique=True, nullable=False, index=True),
        sa.Column('username', sa.String(100), unique=True, nullable=True),
        sa.Column('firstname', sa.String(100)),
        sa.Column('lastname', sa.String(100)),
        sa.Column('email', sa.String(255), unique=True, nullable=True),
        sa.Column('profile_url', sa.String(500)),
        sa.Column('city', sa.String(100)),
        sa.Column('state', sa.String(100)),
        sa.Column('country', sa.String(100)),
        sa.Column('access_token', sa.String(500), nullable=False),
        sa.Column('refresh_token', sa.String(500), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime()),
        sa.Column('last_synced_activity_id', sa.BigInteger()),
        sa.Column('sync_status', sa.String(20), server_default='idle'),
        sa.Column('default_distance_unit', sa.String(10), server_default='metric'),
        sa.Column('preferred_hr_zones', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Route clusters table (without FK to routes — circular dependency)
    op.create_table(
        'route_clusters',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('centroid_route_id', sa.BigInteger(), index=True),
        sa.Column('route_count', sa.BigInteger(), server_default='0'),
        sa.Column('avg_distance', sa.Numeric(10, 2)),
        sa.Column('avg_elevation_gain', sa.Numeric(10, 2)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Routes table (references route_clusters)
    op.create_table(
        'routes',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('name', sa.String(255)),
        sa.Column('polyline', sa.Text()),
        sa.Column('polyline_hash', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('distance', sa.Numeric(10, 2)),
        sa.Column('elevation_gain', sa.Numeric(10, 2)),
        sa.Column('start_lat', sa.Numeric(9, 6)),
        sa.Column('start_lng', sa.Numeric(9, 6)),
        sa.Column('end_lat', sa.Numeric(9, 6)),
        sa.Column('end_lng', sa.Numeric(9, 6)),
        sa.Column('cluster_id', sa.BigInteger(), sa.ForeignKey('route_clusters.id', ondelete='SET NULL'), index=True),
        sa.Column('activity_count', sa.BigInteger(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Now add the deferred FK from route_clusters -> routes
    op.create_foreign_key(
        'fk_route_clusters_centroid_route_id',
        'route_clusters', 'routes',
        ['centroid_route_id'], ['id'],
        ondelete='SET NULL'
    )

    # Activities table
    op.create_table(
        'activities',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strava_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('sport_type', sa.String(50)),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('start_date_local', sa.DateTime(timezone=True), nullable=False),
        sa.Column('moving_time', sa.BigInteger()),
        sa.Column('elapsed_time', sa.BigInteger()),
        sa.Column('distance', sa.Numeric(10, 2)),
        sa.Column('total_elevation_gain', sa.Numeric(10, 2)),
        sa.Column('average_speed', sa.Numeric(6, 3)),
        sa.Column('max_speed', sa.Numeric(6, 3)),
        sa.Column('average_heartrate', sa.Numeric(5, 1)),
        sa.Column('max_heartrate', sa.Numeric(5, 1)),
        sa.Column('has_heartrate', sa.Boolean(), server_default='false'),
        sa.Column('average_watts', sa.Numeric(7, 1)),
        sa.Column('weighted_average_watts', sa.Numeric(7, 1)),
        sa.Column('max_watts', sa.Numeric(7, 1)),
        sa.Column('kilojoules', sa.Numeric(10, 2)),
        sa.Column('average_cadence', sa.Numeric(5, 1)),
        sa.Column('suffer_score', sa.Numeric(5, 1)),
        sa.Column('device_name', sa.String(255)),
        sa.Column('gear_id', sa.String(50)),
        sa.Column('distance_bucket', sa.String(20)),
        sa.Column('effort_zone', sa.String(20)),
        sa.Column('terrain_type', sa.String(20)),
        sa.Column('route_id', sa.BigInteger(), sa.ForeignKey('routes.id', ondelete='SET NULL'), index=True),
        sa.Column('has_streams', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'strava_id', name='uq_activities_user_strava'),
    )
    op.create_index('ix_activities_user_id_type_start_date', 'activities', ['user_id', 'type', 'start_date'])
    op.create_index('ix_activities_user_id_start_date_local', 'activities', ['user_id', 'start_date_local'])
    op.create_index('ix_activities_user_id_distance_bucket', 'activities', ['user_id', 'distance_bucket'])
    op.create_index('ix_activities_user_id_effort_zone', 'activities', ['user_id', 'effort_zone'])
    op.create_index('ix_activities_user_id_route_id', 'activities', ['user_id', 'route_id'])

    # Activity streams table
    op.create_table(
        'activity_streams',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activity_id', sa.BigInteger(), sa.ForeignKey('activities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stream_type', sa.String(50), nullable=False),
        sa.Column('data', postgresql.JSONB(), nullable=False),
        sa.Column('series_type', sa.String(20), server_default='time'),
        sa.Column('original_size', sa.BigInteger()),
        sa.Column('resolution', sa.String(20)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'activity_id', 'stream_type', name='uq_streams_user_activity_type'),
    )
    op.create_index('ix_activity_streams_user_id_activity_id', 'activity_streams', ['user_id', 'activity_id'])

    # Computed metrics table
    op.create_table(
        'computed_metrics',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activity_id', sa.BigInteger(), sa.ForeignKey('activities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('value', sa.Numeric(10, 4), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'activity_id', 'metric_type', name='uq_metrics_user_activity_type'),
    )
    op.create_index('ix_computed_metrics_user_id_metric_type', 'computed_metrics', ['user_id', 'metric_type'])

    # Effort groups table
    op.create_table(
        'effort_groups',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activity_id', sa.BigInteger(), sa.ForeignKey('activities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('group_type', sa.String(30), nullable=False),
        sa.Column('group_label', sa.String(50), nullable=False),
        sa.Column('group_value', sa.BigInteger()),
        sa.Column('time_in_zone', sa.BigInteger()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'activity_id', 'group_type', 'group_label', name='uq_effort_groups_user_activity_group'),
    )
    op.create_index('ix_effort_groups_user_id_group_type', 'effort_groups', ['user_id', 'group_type'])


def downgrade() -> None:
    op.drop_table('effort_groups')
    op.drop_table('computed_metrics')
    op.drop_table('activity_streams')
    op.drop_table('activities')
    op.drop_table('routes')
    op.drop_table('route_clusters')
    op.drop_table('users')
