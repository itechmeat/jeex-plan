"""
Document model with multi-tenant support.
"""

from sqlalchemy import Column, String, Text, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
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
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)

    # Generation metadata
    generation_step = Column(Integer, default=1, nullable=False)  # 1-4 for wizard steps
    generation_progress = Column(Integer, default=0, nullable=False)  # 0-100%
    error_message = Column(Text, nullable=True)

    # Project relationship
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="documents")

    class Config:
        """Pydantic config."""
        from_attributes = True