"""Document versioning model with multi-tenant support."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
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
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Epic-specific fields for plan documents
    epic_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    epic_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Generation metadata (stored in "metadata" column)
    document_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )

    # Project relationship
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="document_versions",
        primaryjoin="and_(DocumentVersion.project_id == Project.id, DocumentVersion.tenant_id == Project.tenant_id)",
        foreign_keys="[DocumentVersion.project_id, DocumentVersion.tenant_id]",
    )

    # Created by user
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

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
            postgresql_where=text(
                "epic_number IS NOT NULL AND document_type = 'plan_epic' AND is_deleted = false"
            ),
        ),
    )
