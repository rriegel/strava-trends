"""Scope routes and route_clusters to users.

The routes feature was single-user: routes were matched globally by
polyline_hash (exact) + fuzzy start-point match, with no user_id column.
With multi-user auth in place, routes must be per-user:

- Two users running the same route each get their own route row (with their
  own activity_count rollup), so the denormalized count is "my runs on this
  route" and route polylines (location data) don't leak across users.
- polyline_hash uniqueness becomes per-user: (user_id, polyline_hash).

Revision ID: 006_user_scoped_routes
Revises: 005_add_auth_fields
Create Date: 2026-11-08
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "006_user_scoped_routes"
down_revision = "005_add_auth_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add user_id columns (nullable first, so the backfill can run).
    op.add_column(
        "routes",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
    )
    op.add_column(
        "route_clusters",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
    )

    # 2. Backfill: routes inherit the user_id of their linked activities.
    #    A route is only ever linked to activities of one user after this
    #    migration (see the orphan cleanup below), so any linked activity's
    #    owner is the route's owner.
    op.execute(
        """
        UPDATE routes r
        SET user_id = a.user_id
        FROM activities a
        WHERE a.route_id = r.id
        """
    )

    # 3. Orphan routes (no linked activities — e.g. a route whose activities
    #    were deleted) have no owner: delete them.
    op.execute(
        """
        DELETE FROM routes r
        WHERE r.user_id IS NULL
        """
    )

    # 4. Same for clusters: re-derive from their (now-owned) routes; delete
    #    clusters with no owned routes.
    op.execute(
        """
        UPDATE route_clusters c
        SET user_id = r.user_id
        FROM routes r
        WHERE r.cluster_id = c.id
          AND r.user_id IS NOT NULL
        """
    )
    op.execute(
        """
        DELETE FROM route_clusters c
        WHERE c.user_id IS NULL
          AND NOT EXISTS (SELECT 1 FROM routes r WHERE r.cluster_id = c.id)
        """
    )

    # 5. Enforce NOT NULL now that the backfill is done.
    op.alter_column("routes", "user_id", nullable=False)
    op.alter_column("route_clusters", "user_id", nullable=False)

    # 6. Per-user hash uniqueness (was: global unique on polyline_hash).
    #    SQLAlchemy's unique=True on the column created a unique *index*
    #    (ix_routes_polyline_hash), not a named unique constraint.
    op.drop_index("ix_routes_polyline_hash", "routes")
    op.create_unique_constraint(
        "uq_routes_user_polyline_hash",
        "routes",
        ["user_id", "polyline_hash"],
    )
    op.create_index("ix_routes_user_id", "routes", ["user_id"])
    op.create_index("ix_route_clusters_user_id", "route_clusters", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_route_clusters_user_id", "route_clusters")
    op.drop_index("ix_routes_user_id", "routes")
    op.drop_constraint("uq_routes_user_polyline_hash", "routes", type_="unique")
    op.create_index("ix_routes_polyline_hash", "routes", ["polyline_hash"], unique=True)
    op.drop_column("route_clusters", "user_id")
    op.drop_column("routes", "user_id")
