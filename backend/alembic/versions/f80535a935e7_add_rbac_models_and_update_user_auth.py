"""Add RBAC models and update user authentication

Revision ID: f80535a935e7
Revises: cbe2ed1ce948
Create Date: 2025-09-22 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f80535a935e7"
down_revision: str | Sequence[str] | None = "cbe2ed1ce948"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add RBAC models and update user authentication fields."""

    # Note: hashed_password and last_login_at fields already exist in the User model

    # Create permissions table
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column(
            "is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_permission_tenant_name"),
    )

    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )

    # Create unique indexes for composite foreign key references (must be before association tables)
    op.create_index(
        "ix_roles_tenant_id_unique", "roles", ["tenant_id", "id"], unique=True
    )
    op.create_index(
        "ix_permissions_tenant_id_unique",
        "permissions",
        ["tenant_id", "id"],
        unique=True,
    )
    op.create_index(
        "ix_users_tenant_id_unique", "users", ["tenant_id", "id"], unique=True
    )
    op.create_index(
        "ix_projects_tenant_id_unique", "projects", ["tenant_id", "id"], unique=True
    )

    # Create role_permissions association table
    op.create_table(
        "role_permissions",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "role_id"],
            ["roles.tenant_id", "roles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "permission_id"],
            ["permissions.tenant_id", "permissions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tenant_id", "role_id", "permission_id"),
    )

    # Create project_members table
    op.create_table(
        "project_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "project_id"],
            ["projects.tenant_id", "projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["users.tenant_id", "users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "role_id"],
            ["roles.tenant_id", "roles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "invited_by_id"], ["users.tenant_id", "users.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "project_id",
            "user_id",
            name="uq_project_member_tenant_project_user",
        ),
    )

    # Create indexes for performance
    op.create_index("ix_permissions_tenant_id", "permissions", ["tenant_id"])
    op.create_index("ix_permissions_is_deleted", "permissions", ["is_deleted"])
    op.create_index("ix_permissions_resource_type", "permissions", ["resource_type"])
    op.create_index("ix_permissions_name", "permissions", ["name"])

    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"])
    op.create_index("ix_roles_is_deleted", "roles", ["is_deleted"])
    op.create_index("ix_roles_name", "roles", ["name"])
    op.create_index("ix_roles_is_active", "roles", ["is_active"])

    op.create_index("ix_project_members_tenant_id", "project_members", ["tenant_id"])
    op.create_index("ix_project_members_is_deleted", "project_members", ["is_deleted"])
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])
    op.create_index("ix_project_members_role_id", "project_members", ["role_id"])
    op.create_index("ix_project_members_is_active", "project_members", ["is_active"])

    # Create performance indexes for RBAC queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_project_members_user_project_active
        ON project_members(user_id, project_id, is_active)
        WHERE is_deleted = false
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_project_members_project_active
        ON project_members(project_id, is_active)
        WHERE is_deleted = false
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_roles_tenant_active
        ON roles(tenant_id, is_active)
        WHERE is_deleted = false
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_permissions_tenant_resource
        ON permissions(tenant_id, resource_type)
        WHERE is_deleted = false
    """)

    # Add check constraints for RBAC validation
    op.execute("""
        ALTER TABLE permissions
        ADD CONSTRAINT ck_permissions_resource_type_valid
        CHECK (resource_type IN ('project', 'document', 'agent', 'analytics', 'export'))
    """)

    op.execute("""
        ALTER TABLE permissions
        ADD CONSTRAINT ck_permissions_action_valid
        CHECK (action IN ('read', 'write', 'delete', 'admin', 'execute', 'documents'))
    """)

    op.execute("""
        ALTER TABLE roles
        ADD CONSTRAINT ck_roles_name_valid
        CHECK (name IN ('OWNER', 'EDITOR', 'VIEWER') OR is_system = false)
    """)

    # Add authentication password constraints
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT ck_users_auth_method
        CHECK (
            (hashed_password IS NOT NULL) OR
            (oauth_provider IS NOT NULL AND oauth_id IS NOT NULL)
        ) NOT VALID
    """)

    # Backfill legacy rows without any authentication method
    op.execute("""
        UPDATE users
        SET is_active = false
        WHERE hashed_password IS NULL
          AND (oauth_provider IS NULL OR oauth_id IS NULL)
    """)

    op.execute("ALTER TABLE users VALIDATE CONSTRAINT ck_users_auth_method")


def downgrade() -> None:
    """Remove RBAC models and user authentication updates."""

    # Drop check constraints
    op.execute(
        "ALTER TABLE permissions DROP CONSTRAINT IF EXISTS ck_permissions_resource_type_valid"
    )
    op.execute(
        "ALTER TABLE permissions DROP CONSTRAINT IF EXISTS ck_permissions_action_valid"
    )
    op.execute("ALTER TABLE roles DROP CONSTRAINT IF EXISTS ck_roles_name_valid")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_auth_method")

    # Drop performance indexes
    op.execute("DROP INDEX IF EXISTS ix_project_members_user_project_active")
    op.execute("DROP INDEX IF EXISTS ix_project_members_project_active")
    op.execute("DROP INDEX IF EXISTS ix_roles_tenant_active")
    op.execute("DROP INDEX IF EXISTS ix_permissions_tenant_resource")

    # Drop unique composite indexes for foreign keys
    op.drop_index("ix_roles_tenant_id_unique", "roles")
    op.drop_index("ix_permissions_tenant_id_unique", "permissions")
    op.drop_index("ix_users_tenant_id_unique", "users")
    op.drop_index("ix_projects_tenant_id_unique", "projects")

    # Drop tables in reverse order (due to foreign keys)
    op.drop_table("project_members")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")

    # Note: hashed_password and last_login_at fields are part of User model, not dropped
