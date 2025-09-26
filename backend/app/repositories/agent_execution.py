"""
Agent execution repository with tenant isolation.
Handles audit trail for agent executions in the document generation workflow.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.agent_execution import AgentExecution, AgentType, ExecutionStatus
from app.repositories.base import TenantRepository

logger = get_logger()


class AgentExecutionRepository(TenantRepository[AgentExecution]):
    """Repository for agent executions with tenant isolation."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, AgentExecution, tenant_id)

    async def start_execution(
        self,
        project_id: UUID,
        agent_type: AgentType,
        correlation_id: UUID,
        input_data: dict[str, Any],
        initiated_by: UUID,
    ) -> AgentExecution:
        """Start a new agent execution."""
        return await self.create(
            project_id=project_id,
            agent_type=agent_type.value,
            correlation_id=correlation_id,
            input_data=input_data,
            status=ExecutionStatus.RUNNING.value,
            initiated_by=initiated_by,
            started_at=datetime.now(UTC),
        )

    async def complete_execution(
        self, execution_id: UUID, output_data: dict[str, Any]
    ) -> AgentExecution | None:
        """Mark execution as completed with output data."""
        return await self.update(
            execution_id,
            status=ExecutionStatus.COMPLETED.value,
            output_data=output_data,
            completed_at=datetime.now(UTC),
        )

    async def fail_execution(
        self, execution_id: UUID, error_message: str
    ) -> AgentExecution | None:
        """Mark execution as failed with error message."""
        return await self.update(
            execution_id,
            status=ExecutionStatus.FAILED.value,
            error_message=error_message,
            completed_at=datetime.now(UTC),
        )

    async def cancel_execution(self, execution_id: UUID) -> AgentExecution | None:
        """Cancel a running execution."""
        return await self.update(
            execution_id,
            status=ExecutionStatus.CANCELLED.value,
            completed_at=datetime.now(UTC),
        )

    async def get_by_correlation_id(
        self, correlation_id: UUID
    ) -> AgentExecution | None:
        """Get execution by correlation ID."""
        return await self.get_by_field("correlation_id", correlation_id)

    async def get_project_executions(
        self, project_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[AgentExecution]:
        """Get executions for a project, ordered by start time desc."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.project_id == project_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .order_by(desc(self.model.started_at))
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_executions(self, project_id: UUID) -> list[AgentExecution]:
        """Get currently running executions for a project."""
        return await self.get_by_fields(
            project_id=project_id, status=ExecutionStatus.RUNNING.value
        )

    async def get_execution_stats(self, project_id: UUID) -> dict[str, Any]:
        """Get execution statistics for a project."""
        # Count by status
        stmt = (
            select(self.model.status, func.count(self.model.id).label("count"))
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.project_id == project_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .group_by(self.model.status)
        )

        result = await self.session.execute(stmt)
        status_counts = {row.status: row.count for row in result}

        # Count by agent type
        stmt = (
            select(self.model.agent_type, func.count(self.model.id).label("count"))
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.project_id == project_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .group_by(self.model.agent_type)
        )

        result = await self.session.execute(stmt)
        agent_counts = {row.agent_type: row.count for row in result}

        # Average execution time for completed executions
        stmt = select(
            func.avg(
                func.extract("epoch", self.model.completed_at - self.model.started_at)
                * 1000
            ).label("avg_duration_ms")
        ).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.project_id == project_id,
                self.model.status == ExecutionStatus.COMPLETED.value,
                self.model.completed_at.is_not(None),
                self.model.is_deleted.is_(False),
            )
        )

        result = await self.session.execute(stmt)
        avg_duration = result.scalar() or 0

        return {
            "status_counts": status_counts,
            "agent_counts": agent_counts,
            "average_duration_ms": int(avg_duration),
        }

    async def cleanup_old_executions(self, days_old: int = 30) -> int:
        """Soft delete old completed/failed executions."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.is_deleted.is_(False),
                    self.model.status.in_(
                        [ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value]
                    ),
                    self.model.completed_at.is_not(None),
                    self.model.completed_at < cutoff_date,
                )
            )
            .values(is_deleted=True, updated_at=datetime.now(UTC))
        )
        result = await self.session.execute(
            stmt.execution_options(synchronize_session=False)
        )
        await self.session.commit()
        return result.rowcount or 0

    async def get_recent_executions(
        self,
        agent_type: AgentType | None = None,
        status: ExecutionStatus | None = None,
        limit: int = 20,
    ) -> list[AgentExecution]:
        """Get recent executions with optional filtering."""
        filters = {}
        if agent_type:
            filters["agent_type"] = agent_type.value
        if status:
            filters["status"] = status.value

        conditions = [
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False),
        ]
        conditions.extend([getattr(self.model, k) == v for k, v in filters.items()])

        stmt = (
            select(self.model)
            .where(and_(*conditions))
            .order_by(desc(self.model.started_at))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
