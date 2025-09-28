"""Tenant repository for tenant management operations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.tenant import Tenant

logger = get_logger()


class TenantRepository:
    """Repository for tenant lifecycle and lookup operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.model = Tenant

    async def create(self, **kwargs: Any) -> Tenant:
        """Create a new tenant entity."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        logger.info("Tenant created", tenant_id=str(instance.id), slug=instance.slug)
        return instance

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Get tenant by identifier."""
        stmt = select(self.model).where(self.model.id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, tenant_id: UUID, **updates: Any) -> Tenant | None:
        """Update tenant attributes."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        for field, value in updates.items():
            if hasattr(tenant, field):
                setattr(tenant, field, value)

        await self.session.flush()
        await self.session.refresh(tenant)
        logger.info(
            "Tenant updated", tenant_id=str(tenant_id), updates=list(updates.keys())
        )
        return tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Get tenant by slug."""
        stmt = select(self.model).where(self.model.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_tenants(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """List active tenants with pagination."""
        stmt = (
            select(self.model)
            .where(self.model.is_active.is_(True))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_tenant(
        self,
        name: str,
        slug: str,
        description: str | None = None,
        max_projects: int | None = None,
        max_storage_mb: int | None = None,
    ) -> Tenant:
        """Create a new tenant with defaults."""
        return await self.create(
            name=name,
            slug=slug,
            description=description,
            max_projects=max_projects,
            max_storage_mb=max_storage_mb,
            is_active=True,
        )

    async def deactivate_tenant(self, tenant_id: UUID) -> bool:
        """Deactivate a tenant."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return False
        await self.update(tenant_id, is_active=False)
        return True

    async def activate_tenant(self, tenant_id: UUID) -> bool:
        """Activate a tenant."""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return False
        await self.update(tenant_id, is_active=True)
        return True

    async def update_limits(
        self,
        tenant_id: UUID,
        max_projects: int | None = None,
        max_storage_mb: int | None = None,
    ) -> Tenant | None:
        """Update tenant resource limits."""
        updates: dict[str, Any] = {}
        if max_projects is not None:
            updates["max_projects"] = max_projects
        if max_storage_mb is not None:
            updates["max_storage_mb"] = max_storage_mb

        if not updates:
            logger.debug(
                "No updates provided for tenant limits", tenant_id=str(tenant_id)
            )
            return None

        return await self.update(tenant_id, **updates)

    async def check_slug_availability(
        self, slug: str, exclude_tenant_id: UUID | None = None
    ) -> bool:
        """Check if slug is unique."""
        stmt = select(self.model.id).where(self.model.slug == slug)

        if exclude_tenant_id:
            stmt = stmt.where(self.model.id != exclude_tenant_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is None

    async def get_default_tenant(self) -> Tenant | None:
        """Get tenant with slug 'default'."""
        stmt = select(self.model).where(self.model.slug == "default")
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_default(self) -> Tenant:
        """Create default tenant if missing."""
        return await self.create_tenant(
            name="Default Tenant",
            slug="default",
            description="Default tenant for new users",
        )
