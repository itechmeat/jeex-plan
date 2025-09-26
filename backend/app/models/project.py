"""
Project model with multi-tenant support.
"""

from enum import Enum

from sqlalchemy import (
    Column,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import foreign, relationship, remote

from .base import BaseModel
from .document import Document
from .tenant import Tenant
from .user import User


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
    owner = relationship(
        "User",
        back_populates="projects",
        primaryjoin=lambda: and_(
            foreign(Project.owner_id) == remote(User.id),
            foreign(Project.tenant_id) == remote(User.tenant_id),
        ),
        foreign_keys=lambda: [Project.owner_id, Project.tenant_id],
    )

    # Tenant relationship
    tenant = relationship(
        "Tenant",
        back_populates="projects",
        primaryjoin=lambda: foreign(Project.tenant_id) == remote(Tenant.id),
        foreign_keys=lambda: [Project.tenant_id],
    )

    # Documents relationship
    documents = relationship(
        "Document",
        back_populates="project",
        primaryjoin=lambda: and_(
            foreign(Document.project_id) == remote(Project.id),
            foreign(Document.tenant_id) == remote(Project.tenant_id),
        ),
        foreign_keys=lambda: [Document.project_id, Document.tenant_id],
    )

    # Document versions relationship
    document_versions = relationship(
        "DocumentVersion",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Agent executions relationship
    agent_executions = relationship(
        "AgentExecution",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Exports relationship
    exports = relationship(
        "Export",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

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
