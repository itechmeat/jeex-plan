"""
Document version repository with tenant isolation and versioning support.
Handles document versioning for the four-stage generation workflow.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.document_version import DocumentType, DocumentVersion
from app.repositories.base import TenantRepository

logger = get_logger()


class DocumentVersionRepository(TenantRepository[DocumentVersion]):
    """Repository for document versions with tenant isolation."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, DocumentVersion, tenant_id)

    async def create_version(
        self,
        project_id: UUID,
        document_type: DocumentType,
        title: str,
        content: str,
        created_by: UUID,
        epic_number: int | None = None,
        epic_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentVersion:
        """Create a new document version.

        Args:
            project_id: Project UUID
            document_type: Type of document
            title: Document title
            content: Document content
            created_by: User UUID who created the document
            epic_number: Epic number for PLAN_EPIC documents
            epic_name: Epic name for PLAN_EPIC documents
            metadata: Additional metadata to store with the document
        """
        base_data: dict[str, Any] = {
            "project_id": project_id,
            "document_type": document_type.value,
            "title": title,
            "content": content,
            "created_by": created_by,
            "document_metadata": metadata or {},
        }

        # Add epic fields if this is a plan epic document
        if document_type == DocumentType.PLAN_EPIC:
            if epic_number is None:
                raise ValueError("epic_number is required for PLAN_EPIC documents")
            base_data["epic_number"] = epic_number
            base_data["epic_name"] = epic_name

        last_error: IntegrityError | None = None
        for attempt in range(3):
            next_version = await self.get_next_version(
                project_id, document_type, epic_number
            )
            try:
                return await self.create(**{**base_data, "version": next_version})
            except IntegrityError as exc:
                last_error = exc
                await self.session.rollback()
                logger.warning(
                    "Retrying document version creation after integrity error",
                    attempt=attempt + 1,
                    project_id=str(project_id),
                    document_type=document_type.value,
                    epic_number=epic_number,
                    tenant_id=str(self.tenant_id),
                )

        raise RuntimeError(
            "Concurrent document version creation conflict"
        ) from last_error

    async def get_next_version(
        self,
        project_id: UUID,
        document_type: DocumentType,
        epic_number: int | None = None,
    ) -> int:
        """Get the next version number for a document type."""
        filters: dict[str, Any] = {}
        filters["project_id"] = project_id
        filters["document_type"] = document_type.value

        if document_type == DocumentType.PLAN_EPIC and epic_number is not None:
            filters["epic_number"] = epic_number

        stmt = select(func.max(self.model.version)).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted.is_(False),
                *[getattr(self.model, k) == v for k, v in filters.items()],
            )
        )

        result = await self.session.execute(stmt)
        max_version = result.scalar()
        return (max_version or 0) + 1

    async def get_latest_version(
        self,
        project_id: UUID,
        document_type: DocumentType,
        epic_number: int | None = None,
    ) -> DocumentVersion | None:
        """Get the latest version of a document."""
        filters: dict[str, Any] = {
            "project_id": project_id,
            "document_type": document_type.value,
        }

        if document_type == DocumentType.PLAN_EPIC and epic_number is not None:
            filters["epic_number"] = epic_number

        conditions = [
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False),
        ]
        conditions.extend([getattr(self.model, k) == v for k, v in filters.items()])

        stmt = (
            select(self.model)
            .where(and_(*conditions))
            .order_by(desc(self.model.version))
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_version(
        self,
        project_id: UUID,
        document_type: DocumentType,
        version: int,
        epic_number: int | None = None,
    ) -> DocumentVersion | None:
        """Get a specific version of a document."""
        filters: dict[str, Any] = {}
        filters["project_id"] = project_id
        filters["document_type"] = document_type.value
        filters["version"] = version

        if document_type == DocumentType.PLAN_EPIC and epic_number is not None:
            filters["epic_number"] = epic_number

        conditions = [
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False),
            *[getattr(self.model, k) == v for k, v in filters.items()],
        ]
        stmt = select(self.model).where(and_(*conditions)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_versions(
        self,
        project_id: UUID,
        document_type: DocumentType,
        epic_number: int | None = None,
    ) -> list[DocumentVersion]:
        """Get all versions of a document, ordered by version desc."""
        filters: dict[str, Any] = {}
        filters["project_id"] = project_id
        filters["document_type"] = document_type.value

        if document_type == DocumentType.PLAN_EPIC and epic_number is not None:
            filters["epic_number"] = epic_number

        conditions = [
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False),
        ]
        conditions.extend([getattr(self.model, k) == v for k, v in filters.items()])

        stmt = (
            select(self.model)
            .where(and_(*conditions))
            .order_by(desc(self.model.version))
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_project_documents(self, project_id: UUID) -> list[DocumentVersion]:
        """Get all latest document versions for a project."""
        # Subquery to get max version for each document type/epic combination
        subquery = (
            select(
                self.model.document_type,
                self.model.epic_number,
                func.max(self.model.version).label("max_version"),
            )
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.project_id == project_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .group_by(self.model.document_type, self.model.epic_number)
            .subquery()
        )

        # Main query to get the actual documents
        stmt = (
            select(self.model)
            .join(
                subquery,
                and_(
                    self.model.document_type == subquery.c.document_type,
                    self.model.version == subquery.c.max_version,
                    # Handle NULL epic_number comparison
                    (self.model.epic_number == subquery.c.epic_number)
                    | (
                        and_(
                            self.model.epic_number.is_(None),
                            subquery.c.epic_number.is_(None),
                        )
                    ),
                ),
            )
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.project_id == project_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .order_by(self.model.created_at)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_epic_documents(self, project_id: UUID) -> list[DocumentVersion]:
        """Get latest PLAN_EPIC documents (one per epic)."""
        subq = (
            select(
                self.model.epic_number,
                func.max(self.model.version).label("max_version"),
            )
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.project_id == project_id,
                    self.model.document_type == DocumentType.PLAN_EPIC.value,
                    self.model.is_deleted.is_(False),
                )
            )
            .group_by(self.model.epic_number)
            .subquery()
        )
        stmt = (
            select(self.model)
            .join(
                subq,
                and_(
                    self.model.epic_number == subq.c.epic_number,
                    self.model.version == subq.c.max_version,
                ),
            )
            .where(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.project_id == project_id,
                    self.model.document_type == DocumentType.PLAN_EPIC.value,
                    self.model.is_deleted.is_(False),
                )
            )
            .order_by(self.model.epic_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ids(self, ids: list[UUID]) -> list[DocumentVersion]:
        """Get documents by IDs preserving input order."""
        if not ids:
            return []

        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False),
            self.model.id.in_(ids),
        )

        result = await self.session.execute(stmt)
        documents = list(result.scalars().all())

        order_map = {document_id: index for index, document_id in enumerate(ids)}
        documents.sort(key=lambda doc: order_map.get(doc.id, len(order_map)))
        return documents

    async def delete_document_versions(
        self,
        project_id: UUID,
        document_type: DocumentType,
        epic_number: int | None = None,
    ) -> int:
        """Soft delete all versions of a document."""
        filters: dict[str, Any] = {
            "project_id": project_id,
            "document_type": document_type.value,
        }

        if document_type == DocumentType.PLAN_EPIC and epic_number is not None:
            filters["epic_number"] = epic_number

        return await self.bulk_update(filters=filters, updates={"is_deleted": True})
