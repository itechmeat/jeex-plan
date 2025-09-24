"""Add document generation models

Revision ID: 1234567890ab
Revises: f80535a935e7
Create Date: 2024-09-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = 'f80535a935e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create document_versions table
    op.create_table('document_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('epic_number', sa.Integer(), nullable=True),
        sa.Column('epic_name', sa.String(length=255), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by', 'tenant_id'], ['users.id', 'users.tenant_id'], ondelete='RESTRICT')
    )

    # Create indexes for document_versions
    op.create_index('idx_document_versions_project_type', 'document_versions', ['project_id', 'document_type'])
    op.create_index('idx_document_versions_project_version', 'document_versions', ['project_id', 'version'])
    op.create_index('idx_document_versions_tenant_created', 'document_versions', ['tenant_id', 'created_at'])
    op.create_index('idx_document_versions_epic', 'document_versions', ['project_id', 'epic_number'])
    op.create_index('idx_document_versions_tenant_id', 'document_versions', ['tenant_id'])
    op.create_index('idx_document_versions_is_deleted', 'document_versions', ['is_deleted'])
    op.create_index(
        'uq_document_version_tenant_project_type_version',
        'document_versions',
        ['tenant_id', 'project_id', 'document_type', 'version'],
        unique=True,
        postgresql_where=sa.text('epic_number IS NULL')
    )
    op.create_index(
        'uq_document_version_tenant_project_epic_version',
        'document_versions',
        ['tenant_id', 'project_id', 'epic_number', 'version'],
        unique=True,
        postgresql_where=sa.text("epic_number IS NOT NULL AND document_type = 'plan_epic'")
    )

    # Create agent_executions table
    op.create_table('agent_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('input_data', postgresql.JSON(), nullable=False),
        sa.Column('output_data', postgresql.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('initiated_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )

    # Create indexes for agent_executions
    op.create_index('idx_agent_executions_project_started', 'agent_executions', ['project_id', 'started_at'])
    op.create_index('idx_agent_executions_correlation', 'agent_executions', ['correlation_id'])
    op.create_index('idx_agent_executions_status_started', 'agent_executions', ['status', 'started_at'])
    op.create_index('idx_agent_executions_tenant_agent_type', 'agent_executions', ['tenant_id', 'agent_type'])
    op.create_index('idx_agent_executions_tenant_id', 'agent_executions', ['tenant_id'])
    op.create_index('idx_agent_executions_is_deleted', 'agent_executions', ['is_deleted'])
    op.create_index('idx_agent_executions_agent_type', 'agent_executions', ['agent_type'])
    op.create_index('idx_agent_executions_status', 'agent_executions', ['status'])

    # Create exports table
    op.create_table('exports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('manifest', postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(now() + interval '24 hours')")),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )

    # Create indexes for exports
    op.create_index('idx_exports_project', 'exports', ['project_id'])
    op.create_index('idx_exports_expires', 'exports', ['expires_at'])
    op.create_index('idx_exports_status', 'exports', ['status'])
    op.create_index('idx_exports_tenant_created', 'exports', ['tenant_id', 'created_at'])
    op.create_index('idx_exports_tenant_id', 'exports', ['tenant_id'])
    op.create_index('idx_exports_is_deleted', 'exports', ['is_deleted'])


def downgrade() -> None:
    # Drop exports table
    op.drop_table('exports')

    # Drop agent_executions table
    op.drop_table('agent_executions')

    # Drop document_versions table
    op.drop_table('document_versions')
