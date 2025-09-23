"""
Role-Based Access Control (RBAC) models for project-level permissions.
"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    ForeignKey,
    Text,
    UniqueConstraint,
    Table,
    DateTime,
    ForeignKeyConstraint,
    and_,
)
from sqlalchemy.orm import relationship, foreign
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum
from .base import BaseModel, Base
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
    'role_permissions',
    Base.metadata,
    Column('tenant_id', UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    Column('role_id', UUID(as_uuid=True), nullable=False, primary_key=True),
    Column('permission_id', UUID(as_uuid=True), nullable=False, primary_key=True),
    ForeignKeyConstraint(
        ['tenant_id', 'role_id'],
        ['roles.tenant_id', 'roles.id'],
        ondelete='CASCADE'
    ),
    ForeignKeyConstraint(
        ['tenant_id', 'permission_id'],
        ['permissions.tenant_id', 'permissions.id'],
        ondelete='CASCADE'
    ),
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
        back_populates="roles",
        primaryjoin=lambda: and_(
            Role.id == foreign(role_permissions.c.role_id),
            Role.tenant_id == foreign(role_permissions.c.tenant_id),
        ),
        secondaryjoin=lambda: and_(
            PermissionModel.id == foreign(role_permissions.c.permission_id),
            PermissionModel.tenant_id == foreign(role_permissions.c.tenant_id),
        ),
        foreign_keys=lambda: [
            role_permissions.c.role_id,
            role_permissions.c.permission_id,
            role_permissions.c.tenant_id,
        ],
    )
    project_members = relationship(
        "ProjectMember",
        back_populates="role",
        primaryjoin=lambda: and_(
            Role.id == foreign(ProjectMember.role_id),
            Role.tenant_id == foreign(ProjectMember.tenant_id),
        ),
        foreign_keys=lambda: [ProjectMember.role_id, ProjectMember.tenant_id],
    )

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
        back_populates="permissions",
        primaryjoin=lambda: and_(
            PermissionModel.id == foreign(role_permissions.c.permission_id),
            PermissionModel.tenant_id == foreign(role_permissions.c.tenant_id),
        ),
        secondaryjoin=lambda: and_(
            Role.id == foreign(role_permissions.c.role_id),
            Role.tenant_id == foreign(role_permissions.c.tenant_id),
        ),
        foreign_keys=lambda: [
            role_permissions.c.role_id,
            role_permissions.c.permission_id,
            role_permissions.c.tenant_id,
        ],
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_permission_tenant_name"),
    )


class ProjectMember(BaseModel):
    """Project membership with role assignment."""

    __tablename__ = "project_members"

    project_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    role_id = Column(UUID(as_uuid=True), nullable=False)
    invited_by_id = Column(UUID(as_uuid=True), nullable=True)
    invited_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    project = relationship(
        "Project",
        back_populates="members",
        primaryjoin=lambda: and_(
            foreign(ProjectMember.project_id) == Project.id,
            foreign(ProjectMember.tenant_id) == Project.tenant_id,
        ),
        foreign_keys=lambda: [ProjectMember.project_id, ProjectMember.tenant_id],
    )
    user = relationship(
        "User",
        foreign_keys=lambda: [ProjectMember.user_id, ProjectMember.tenant_id],
        back_populates="project_memberships",
        primaryjoin=lambda: and_(
            foreign(ProjectMember.user_id) == User.id,
            foreign(ProjectMember.tenant_id) == User.tenant_id,
        ),
    )
    role = relationship(
        "Role",
        back_populates="project_members",
        primaryjoin=lambda: and_(
            foreign(ProjectMember.role_id) == Role.id,
            foreign(ProjectMember.tenant_id) == Role.tenant_id,
        ),
        foreign_keys=lambda: [ProjectMember.role_id, ProjectMember.tenant_id],
    )
    invited_by = relationship(
        "User",
        foreign_keys=lambda: [ProjectMember.invited_by_id, ProjectMember.tenant_id],
        primaryjoin=lambda: and_(
            foreign(ProjectMember.invited_by_id) == User.id,
            foreign(ProjectMember.tenant_id) == User.tenant_id,
        ),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ['tenant_id', 'project_id'],
            ['projects.tenant_id', 'projects.id'],
            ondelete='CASCADE'
        ),
        ForeignKeyConstraint(
            ['tenant_id', 'user_id'],
            ['users.tenant_id', 'users.id'],
            ondelete='CASCADE'
        ),
        ForeignKeyConstraint(
            ['tenant_id', 'role_id'],
            ['roles.tenant_id', 'roles.id'],
            ondelete='CASCADE'
        ),
        ForeignKeyConstraint(
            ['tenant_id', 'invited_by_id'],
            ['users.tenant_id', 'users.id'],
        ),
        UniqueConstraint("tenant_id", "project_id", "user_id", name="uq_project_member_tenant_project_user"),
    )
