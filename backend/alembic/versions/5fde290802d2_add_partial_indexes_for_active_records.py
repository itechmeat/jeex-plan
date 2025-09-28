"""Add partial indexes for active records

Revision ID: 5fde290802d2
Revises: 001
Create Date: 2025-09-21 23:14:00.397471

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5fde290802d2"
down_revision: str | Sequence[str] | None = "9e95af11ace6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add partial indexes for active records optimization."""

    # Partial indexes for active records only (is_deleted = false)
    # These indexes will be much smaller and more efficient
    # for queries on active records

    # Users - active users by tenant
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_tenant_active "
        "ON users(tenant_id) WHERE is_deleted = false"
    )

    # Users - active users by email (for login lookups)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_email_active "
        "ON users(email) WHERE is_deleted = false"
    )

    # Users - active users by tenant and email (compound lookup)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_tenant_email_active "
        "ON users(tenant_id, email) WHERE is_deleted = false"
    )

    # Projects - active projects by tenant
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_projects_tenant_active "
        "ON projects(tenant_id) WHERE is_deleted = false"
    )

    # Projects - active projects by tenant and status
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_projects_tenant_status_active "
        "ON projects(tenant_id, status) WHERE is_deleted = false"
    )

    # Projects - active projects by owner
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_projects_owner_active "
        "ON projects(owner_id) WHERE is_deleted = false"
    )

    # Documents - active documents by tenant
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_tenant_active "
        "ON documents(tenant_id) WHERE is_deleted = false"
    )

    # Documents - active documents by project
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_project_active "
        "ON documents(project_id) WHERE is_deleted = false"
    )

    # Documents - active documents by tenant and status
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_tenant_status_active "
        "ON documents(tenant_id, status) WHERE is_deleted = false"
    )

    # Documents - active documents by project and type
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_project_type_active "
        "ON documents(project_id, document_type) WHERE is_deleted = false"
    )

    # Tenants - active tenants by slug for efficient lookups
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tenants_slug_active "
        "ON tenants(slug) WHERE is_active = true"
    )


def downgrade() -> None:
    """Remove partial indexes for active records."""

    # Drop all partial indexes
    op.execute("DROP INDEX IF EXISTS ix_users_tenant_active")
    op.execute("DROP INDEX IF EXISTS ix_users_email_active")
    op.execute("DROP INDEX IF EXISTS ix_users_tenant_email_active")
    op.execute("DROP INDEX IF EXISTS ix_projects_tenant_active")
    op.execute("DROP INDEX IF EXISTS ix_projects_tenant_status_active")
    op.execute("DROP INDEX IF EXISTS ix_projects_owner_active")
    op.execute("DROP INDEX IF EXISTS ix_documents_tenant_active")
    op.execute("DROP INDEX IF EXISTS ix_documents_project_active")
    op.execute("DROP INDEX IF EXISTS ix_documents_tenant_status_active")
    op.execute("DROP INDEX IF EXISTS ix_documents_project_type_active")
    op.execute("DROP INDEX IF EXISTS ix_tenants_slug_active")
