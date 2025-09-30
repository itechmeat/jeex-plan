"""update_agent_execution_enum_native

Revision ID: a1b2c3d4e5f6
Revises: 2c4a355c7c2a
Create Date: 2025-09-30 13:35:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "2c4a355c7c2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - convert agent_executions.status to native enum."""
    # Drop existing enum type constraint
    op.execute(
        "ALTER TABLE agent_executions DROP CONSTRAINT IF EXISTS agentexecutionsstatus_check"
    )

    # Convert column to native PostgreSQL enum
    op.execute(
        """
        ALTER TABLE agent_executions
        ALTER COLUMN status TYPE VARCHAR(50)
    """
    )

    # Create native enum type
    op.execute(
        """
        CREATE TYPE agentexecutionstatus AS ENUM (
            'pending', 'running', 'completed', 'failed', 'cancelled'
        )
    """
    )

    # Convert column to native enum type
    op.execute(
        """
        ALTER TABLE agent_executions
        ALTER COLUMN status TYPE agentexecutionstatus
        USING status::agentexecutionstatus
    """
    )


def downgrade() -> None:
    """Downgrade schema - convert back to regular enum."""
    # Convert back to regular enum
    op.execute(
        """
        ALTER TABLE agent_executions
        ALTER COLUMN status TYPE VARCHAR(50)
    """
    )

    # Drop native enum type
    op.execute("DROP TYPE IF EXISTS agentexecutionstatus")

    # Add check constraint
    op.execute(
        """
        ALTER TABLE agent_executions
        ADD CONSTRAINT agentexecutionsstatus_check
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
    """
    )
