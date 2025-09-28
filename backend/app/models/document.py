"""Document model with multi-tenant support."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKeyConstraint, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .project import Project


class DocumentType(str, Enum):
    """Document type enumeration."""

    ARCHITECTURE = "ARCHITECTURE"
    PLANNING = "PLANNING"
    STANDARDS = "STANDARDS"
    TECHNICAL_SPEC = "TECHNICAL_SPEC"


class DocumentStatus(str, Enum):
    """Document generation status."""

    PENDING = "PENDING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Document(BaseModel):
    """Document entity with tenant isolation."""

    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType, name="documenttype"),
        nullable=False,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus, name="documentstatus"),
        default=DocumentStatus.PENDING,
        nullable=False,
    )

    # Generation metadata
    generation_step: Mapped[int] = mapped_column(  # 1-4 for wizard steps
        Integer, default=1, nullable=False
    )
    generation_progress: Mapped[int] = mapped_column(  # 0-100%
        Integer, default=0, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Project relationship
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "project_id"],
            ["projects.tenant_id", "projects.id"],
            ondelete="CASCADE",
        ),
    )

    project: Mapped[Project] = relationship("Project", back_populates="documents")

    class Config:
        """Pydantic config."""

        from_attributes = True
