"""Role-Based Access Control (RBAC) models for project-level permissions."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, BaseModel

if TYPE_CHECKING:
    from .project import Project
    from .user import User


class ProjectRole(str, Enum):
    """Project role enumeration."""

    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class Permission(str, Enum):
    """Permission enumeration."""

    # Project permissions
    PROJECT_READ = "PROJECT_READ"
    PROJECT_WRITE = "PROJECT_WRITE"
    PROJECT_DELETE = "PROJECT_DELETE"
    PROJECT_ADMIN = "PROJECT_ADMIN"

    # Document permissions
    DOCUMENT_READ = "DOCUMENT_READ"
    DOCUMENT_WRITE = "DOCUMENT_WRITE"
    DOCUMENT_DELETE = "DOCUMENT_DELETE"

    # Agent permissions
    AGENT_READ = "AGENT_READ"
    AGENT_WRITE = "AGENT_WRITE"
    AGENT_DELETE = "AGENT_DELETE"
    AGENT_EXECUTE = "AGENT_EXECUTE"

    # Analytics permissions
    ANALYTICS_READ = "ANALYTICS_READ"

    # Export permissions
    EXPORT_DOCUMENTS = "EXPORT_DOCUMENTS"


# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "tenant_id",
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column("role_id", UUID(as_uuid=True), nullable=False, primary_key=True),
    Column("permission_id", UUID(as_uuid=True), nullable=False, primary_key=True),
    ForeignKeyConstraint(
        ["tenant_id", "role_id"], ["roles.tenant_id", "roles.id"], ondelete="CASCADE"
    ),
    ForeignKeyConstraint(
        ["tenant_id", "permission_id"],
        ["permissions.tenant_id", "permissions.id"],
        ondelete="CASCADE",
    ),
)


class Role(BaseModel):
    """Role entity for RBAC system."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # System roles cannot be deleted
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    permissions: Mapped[list[PermissionModel]] = relationship(
        "PermissionModel",
        secondary=role_permissions,
        back_populates="roles",
        primaryjoin="and_(Role.id == role_permissions.c.role_id, Role.tenant_id == role_permissions.c.tenant_id)",
        secondaryjoin="and_(PermissionModel.id == role_permissions.c.permission_id, PermissionModel.tenant_id == role_permissions.c.tenant_id)",
        foreign_keys="[role_permissions.c.role_id, role_permissions.c.permission_id, role_permissions.c.tenant_id]",
        lazy="selectin",  # Async-safe eager loading without unique() requirement
    )
    project_members: Mapped[list[ProjectMember]] = relationship(
        "ProjectMember",
        back_populates="role",
        primaryjoin="and_(Role.id == ProjectMember.role_id, Role.tenant_id == ProjectMember.tenant_id)",
        foreign_keys="[ProjectMember.role_id, ProjectMember.tenant_id]",
        overlaps="members",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )


class PermissionModel(BaseModel):
    """Permission entity for RBAC system."""

    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # project, document, agent, etc.
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # read, write, delete, admin, execute
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # System permissions cannot be deleted

    # Relationships
    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        primaryjoin="and_(PermissionModel.id == role_permissions.c.permission_id, PermissionModel.tenant_id == role_permissions.c.tenant_id)",
        secondaryjoin="and_(Role.id == role_permissions.c.role_id, Role.tenant_id == role_permissions.c.tenant_id)",
        foreign_keys="[role_permissions.c.role_id, role_permissions.c.permission_id, role_permissions.c.tenant_id]",
        lazy="selectin",  # Async-safe eager loading without unique() requirement
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_permission_tenant_name"),
    )


class ProjectMember(BaseModel):
    """Project membership with role assignment."""

    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    invited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="members",
        primaryjoin="and_(ProjectMember.project_id == Project.id, ProjectMember.tenant_id == Project.tenant_id)",
        foreign_keys="[ProjectMember.project_id, ProjectMember.tenant_id]",
        overlaps="project_members,members",
        lazy="selectin",  # Async-safe eager loading without unique() requirement
    )
    user: Mapped[User] = relationship(
        "User",
        foreign_keys="[ProjectMember.user_id, ProjectMember.tenant_id]",
        back_populates="project_memberships",
        primaryjoin="and_(ProjectMember.user_id == User.id, ProjectMember.tenant_id == User.tenant_id)",
        overlaps="project_members,members,project,project_members,role",
        lazy="selectin",  # Async-safe eager loading without unique() requirement
    )
    role: Mapped[Role] = relationship(
        "Role",
        back_populates="project_members",
        primaryjoin="and_(ProjectMember.role_id == Role.id, ProjectMember.tenant_id == Role.tenant_id)",
        foreign_keys="[ProjectMember.role_id, ProjectMember.tenant_id]",
        overlaps="project_members,members,project,user",
        lazy="selectin",  # Async-safe eager loading without unique() requirement
    )
    invited_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys="[ProjectMember.invited_by_id, ProjectMember.tenant_id]",
        primaryjoin="and_(ProjectMember.invited_by_id == User.id, ProjectMember.tenant_id == User.tenant_id)",
        overlaps="project_members,members,project,role,user",
        lazy="selectin",  # Async-safe eager loading without unique() requirement
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "project_id"],
            ["projects.tenant_id", "projects.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["users.tenant_id", "users.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "role_id"],
            ["roles.tenant_id", "roles.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "invited_by_id"],
            ["users.tenant_id", "users.id"],
        ),
        UniqueConstraint(
            "tenant_id",
            "project_id",
            "user_id",
            name="uq_project_member_tenant_project_user",
        ),
    )
