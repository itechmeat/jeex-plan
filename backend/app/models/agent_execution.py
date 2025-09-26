"""
Agent execution audit trail model with multi-tenant support.
Tracks all agent executions for observability and debugging.
"""

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class AgentType(str, Enum):
    """Agent type enumeration for the four-stage workflow."""
    BUSINESS_ANALYST = "business_analyst"
    SOLUTION_ARCHITECT = "solution_architect"
    PROJECT_PLANNER = "project_planner"
    ENGINEERING_STANDARDS = "engineering_standards"


class ExecutionStatus(str, Enum):
    """Agent execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecution(BaseModel):
    """Agent execution audit trail with tenant isolation."""

    __tablename__ = "agent_executions"

    # Agent info
    agent_type = Column(String(50), nullable=False, index=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Execution data
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=True)

    # Status and timing
    status = Column(String(50), default=ExecutionStatus.PENDING.value, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Project relationship
    project_id = Column(UUID(as_uuid=True), nullable=False)
    project = relationship(
        "Project",
        back_populates="agent_executions",
        primaryjoin="and_(AgentExecution.project_id==Project.id, AgentExecution.tenant_id==Project.tenant_id)",
        foreign_keys=[project_id]
    )

    # User who initiated the execution
    initiated_by = Column(UUID(as_uuid=True), nullable=False)

    @property
    def execution_time_ms(self) -> int:
        """Calculate execution time in milliseconds."""
        if self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return 0

    __table_args__ = (
        # Tenant-scoped FK constraint
        ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            ondelete="CASCADE",
        ),
        # Indexes for performance
        Index("idx_agent_executions_project_started", "project_id", "started_at"),
        Index("idx_agent_executions_correlation", "correlation_id"),
        Index("idx_agent_executions_status_started", "status", "started_at"),
        Index("idx_agent_executions_tenant_agent_type", "tenant_id", "agent_type"),
    )
