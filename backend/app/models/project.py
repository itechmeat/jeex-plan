"""
Project model with multi-tenant support.
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    Enum as SQLEnum,
    UniqueConstraint,
    ForeignKey,
    ForeignKeyConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
from .base import BaseModel


class ProjectStatus(str, Enum):
    """Project status enumeration."""
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class Project(BaseModel):
    """Project entity with tenant isolation."""

    __tablename__ = "projects"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(ProjectStatus, name="projectstatus"),
        default=ProjectStatus.DRAFT,
        nullable=False,
    )

    # Owner relationship
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    owner = relationship("User", back_populates="projects")

    # Tenant relationship
    tenant = relationship("Tenant", back_populates="projects")

    # Documents relationship
    documents = relationship("Document", back_populates="project")

    # RBAC relationships
    members = relationship("ProjectMember", back_populates="project")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_project_tenant_name"),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["owner_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            ondelete="RESTRICT",
        ),
    )

    class Config:
        """Pydantic config."""
        from_attributes = True
