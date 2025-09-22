"""
Document repository for document management operations with tenant isolation.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.document import Document, DocumentType, DocumentStatus
from .base import TenantRepository


class DocumentRepository(TenantRepository[Document]):
    """Repository for document operations with tenant isolation."""

    def __init__(self, session: Session, tenant_id: UUID):
        super().__init__(session, Document, tenant_id)

    def get_by_project(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """Get documents by project within tenant."""
        return self.session.query(self.model).filter(
            and_(
                self.model.project_id == project_id,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        ).offset(skip).limit(limit).all()

    def get_by_type(
        self,
        document_type: DocumentType,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """Get documents by type within tenant."""
        return self.session.query(self.model).filter(
            and_(
                self.model.document_type == document_type,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        ).offset(skip).limit(limit).all()

    def get_by_status(
        self,
        status: DocumentStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """Get documents by status within tenant."""
        return self.session.query(self.model).filter(
            and_(
                self.model.status == status,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        ).offset(skip).limit(limit).all()

    def get_by_project_and_type(
        self,
        project_id: UUID,
        document_type: DocumentType
    ) -> Optional[Document]:
        """Get document by project and type within tenant."""
        return self.session.query(self.model).filter(
            and_(
                self.model.project_id == project_id,
                self.model.document_type == document_type,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        ).first()

    def create_document(
        self,
        title: str,
        project_id: UUID,
        document_type: DocumentType,
        content: Optional[str] = None,
        status: DocumentStatus = DocumentStatus.PENDING
    ) -> Document:
        """Create a new document within tenant."""
        return self.create(
            title=title,
            project_id=project_id,
            document_type=document_type,
            content=content,
            status=status,
            generation_step=1,
            generation_progress=0
        )

    def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_message: Optional[str] = None
    ) -> Optional[Document]:
        """Update document status."""
        updates = {'status': status}
        if error_message is not None:
            updates['error_message'] = error_message

        return self.update(document_id, **updates)

    def update_progress(
        self,
        document_id: UUID,
        generation_step: int,
        generation_progress: int
    ) -> Optional[Document]:
        """Update document generation progress."""
        return self.update(
            document_id,
            generation_step=generation_step,
            generation_progress=generation_progress
        )

    def update_content(self, document_id: UUID, content: str) -> Optional[Document]:
        """Update document content."""
        return self.update(document_id, content=content)

    def mark_completed(
        self,
        document_id: UUID,
        content: str
    ) -> Optional[Document]:
        """Mark document as completed with final content."""
        return self.update(
            document_id,
            status=DocumentStatus.COMPLETED,
            content=content,
            generation_progress=100
        )

    def mark_failed(
        self,
        document_id: UUID,
        error_message: str
    ) -> Optional[Document]:
        """Mark document generation as failed."""
        return self.update(
            document_id,
            status=DocumentStatus.FAILED,
            error_message=error_message
        )

    def search_documents(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """Search documents by title or content within tenant."""
        return self.search(
            search_fields=['title', 'content'],
            search_term=search_term,
            skip=skip,
            limit=limit
        )

    def get_pending_documents(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """Get pending documents within tenant."""
        return self.get_by_status(DocumentStatus.PENDING, skip, limit)

    def get_generating_documents(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """Get documents currently being generated within tenant."""
        return self.get_by_status(DocumentStatus.GENERATING, skip, limit)

    def count_by_project(self, project_id: UUID) -> int:
        """Count documents by project within tenant."""
        return self.session.query(self.model).filter(
            and_(
                self.model.project_id == project_id,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        ).count()

    def count_by_type(self, document_type: DocumentType) -> int:
        """Count documents by type within tenant."""
        return self.session.query(self.model).filter(
            and_(
                self.model.document_type == document_type,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        ).count()

    def count_by_status(self, status: DocumentStatus) -> int:
        """Count documents by status within tenant."""
        return self.session.query(self.model).filter(
            and_(
                self.model.status == status,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        ).count()