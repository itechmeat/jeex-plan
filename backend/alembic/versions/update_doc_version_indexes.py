"""Update document version unique indexes to exclude soft-deleted records

Revision ID: update_doc_version_indexes
Revises: 1234567890ab
Create Date: 2024-09-24 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'abcdef123456'
down_revision = '1234567890ab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing unique indexes
    op.drop_index('uq_document_version_tenant_project_type_version', table_name='document_versions')
    op.drop_index('uq_document_version_tenant_project_epic_version', table_name='document_versions')

    # Recreate unique indexes with soft-delete exclusion
    op.create_index(
        'uq_document_version_tenant_project_type_version',
        'document_versions',
        ['tenant_id', 'project_id', 'document_type', 'version'],
        unique=True,
        postgresql_where=sa.text('epic_number IS NULL AND is_deleted = false')
    )
    op.create_index(
        'uq_document_version_tenant_project_epic_version',
        'document_versions',
        ['tenant_id', 'project_id', 'epic_number', 'version'],
        unique=True,
        postgresql_where=sa.text("epic_number IS NOT NULL AND document_type = 'plan_epic' AND is_deleted = false")
    )


def downgrade() -> None:
    # Drop updated indexes
    op.drop_index('uq_document_version_tenant_project_type_version', table_name='document_versions')
    op.drop_index('uq_document_version_tenant_project_epic_version', table_name='document_versions')

    # Recreate original indexes without soft-delete exclusion
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