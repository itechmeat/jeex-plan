"""
Document versioning model with multi-tenant support.
Handles document versions for the four-stage generation workflow.
"""

from enum import Enum

from sqlalchemy import (
    JSON,
    Column,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    and_,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import foreign, relationship, remote

from .base import BaseModel
from .project import Project


class DocumentType(str, Enum):
    """Document type enumeration for the four-stage workflow."""
    ABOUT = "about"  # Step 1: Business Analysis
    SPECS = "specs"  # Step 2: Engineering Standards
    ARCHITECTURE = "architecture"  # Step 3: Solution Architecture
    PLAN_OVERVIEW = "plan_overview"  # Step 4: Implementation Planning (overview)
    PLAN_EPIC = "plan_epic"  # Step 4: Implementation Planning (individual epics)


class DocumentVersion(BaseModel):
    """Document version entity with tenant isolation and full versioning."""

    __tablename__ = "document_versions"

    # Basic document info
    document_type = Column(String(50), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    # Epic-specific fields for plan documents
    epic_number = Column(Integer, nullable=True)  # For PLAN_EPIC documents
    epic_name = Column(String(255), nullable=True)  # For PLAN_EPIC documents

    # Generation metadata (stored in "metadata" column)
    document_metadata = Column("metadata", JSON, default=dict, nullable=False)

    # Project relationship
    project_id = Column(UUID(as_uuid=True), nullable=False)
    project = relationship(
        "Project",
        back_populates="document_versions",
        primaryjoin=lambda: and_(
            foreign(DocumentVersion.project_id) == remote(Project.id),
            foreign(DocumentVersion.tenant_id) == remote(Project.tenant_id),
        ),
        foreign_keys=lambda: [DocumentVersion.project_id, DocumentVersion.tenant_id],
    )

    # Created by user
    created_by = Column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        # Tenant-scoped FK constraint
        ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            ondelete="CASCADE",
        ),
        # Author (tenant-scoped)
        ForeignKeyConstraint(
            ["created_by", "tenant_id"],
            ["users.id", "users.tenant_id"],
            ondelete="RESTRICT",
        ),
        # Indexes for performance
        Index("idx_document_versions_project_type", "project_id", "document_type"),
        Index("idx_document_versions_project_version", "project_id", "version"),
        Index("idx_document_versions_tenant_created", "tenant_id", "created_at"),
        Index("idx_document_versions_epic", "project_id", "epic_number"),
        Index(
            "uq_document_version_tenant_project_type_version",
            "tenant_id",
            "project_id",
            "document_type",
            "version",
            unique=True,
            postgresql_where=text("epic_number IS NULL AND is_deleted = false"),
        ),
        Index(
            "uq_document_version_tenant_project_epic_version",
            "tenant_id",
            "project_id",
            "epic_number",
            "version",
            unique=True,
            postgresql_where=text("epic_number IS NOT NULL AND document_type = 'plan_epic' AND is_deleted = false"),
        ),
    )
