"""Remove redundant tenant slug/is_active index

Revision ID: 2c4a355c7c2a
Revises: 0aad7c4f25d0
Create Date: 2025-09-23 10:15:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2c4a355c7c2a"
down_revision: str | Sequence[str] | None = "0aad7c4f25d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop redundant composite index on tenants."""
    op.execute("DROP INDEX IF EXISTS idx_tenant_slug_active")


def downgrade() -> None:
    """Recreate composite index on tenants."""
    op.create_index(
        "idx_tenant_slug_active",
        "tenants",
        ["slug", "is_active"],
    )
