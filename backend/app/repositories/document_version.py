"""
Document version repository with tenant isolation and versioning support.
Handles document versioning for the four-stage generation workflow.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import and_, select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_version import DocumentVersion, DocumentType
from app.repositories.base import TenantRepository
from app.core.logger import get_logger

logger = get_logger()


class DocumentVersionRepository(TenantRepository[DocumentVersion]):
    """Repository for document versions with tenant isolation."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, DocumentVersion, tenant_id)

    async def create_version(
        self,
        project_id: UUID,
        document_type: DocumentType,
        title: str,
        content: str,
        created_by: UUID,
        epic_number: Optional[int] = None,
        epic_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentVersion:
        """Create a new document version."""
        # Get next version number for this document type
        next_version = await self.get_next_version(project_id, document_type, epic_number)

        version_data = {
            "project_id": project_id,
            "document_type": document_type.value,
            "version": next_version,
            "title": title,
            "content": content,
            "created_by": created_by,
            "metadata": metadata or {}
        }

        # Add epic fields if this is a plan epic document
        if document_type == DocumentType.PLAN_EPIC:
            if epic_number is None:
                raise ValueError("epic_number is required for PLAN_EPIC documents")
            version_data["epic_number"] = epic_number
            version_data["epic_name"] = epic_name

        return await self.create(**version_data)

    async def get_next_version(
        self,
        project_id: UUID,
        document_type: DocumentType,
        epic_number: Optional[int] = None
    ) -> int:
        """Get the next version number for a document type."""
        filters = {
            "project_id": project_id,
            "document_type": document_type.value
        }

        if document_type == DocumentType.PLAN_EPIC and epic_number is not None:
            filters["epic_number"] = epic_number

        stmt = select(func.max(self.model.version)).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted.is_(False),
                *[getattr(self.model, k) == v for k, v in filters.items()]
            )
        )

        result = await self.session.execute(stmt)
        max_version = result.scalar()
        return (max_version or 0) + 1

    async def get_latest_version(
        self,
        project_id: UUID,
        document_type: DocumentType,
        epic_number: Optional[int] = None
    ) -> Optional[DocumentVersion]:
        """Get the latest version of a document."""
        filters = {
            "project_id": project_id,
            "document_type": document_type.value
        }

        if document_type == DocumentType.PLAN_EPIC and epic_number is not None:
            filters["epic_number"] = epic_number

        conditions = [
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False)
        ]
        conditions.extend([getattr(self.model, k) == v for k, v in filters.items()])

        stmt = select(self.model).where(
            and_(*conditions)
        ).order_by(desc(self.model.version)).limit(1)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_version(
        self,
        project_id: UUID,
        document_type: DocumentType,
        version: int,
        epic_number: Optional[int] = None
    ) -> Optional[DocumentVersion]:
        """Get a specific version of a document."""
        filters = {
            "project_id": project_id,
            "document_type": document_type.value,
            "version": version
        }

        if document_type == DocumentType.PLAN_EPIC and epic_number is not None:
            filters["epic_number"] = epic_number

        return await self.get_by_fields(**filters)

    async def get_all_versions(
        self,
        project_id: UUID,
        document_type: DocumentType,
        epic_number: Optional[int] = None
    ) -> List[DocumentVersion]:
        """Get all versions of a document, ordered by version desc."""
        filters = {
            "project_id": project_id,
            "document_type": document_type.value
        }

        if document_type == DocumentType.PLAN_EPIC and epic_number is not None:
            filters["epic_number"] = epic_number

        conditions = [
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False)
        ]
        conditions.extend([getattr(self.model, k) == v for k, v in filters.items()])

        stmt = select(self.model).where(
            and_(*conditions)
        ).order_by(desc(self.model.version))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_project_documents(self, project_id: UUID) -> List[DocumentVersion]:
        """Get all latest document versions for a project."""
        # Subquery to get max version for each document type/epic combination
        subquery = select(
            self.model.document_type,
            self.model.epic_number,
            func.max(self.model.version).label("max_version")
        ).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.project_id == project_id,
                self.model.is_deleted.is_(False)
            )
        ).group_by(
            self.model.document_type,
            self.model.epic_number
        ).subquery()

        # Main query to get the actual documents
        stmt = select(self.model).select_from(
            self.model.join(
                subquery,
                and_(
                    self.model.document_type == subquery.c.document_type,
                    self.model.version == subquery.c.max_version,
                    # Handle NULL epic_number comparison
                    (self.model.epic_number == subquery.c.epic_number) |
                    (and_(self.model.epic_number.is_(None), subquery.c.epic_number.is_(None)))
                )
            )
        ).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.project_id == project_id,
                self.model.is_deleted.is_(False)
            )
        ).order_by(self.model.created_at)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_epic_documents(self, project_id: UUID) -> List[DocumentVersion]:
        """Get all latest epic documents for a project."""
        return await self.get_by_fields(
            project_id=project_id,
            document_type=DocumentType.PLAN_EPIC.value
        )

    async def delete_document_versions(
        self,
        project_id: UUID,
        document_type: DocumentType,
        epic_number: Optional[int] = None
    ) -> int:
        """Soft delete all versions of a document."""
        filters = {
            "project_id": project_id,
            "document_type": document_type.value
        }

        if document_type == DocumentType.PLAN_EPIC and epic_number is not None:
            filters["epic_number"] = epic_number

        return await self.bulk_update(
            filters=filters,
            updates={"is_deleted": True}
        )