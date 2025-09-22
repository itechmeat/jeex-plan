"""Add RBAC models and update user authentication

Revision ID: 003
Revises: 002
Create Date: 2025-09-22 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, Sequence[str], None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add RBAC models and update user authentication fields."""

    # Add new fields to users table for authentication
    op.add_column('users', sa.Column('hashed_password', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))

    # Create permissions table
    op.create_table('permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_permission_tenant_name')
    )

    # Create roles table
    op.create_table('roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_role_tenant_name')
    )

    # Create role_permissions association table
    op.create_table('role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # Create project_members table
    op.create_table('project_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invited_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'project_id', 'user_id', name='uq_project_member_tenant_project_user')
    )

    # Create indexes for performance
    op.create_index('ix_permissions_id', 'permissions', ['id'])
    op.create_index('ix_permissions_tenant_id', 'permissions', ['tenant_id'])
    op.create_index('ix_permissions_is_deleted', 'permissions', ['is_deleted'])
    op.create_index('ix_permissions_resource_type', 'permissions', ['resource_type'])
    op.create_index('ix_permissions_name', 'permissions', ['name'])

    op.create_index('ix_roles_id', 'roles', ['id'])
    op.create_index('ix_roles_tenant_id', 'roles', ['tenant_id'])
    op.create_index('ix_roles_is_deleted', 'roles', ['is_deleted'])
    op.create_index('ix_roles_name', 'roles', ['name'])
    op.create_index('ix_roles_is_active', 'roles', ['is_active'])

    op.create_index('ix_project_members_id', 'project_members', ['id'])
    op.create_index('ix_project_members_tenant_id', 'project_members', ['tenant_id'])
    op.create_index('ix_project_members_is_deleted', 'project_members', ['is_deleted'])
    op.create_index('ix_project_members_project_id', 'project_members', ['project_id'])
    op.create_index('ix_project_members_user_id', 'project_members', ['user_id'])
    op.create_index('ix_project_members_role_id', 'project_members', ['role_id'])
    op.create_index('ix_project_members_is_active', 'project_members', ['is_active'])

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
        )
    """)


def downgrade() -> None:
    """Remove RBAC models and user authentication updates."""

    # Drop check constraints
    op.execute("ALTER TABLE permissions DROP CONSTRAINT IF EXISTS ck_permissions_resource_type_valid")
    op.execute("ALTER TABLE permissions DROP CONSTRAINT IF EXISTS ck_permissions_action_valid")
    op.execute("ALTER TABLE roles DROP CONSTRAINT IF EXISTS ck_roles_name_valid")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_auth_method")

    # Drop performance indexes
    op.execute("DROP INDEX IF EXISTS ix_project_members_user_project_active")
    op.execute("DROP INDEX IF EXISTS ix_project_members_project_active")
    op.execute("DROP INDEX IF EXISTS ix_roles_tenant_active")
    op.execute("DROP INDEX IF EXISTS ix_permissions_tenant_resource")

    # Drop tables in reverse order (due to foreign keys)
    op.drop_table('project_members')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')

    # Remove columns from users table
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'hashed_password')