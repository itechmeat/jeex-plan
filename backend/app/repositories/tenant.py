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
        """
        Create a new tenant entity.

        Accepted fields:
            - name (str, required): Tenant name
            - slug (str, required): Unique tenant slug
            - description (str, optional): Tenant description
            - max_projects (int, optional): Maximum projects limit
            - max_storage_mb (int, optional): Maximum storage in MB
            - is_active (bool, optional): Active status (default: True)

        Raises:
            ValueError: If required fields are missing or invalid fields provided
        """
        # Validate required fields
        if "name" not in kwargs or not kwargs["name"]:
            raise ValueError("Field 'name' is required")
        if "slug" not in kwargs or not kwargs["slug"]:
            raise ValueError("Field 'slug' is required")

        # Validate only accepted fields are provided
        allowed_fields = {
            "name",
            "slug",
            "description",
            "max_projects",
            "max_storage_mb",
            "is_active",
        }
        invalid_fields = set(kwargs.keys()) - allowed_fields
        if invalid_fields:
            raise ValueError(f"Invalid fields provided: {', '.join(invalid_fields)}")

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
        """Get tenant by slug (active tenants only)."""
        stmt = select(self.model).where(
            self.model.slug == slug, self.model.is_active.is_(True)
        )
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

    # REMOVED: get_default_tenant() and create_default() methods


# These violate the strict no-fallback architecture rule.
# Tenants must be explicitly created and provided - no default tenant fallbacks.
