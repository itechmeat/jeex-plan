"""
Export repository with tenant isolation.
Handles ZIP archive generation and download tracking.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.export import Export, ExportStatus
from app.repositories.base import TenantRepository
from app.core.logger import get_logger

logger = get_logger()


class ExportRepository(TenantRepository[Export]):
    """Repository for exports with tenant isolation."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, Export, tenant_id)

    async def create_export(
        self,
        project_id: UUID,
        requested_by: UUID,
        manifest: Dict[str, Any],
        expires_in_hours: int = 24
    ) -> Export:
        """Create a new export request."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        return await self.create(
            project_id=project_id,
            requested_by=requested_by,
            manifest=manifest,
            status=ExportStatus.PENDING.value,
            expires_at=expires_at
        )

    async def start_generation(self, export_id: UUID) -> Optional[Export]:
        """Mark export as generating."""
        return await self.update(
            export_id,
            status=ExportStatus.GENERATING.value
        )

    async def complete_export(
        self,
        export_id: UUID,
        file_path: str
    ) -> Optional[Export]:
        """Mark export as completed with file path."""
        return await self.update(
            export_id,
            status=ExportStatus.COMPLETED.value,
            file_path=file_path
        )

    async def fail_export(
        self,
        export_id: UUID,
        error_message: str
    ) -> Optional[Export]:
        """Mark export as failed with error message."""
        return await self.update(
            export_id,
            status=ExportStatus.FAILED.value,
            error_message=error_message
        )

    async def get_project_exports(
        self,
        project_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[Export]:
        """Get exports for a project, ordered by creation time desc."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.project_id == project_id,
                self.model.is_deleted.is_(False)
            )
        ).order_by(desc(self.model.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_downloadable_exports(self, project_id: UUID) -> List[Export]:
        """Get exports that are ready for download."""
        now = datetime.now(timezone.utc)

        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.project_id == project_id,
                self.model.status == ExportStatus.COMPLETED.value,
                self.model.expires_at > now,
                self.model.file_path.is_not(None),
                self.model.is_deleted.is_(False)
            )
        ).order_by(desc(self.model.created_at))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_expired_exports(self) -> List[Export]:
        """Get exports that have expired."""
        now = datetime.now(timezone.utc)

        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.expires_at <= now,
                self.model.status != ExportStatus.EXPIRED.value,
                self.model.is_deleted.is_(False)
            )
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_expired(self, export_ids: List[UUID]) -> int:
        """Mark multiple exports as expired."""
        if not export_ids:
            return 0

        return await self.bulk_update(
            filters={"id": export_ids},
            updates={"status": ExportStatus.EXPIRED.value}
        )

    async def cleanup_old_exports(self, days_old: int = 7) -> int:
        """Soft delete old expired exports."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        return await self.bulk_update(
            filters={
                "status": ExportStatus.EXPIRED.value,
                "expires_at": {"lt": cutoff_date}
            },
            updates={"is_deleted": True}
        )

    async def get_user_exports(
        self,
        requested_by: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[Export]:
        """Get exports requested by a specific user."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.requested_by == requested_by,
                self.model.is_deleted.is_(False)
            )
        ).order_by(desc(self.model.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_exports(self) -> List[Export]:
        """Get exports that are pending generation."""
        return await self.get_by_fields(
            status=ExportStatus.PENDING.value
        )

    async def get_export_stats(self) -> Dict[str, Any]:
        """Get export statistics for the tenant."""
        from sqlalchemy import func

        # Count by status
        stmt = select(
            self.model.status,
            func.count(self.model.id).label("count")
        ).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted.is_(False)
            )
        ).group_by(self.model.status)

        result = await self.session.execute(stmt)
        status_counts = {row.status: row.count for row in result}

        # Count exports in last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.created_at >= thirty_days_ago,
                self.model.is_deleted.is_(False)
            )
        )

        result = await self.session.execute(stmt)
        recent_count = result.scalar() or 0

        return {
            "status_counts": status_counts,
            "recent_exports_30d": recent_count
        }