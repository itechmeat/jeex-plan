"""Add authentication constraints and indexes

Revision ID: 002
Revises: 5fde290802d2
Create Date: 2025-09-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, Sequence[str], None] = '5fde290802d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add authentication constraints and specialized indexes."""

    # Add check constraints for enum validation
    op.execute("""
        ALTER TABLE projects
        ADD CONSTRAINT ck_projects_status_valid
        CHECK (status IN ('DRAFT', 'IN_PROGRESS', 'COMPLETED', 'ARCHIVED'))
    """)

    op.execute("""
        ALTER TABLE documents
        ADD CONSTRAINT ck_documents_type_valid
        CHECK (document_type IN ('ARCHITECTURE', 'PLANNING', 'STANDARDS', 'TECHNICAL_SPEC'))
    """)

    op.execute("""
        ALTER TABLE documents
        ADD CONSTRAINT ck_documents_status_valid
        CHECK (status IN ('PENDING', 'GENERATING', 'COMPLETED', 'FAILED'))
    """)

    # Add OAuth constraint validation
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT ck_users_oauth_complete
        CHECK (
            (oauth_provider IS NULL AND oauth_id IS NULL) OR
            (oauth_provider IS NOT NULL AND oauth_id IS NOT NULL)
        )
    """)

    # Add check constraint for oauth_provider values
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT ck_users_oauth_provider_valid
        CHECK (
            oauth_provider IS NULL OR
            oauth_provider IN ('google', 'github', 'microsoft', 'gitlab')
        )
    """)

    # Add authentication-specific indexes for OAuth operations
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_oauth_provider_id
        ON users(oauth_provider, oauth_id)
        WHERE oauth_provider IS NOT NULL AND oauth_id IS NOT NULL
    """)

    # Add index for tenant + OAuth lookup (for preventing OAuth duplicate registrations)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_tenant_oauth
        ON users(tenant_id, oauth_provider, oauth_id)
        WHERE oauth_provider IS NOT NULL AND oauth_id IS NOT NULL AND is_deleted = false
    """)

    # Add unique constraint for OAuth per tenant (prevent duplicate OAuth accounts)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_users_tenant_oauth_unique
        ON users(tenant_id, oauth_provider, oauth_id)
        WHERE oauth_provider IS NOT NULL AND oauth_id IS NOT NULL AND is_deleted = false
    """)

    # Add index for email-based authentication lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_email_login
        ON users(email, is_active)
        WHERE is_deleted = false
    """)

    # Add index for username-based authentication lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_username_login
        ON users(username, is_active)
        WHERE is_deleted = false
    """)

    # Add composite index for tenant + email authentication
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_tenant_email_login
        ON users(tenant_id, email, is_active)
        WHERE is_deleted = false
    """)

    # Add composite index for tenant + username authentication
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_tenant_username_login
        ON users(tenant_id, username, is_active)
        WHERE is_deleted = false
    """)

    # Add index for superuser queries (useful for admin operations)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_tenant_superuser
        ON users(tenant_id, is_superuser)
        WHERE is_superuser = true AND is_deleted = false
    """)

    # Add check constraints for data validation
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT ck_users_email_format
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$')
    """)

    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT ck_users_username_length
        CHECK (length(username) >= 3)
    """)

    op.execute("""
        ALTER TABLE documents
        ADD CONSTRAINT ck_documents_generation_progress
        CHECK (generation_progress >= 0 AND generation_progress <= 100)
    """)

    op.execute("""
        ALTER TABLE documents
        ADD CONSTRAINT ck_documents_generation_step
        CHECK (generation_step >= 1 AND generation_step <= 4)
    """)


def downgrade() -> None:
    """Remove authentication constraints and indexes."""

    # Drop check constraints
    op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS ck_projects_status_valid")
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS ck_documents_type_valid")
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS ck_documents_status_valid")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_oauth_complete")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_oauth_provider_valid")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_email_format")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_username_length")
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS ck_documents_generation_progress")
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS ck_documents_generation_step")

    # Drop authentication indexes
    op.execute("DROP INDEX IF EXISTS ix_users_oauth_provider_id")
    op.execute("DROP INDEX IF EXISTS ix_users_tenant_oauth")
    op.execute("DROP INDEX IF EXISTS uq_users_tenant_oauth_unique")
    op.execute("DROP INDEX IF EXISTS ix_users_email_login")
    op.execute("DROP INDEX IF EXISTS ix_users_username_login")
    op.execute("DROP INDEX IF EXISTS ix_users_tenant_email_login")
    op.execute("DROP INDEX IF EXISTS ix_users_tenant_username_login")
    op.execute("DROP INDEX IF EXISTS ix_users_tenant_superuser")