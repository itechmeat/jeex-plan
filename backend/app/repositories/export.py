"""
Export repository with tenant isolation.
Handles ZIP archive generation and download tracking.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.export import Export, ExportStatus
from app.repositories.base import TenantRepository

logger = get_logger()


class ExportRepository(TenantRepository[Export]):
    """Repository for exports with tenant isolation."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Export, tenant_id)

    async def create_export(
        self,
        project_id: UUID,
        requested_by: UUID,
        manifest: dict[str, Any],
        expires_in_hours: int = 24,
    ) -> Export:
        """Create a new export request."""
        expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours)

        return await self.create(
            project_id=project_id,
            requested_by=requested_by,
            manifest=manifest,
            status=ExportStatus.PENDING.value,
            expires_at=expires_at,
        )

    async def start_generation(self, export_id: UUID) -> Export | None:
        """Atomically mark export as generating if currently pending."""
        from sqlalchemy import update

        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.id == export_id,
                    self.model.status == ExportStatus.PENDING.value,
                    self.model.is_deleted.is_(False),
                )
            )
            .values(status=ExportStatus.GENERATING.value, updated_at=datetime.now(UTC))
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def complete_export(self, export_id: UUID, file_path: str) -> Export | None:
        """Mark export as completed with file path."""
        return await self.update(
            export_id, status=ExportStatus.COMPLETED.value, file_path=file_path
        )

    async def fail_export(self, export_id: UUID, error_message: str) -> Export | None:
        """Mark export as failed with error message."""
        return await self.update(
            export_id, status=ExportStatus.FAILED.value, error_message=error_message
        )

    async def get_project_exports(
        self, project_id: UUID, limit: int = 20, offset: int = 0
    ) -> list[Export]:
        """Get exports for a project, ordered by creation time desc."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.project_id == project_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .order_by(desc(self.model.created_at))
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_downloadable_exports(self, project_id: UUID) -> list[Export]:
        """Get exports that are ready for download."""
        now = datetime.now(UTC)

        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.project_id == project_id,
                    self.model.status == ExportStatus.COMPLETED.value,
                    self.model.expires_at > now,
                    self.model.file_path.is_not(None),
                    self.model.is_deleted.is_(False),
                )
            )
            .order_by(desc(self.model.created_at))
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_expired_exports(self) -> list[Export]:
        """Get exports that have expired."""
        now = datetime.now(UTC)

        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.expires_at <= now,
                self.model.status != ExportStatus.EXPIRED.value,
                self.model.is_deleted.is_(False),
            )
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_expired(self, export_ids: list[UUID]) -> int:
        """Mark multiple exports as expired."""
        if not export_ids:
            return 0

        from sqlalchemy import update

        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.is_deleted.is_(False),
                    self.model.id.in_(export_ids),
                )
            )
            .values(status=ExportStatus.EXPIRED.value, updated_at=datetime.now(UTC))
        )
        result = await self.session.execute(
            stmt.execution_options(synchronize_session=False)
        )
        await self.session.commit()
        return result.rowcount or 0

    async def cleanup_old_exports(self, days_old: int = 7) -> int:
        """Soft delete old expired exports."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

        from sqlalchemy import update

        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.status == ExportStatus.EXPIRED.value,
                    self.model.expires_at < cutoff_date,
                    self.model.is_deleted.is_(False),
                )
            )
            .values(is_deleted=True, updated_at=datetime.now(UTC))
        )
        result = await self.session.execute(
            stmt.execution_options(synchronize_session=False)
        )
        await self.session.commit()
        return result.rowcount or 0

    async def get_user_exports(
        self, requested_by: UUID, limit: int = 20, offset: int = 0
    ) -> list[Export]:
        """Get exports requested by a specific user."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.requested_by == requested_by,
                    self.model.is_deleted.is_(False),
                )
            )
            .order_by(desc(self.model.created_at))
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_exports(self) -> list[Export]:
        """Get exports that are pending generation."""
        return await self.get_by_fields(status=ExportStatus.PENDING.value)

    async def get_export_stats(self) -> dict[str, Any]:
        """Get export statistics for the tenant."""
        from sqlalchemy import func

        # Count by status
        status_stmt = (
            select(self.model.status, func.count(self.model.id).label("count"))
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .group_by(self.model.status)
        )

        status_result = await self.session.execute(status_stmt)
        status_counts = {row.status: row.count for row in status_result.fetchall()}

        # Count exports in last 30 days
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
        recent_stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.created_at >= thirty_days_ago,
                self.model.is_deleted.is_(False),
            )
        )

        recent_result = await self.session.execute(recent_stmt)
        recent_count = int(recent_result.scalar() or 0)

        return {"status_counts": status_counts, "recent_exports_30d": recent_count}
