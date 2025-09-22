"""
Tenant repository for tenant management operations.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

from app.models.tenant import Tenant
from .base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """Repository for tenant operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Tenant)

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        stmt = select(self.model).where(
            and_(
                self.model.slug == slug,
                self.model.is_active == True
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_tenants(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tenant]:
        """Get all active tenants."""
        stmt = select(self.model).where(
            self.model.is_active == True
        ).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_tenant(
        self,
        name: str,
        slug: str,
        description: Optional[str] = None,
        max_projects: Optional[int] = None,
        max_storage_mb: Optional[int] = None
    ) -> Tenant:
        """Create a new tenant."""
        return await self.create(
            name=name,
            slug=slug,
            description=description,
            max_projects=max_projects,
            max_storage_mb=max_storage_mb,
            is_active=True
        )

    async def deactivate_tenant(self, tenant_id: UUID) -> bool:
        """Deactivate a tenant."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return False

        return await self.update(tenant_id, is_active=False) is not None

    async def activate_tenant(self, tenant_id: UUID) -> bool:
        """Activate a tenant."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return False

        return await self.update(tenant_id, is_active=True) is not None

    async def update_limits(
        self,
        tenant_id: UUID,
        max_projects: Optional[int] = None,
        max_storage_mb: Optional[int] = None
    ) -> Optional[Tenant]:
        """Update tenant resource limits."""
        updates = {}
        if max_projects is not None:
            updates['max_projects'] = max_projects
        if max_storage_mb is not None:
            updates['max_storage_mb'] = max_storage_mb

        if not updates:
            return None

        return await self.update(tenant_id, **updates)

    async def check_slug_availability(self, slug: str, exclude_tenant_id: Optional[UUID] = None) -> bool:
        """Check if slug is available."""
        stmt = select(self.model.id).where(self.model.slug == slug)

        if exclude_tenant_id:
            stmt = stmt.where(self.model.id != exclude_tenant_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is None