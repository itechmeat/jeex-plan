"""Document repository for document management operations with tenant isolation."""

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus, DocumentType

from .base import TenantRepository


class DocumentRepository(TenantRepository[Document]):
    """Repository for document operations with tenant isolation."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Document, tenant_id)

    async def get_by_project(
        self, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """Get documents by project within tenant."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.project_id == project_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_type(
        self, document_type: DocumentType, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """Get documents by type within tenant."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.document_type == document_type,
                    self.model.tenant_id == self.tenant_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(
        self, status: DocumentStatus, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """Get documents by status within tenant."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.status == status,
                    self.model.tenant_id == self.tenant_id,
                    self.model.is_deleted.is_(False),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_project_and_type(
        self, project_id: UUID, document_type: DocumentType
    ) -> Document | None:
        """Get document by project and type within tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.project_id == project_id,
                self.model.document_type == document_type,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_document(
        self,
        title: str,
        project_id: UUID,
        document_type: DocumentType,
        content: str | None = None,
        status: DocumentStatus = DocumentStatus.PENDING,
    ) -> Document:
        """Create a new document within tenant."""
        return await self.create(
            title=title,
            project_id=project_id,
            document_type=document_type,
            content=content,
            status=status,
            generation_step=1,
            generation_progress=0,
        )

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> Document | None:
        """Update document status."""
        updates: dict[str, Any] = {"status": status}
        if error_message is not None:
            updates["error_message"] = error_message

        return await self.update(document_id, **updates)

    async def update_progress(
        self, document_id: UUID, generation_step: int, generation_progress: int
    ) -> Document | None:
        """Update document generation progress."""
        return await self.update(
            document_id,
            generation_step=generation_step,
            generation_progress=generation_progress,
        )

    async def update_content(self, document_id: UUID, content: str) -> Document | None:
        """Update document content."""
        return await self.update(document_id, content=content)

    async def mark_completed(self, document_id: UUID, content: str) -> Document | None:
        """Mark document as completed with final content."""
        return await self.update(
            document_id,
            status=DocumentStatus.COMPLETED,
            content=content,
            generation_progress=100,
        )

    async def mark_failed(
        self, document_id: UUID, error_message: str
    ) -> Document | None:
        """Mark document generation as failed."""
        return await self.update(
            document_id, status=DocumentStatus.FAILED, error_message=error_message
        )

    async def search_documents(
        self, search_term: str, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """Search documents by title or content within tenant."""
        return await self.search(
            search_fields=["title", "content"],
            search_term=search_term,
            skip=skip,
            limit=limit,
        )

    async def get_pending_documents(
        self, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """Get pending documents within tenant."""
        return await self.get_by_status(DocumentStatus.PENDING, skip, limit)

    async def get_generating_documents(
        self, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """Get documents currently being generated within tenant."""
        return await self.get_by_status(DocumentStatus.GENERATING, skip, limit)

    async def count_by_project(self, project_id: UUID) -> int:
        """Count documents by project within tenant."""
        stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.project_id == project_id,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def count_by_type(self, document_type: DocumentType) -> int:
        """Count documents by type within tenant."""
        stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.document_type == document_type,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def count_by_status(self, status: DocumentStatus) -> int:
        """Count documents by status within tenant."""
        stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.status == status,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        # Explicit int cast for type safety
        return int(result.scalar() or 0)
