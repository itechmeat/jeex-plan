"""Agent execution audit trail model with multi-tenant support."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKeyConstraint, Index, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .project import Project


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
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Execution data
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Status and timing
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus, name="agentexecutionstatus", native_enum=False),
        default=ExecutionStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Project relationship
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="agent_executions",
        primaryjoin="and_(AgentExecution.project_id==Project.id, AgentExecution.tenant_id==Project.tenant_id)",
        foreign_keys=lambda: [AgentExecution.project_id, AgentExecution.tenant_id],
    )

    # User who initiated the execution
    initiated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

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
