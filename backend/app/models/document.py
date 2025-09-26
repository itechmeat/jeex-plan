"""
Document model with multi-tenant support.
"""

from enum import Enum

from sqlalchemy import (
    Column,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


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

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    document_type = Column(
        SQLEnum(DocumentType, name="documenttype"),
        nullable=False,
    )
    status = Column(
        SQLEnum(DocumentStatus, name="documentstatus"),
        default=DocumentStatus.PENDING,
        nullable=False,
    )

    # Generation metadata
    generation_step = Column(Integer, default=1, nullable=False)  # 1-4 for wizard steps
    generation_progress = Column(Integer, default=0, nullable=False)  # 0-100%
    error_message = Column(Text, nullable=True)

    # Project relationship
    project_id = Column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "project_id"],
            ["projects.tenant_id", "projects.id"],
            ondelete="CASCADE",
        ),
    )

    project = relationship("Project", back_populates="documents")

    class Config:
        """Pydantic config."""
        from_attributes = True
