"""
Role-Based Access Control (RBAC) models for project-level permissions.
"""

from sqlalchemy import Column, String, Boolean, ForeignKey, Text, UniqueConstraint, Table, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
from .base import BaseModel, Base


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
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)


class Role(BaseModel):
    """Role entity for RBAC system."""

    __tablename__ = "roles"

    name = Column(String(100), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles cannot be deleted
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    permissions = relationship(
        "PermissionModel",
        secondary=role_permissions,
        back_populates="roles"
    )
    project_members = relationship("ProjectMember", back_populates="role")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )


class PermissionModel(BaseModel):
    """Permission entity for RBAC system."""

    __tablename__ = "permissions"

    name = Column(String(100), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    resource_type = Column(String(50), nullable=False)  # project, document, agent, etc.
    action = Column(String(50), nullable=False)  # read, write, delete, admin, execute
    is_system = Column(Boolean, default=False, nullable=False)  # System permissions cannot be deleted

    # Relationships
    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_permission_tenant_name"),
    )


class ProjectMember(BaseModel):
    """Project membership with role assignment."""

    __tablename__ = "project_members"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invited_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="project_memberships")
    role = relationship("Role", back_populates="project_members")
    invited_by = relationship("User", foreign_keys=[invited_by_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "user_id", name="uq_project_member_tenant_project_user"),
    )