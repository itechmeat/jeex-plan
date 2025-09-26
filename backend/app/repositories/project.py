"""
Project repository for project management operations with tenant isolation.
"""

from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus

from .base import TenantRepository


class ProjectRepository(TenantRepository[Project]):
    """Repository for project operations with tenant isolation."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Project, tenant_id)

    async def get_by_name(self, name: str) -> Project | None:
        """Get project by name within tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.name == name,
                self.model.tenant_id == self.tenant_id,
                not self.model.is_deleted
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_owner(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> list[Project]:
        """Get projects by owner within tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.owner_id == owner_id,
                self.model.tenant_id == self.tenant_id,
                not self.model.is_deleted
            )
        ).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: ProjectStatus,
        skip: int = 0,
        limit: int = 100
    ) -> list[Project]:
        """Get projects by status within tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.status == status,
                self.model.tenant_id == self.tenant_id,
                not self.model.is_deleted
            )
        ).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_project(
        self,
        name: str,
        owner_id: UUID,
        description: str | None = None,
        status: ProjectStatus = ProjectStatus.DRAFT
    ) -> Project:
        """Create a new project within tenant."""
        return await self.create(
            name=name,
            owner_id=owner_id,
            description=description,
            status=status
        )

    async def update_status(self, project_id: UUID, status: ProjectStatus) -> Project | None:
        """Update project status."""
        return await self.update(project_id, status=status)

    async def archive_project(self, project_id: UUID) -> Project | None:
        """Archive a project."""
        return await self.update_status(project_id, ProjectStatus.ARCHIVED)

    async def complete_project(self, project_id: UUID) -> Project | None:
        """Mark project as completed."""
        return await self.update_status(project_id, ProjectStatus.COMPLETED)

    async def start_project(self, project_id: UUID) -> Project | None:
        """Start a project (set status to in_progress)."""
        return await self.update_status(project_id, ProjectStatus.IN_PROGRESS)

    async def search_projects(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Project]:
        """Search projects by name or description within tenant."""
        return await self.search(
            search_fields=['name', 'description'],
            search_term=search_term,
            skip=skip,
            limit=limit
        )

    async def get_recent_projects(
        self,
        owner_id: UUID | None = None,
        limit: int = 10
    ) -> list[Project]:
        """Get recent projects within tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                not self.model.is_deleted
            )
        )

        if owner_id:
            stmt = stmt.where(self.model.owner_id == owner_id)

        stmt = stmt.order_by(desc(self.model.updated_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_status(self, status: ProjectStatus) -> int:
        """Count projects by status within tenant."""
        stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.status == status,
                self.model.tenant_id == self.tenant_id,
                not self.model.is_deleted
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_by_owner(self, owner_id: UUID) -> int:
        """Count projects by owner within tenant."""
        stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.owner_id == owner_id,
                self.model.tenant_id == self.tenant_id,
                not self.model.is_deleted
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def check_name_availability(
        self,
        name: str,
        exclude_project_id: UUID | None = None
    ) -> bool:
        """Check if project name is available within tenant."""
        stmt = select(self.model.id).where(
            and_(
                self.model.name == name,
                self.model.tenant_id == self.tenant_id,
                not self.model.is_deleted
            )
        )

        if exclude_project_id:
            stmt = stmt.where(self.model.id != exclude_project_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is None
