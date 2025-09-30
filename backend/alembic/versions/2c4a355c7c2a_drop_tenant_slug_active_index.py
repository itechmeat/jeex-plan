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
    """Drop redundant partial index on tenants."""
    op.drop_index(
        "ix_tenants_slug_active",
        table_name="tenants",
        if_exists=True,
    )


def downgrade() -> None:
    """Recreate original partial index on tenants."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tenants_slug_active "
        "ON tenants(slug) WHERE is_active = true"
    )
