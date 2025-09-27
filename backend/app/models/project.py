"""Project model with multi-tenant support."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship, remote

from .base import BaseModel

if TYPE_CHECKING:
    from .agent_execution import AgentExecution
    from .document import Document
    from .document_version import DocumentVersion
    from .export import Export
    from .rbac import ProjectMember
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

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus, name="projectstatus"),
        default=ProjectStatus.DRAFT,
        nullable=False,
    )

    # Owner relationship
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    owner: Mapped[User] = relationship(
        "User",
        back_populates="projects",
        primaryjoin=lambda: and_(
            foreign(Project.owner_id) == remote(User.id),
            foreign(Project.tenant_id) == remote(User.tenant_id),
        ),
        foreign_keys=lambda: [Project.owner_id, Project.tenant_id],
    )

    # Tenant relationship
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="projects",
        primaryjoin=lambda: foreign(Project.tenant_id) == remote(Tenant.id),
        foreign_keys=lambda: [Project.tenant_id],
    )

    # Documents relationship
    documents: Mapped[list[Document]] = relationship(
        "Document",
        back_populates="project",
        primaryjoin=lambda: and_(
            foreign(Document.project_id) == remote(Project.id),
            foreign(Document.tenant_id) == remote(Project.tenant_id),
        ),
        foreign_keys=lambda: [Document.project_id, Document.tenant_id],
    )

    # Document versions relationship
    document_versions: Mapped[list[DocumentVersion]] = relationship(
        "DocumentVersion",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Agent executions relationship
    agent_executions: Mapped[list[AgentExecution]] = relationship(
        "AgentExecution",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Exports relationship
    exports: Mapped[list[Export]] = relationship(
        "Export",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # RBAC relationships
    members: Mapped[list[ProjectMember]] = relationship(
        "ProjectMember", back_populates="project"
    )

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
