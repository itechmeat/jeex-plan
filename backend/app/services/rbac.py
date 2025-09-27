"""
Role-Based Access Control (RBAC) service for managing permissions and roles.
"""

import uuid
from datetime import UTC
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.rbac import Permission, PermissionModel, ProjectMember, Role
from ..repositories.base import TenantRepository


class RBACService:
    """Service for RBAC operations."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        if tenant_id is None:
            raise ValueError("tenant_id is required for RBACService")

        self.db = db
        self.tenant_id = tenant_id
        self.role_repo = TenantRepository(db, Role, tenant_id)
        self.permission_repo = TenantRepository(db, PermissionModel, tenant_id)
        self.member_repo = TenantRepository(db, ProjectMember, tenant_id)

    async def initialize_default_roles_and_permissions(
        self, tenant_id: uuid.UUID | None = None
    ) -> None:
        """Initialize default system roles and permissions for a tenant."""

        tenant_id = tenant_id or getattr(self, "tenant_id", None)
        if tenant_id is None:
            raise ValueError(
                "tenant_id is required to initialize roles and permissions"
            )

        # Create default permissions
        permissions_data = [
            # Project permissions
            ("PROJECT_READ", "Read Project", "project", "read"),
            ("PROJECT_WRITE", "Write Project", "project", "write"),
            ("PROJECT_DELETE", "Delete Project", "project", "delete"),
            ("PROJECT_ADMIN", "Admin Project", "project", "admin"),
            # Document permissions
            ("DOCUMENT_READ", "Read Document", "document", "read"),
            ("DOCUMENT_WRITE", "Write Document", "document", "write"),
            ("DOCUMENT_DELETE", "Delete Document", "document", "delete"),
            # Agent permissions
            ("AGENT_READ", "Read Agent", "agent", "read"),
            ("AGENT_WRITE", "Write Agent", "agent", "write"),
            ("AGENT_DELETE", "Delete Agent", "agent", "delete"),
            ("AGENT_EXECUTE", "Execute Agent", "agent", "execute"),
            # Analytics permissions
            ("ANALYTICS_READ", "Read Analytics", "analytics", "read"),
            # Export permissions
            ("EXPORT_DOCUMENTS", "Export Documents", "export", "documents"),
        ]

        permission_names = [perm[0] for perm in permissions_data]
        existing_permissions_result = await self.db.execute(
            select(PermissionModel).where(
                PermissionModel.tenant_id == tenant_id,
                PermissionModel.name.in_(permission_names),
            )
        )
        created_permissions = {
            permission.name: permission
            for permission in existing_permissions_result.scalars().all()
        }

        permissions_created = False
        for perm_name, display_name, resource_type, action in permissions_data:
            if perm_name in created_permissions:
                continue

            permission = PermissionModel(
                tenant_id=tenant_id,
                name=perm_name,
                display_name=display_name,
                description=f"Permission to {action} {resource_type}",
                resource_type=resource_type,
                action=action,
                is_system=True,
            )
            self.db.add(permission)
            created_permissions[perm_name] = permission
            permissions_created = True

        if permissions_created:
            await self.db.flush()

        # Create default roles with associated permissions
        roles_config = {
            "OWNER": {
                "display_name": "Project Owner",
                "description": "Full access to project including administration",
                "permissions": [
                    "PROJECT_READ",
                    "PROJECT_WRITE",
                    "PROJECT_DELETE",
                    "PROJECT_ADMIN",
                    "DOCUMENT_READ",
                    "DOCUMENT_WRITE",
                    "DOCUMENT_DELETE",
                    "AGENT_READ",
                    "AGENT_WRITE",
                    "AGENT_DELETE",
                    "AGENT_EXECUTE",
                    "ANALYTICS_READ",
                    "EXPORT_DOCUMENTS",
                ],
            },
            "EDITOR": {
                "display_name": "Project Editor",
                "description": "Can read and write project content",
                "permissions": [
                    "PROJECT_READ",
                    "PROJECT_WRITE",
                    "DOCUMENT_READ",
                    "DOCUMENT_WRITE",
                    "AGENT_READ",
                    "AGENT_WRITE",
                    "AGENT_EXECUTE",
                    "ANALYTICS_READ",
                    "EXPORT_DOCUMENTS",
                ],
            },
            "VIEWER": {
                "display_name": "Project Viewer",
                "description": "Read-only access to project content",
                "permissions": [
                    "PROJECT_READ",
                    "DOCUMENT_READ",
                    "AGENT_READ",
                    "ANALYTICS_READ",
                    "EXPORT_DOCUMENTS",
                ],
            },
        }

        role_names = list(roles_config.keys())
        existing_roles_result = await self.db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.tenant_id == tenant_id, Role.name.in_(role_names))
        )
        created_roles = {
            role.name: role for role in existing_roles_result.scalars().all()
        }

        roles_created = False
        for role_name, config in roles_config.items():
            role = created_roles.get(role_name)
            if role is None:
                role = Role(
                    tenant_id=tenant_id,
                    name=role_name,
                    display_name=config["display_name"],
                    description=config["description"],
                    is_system=True,
                    is_active=True,
                )
                self.db.add(role)
                created_roles[role_name] = role
                roles_created = True

            # Add missing permissions to role
            required_permissions = [
                created_permissions[perm_name] for perm_name in config["permissions"]
            ]
            for permission in required_permissions:
                if permission not in role.permissions:
                    role.permissions.append(permission)

        if roles_created:
            await self.db.flush()

        await self.db.commit()

    async def get_user_permissions(
        self, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[Permission]:
        """Get all permissions for a user in a specific project."""

        # Get user's role in the project
        membership = await self.member_repo.get_by_fields(
            user_id=user_id, project_id=project_id, is_active=True
        )

        if not membership:
            return []

        # Get role's permissions
        role = await self.role_repo.get_by_id(membership[0].role_id)
        if not role:
            return []

        return [Permission(perm.name) for perm in role.permissions]

    async def check_permission(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID | None,
        permission: Permission,
    ) -> bool:
        """Check if a user has a specific permission, optionally scoped to a project."""

        # Validate user exists and is active inside tenant
        from sqlalchemy import select

        from ..models.user import User

        user_stmt = select(User).where(
            User.id == user_id,
            User.tenant_id == self.tenant_id,
            User.is_active.is_(True),
            User.is_deleted.is_(False),
        )
        result = await self.db.execute(user_stmt)
        user = result.scalar_one_or_none()
        if not user:
            return False

        # Determine relevant project memberships
        membership_filters: dict[str, Any] = {
            "user_id": user_id,
            "is_active": True,
        }
        if project_id:
            membership_filters["project_id"] = project_id

        memberships = await self.member_repo.get_by_fields(**membership_filters)
        if not memberships:
            return False

        # Gather unique role IDs to minimize duplicate lookups
        role_ids = {membership.role_id for membership in memberships}

        for role_id in role_ids:
            role = await self.role_repo.get_by_id(role_id)
            if not role:
                continue

            if any(perm.name == permission.value for perm in role.permissions):
                return True

        return False

    async def add_project_member(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role_name: str,
        invited_by_id: uuid.UUID,
    ) -> ProjectMember:
        """Add user to project with specified role."""

        # Get role by name
        role = await self.role_repo.get_by_field("name", role_name)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_name}' not found",
            )

        # Check if user is already a member
        existing_membership = await self.member_repo.get_by_fields(
            user_id=user_id, project_id=project_id
        )

        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this project",
            )

        # Create membership
        from datetime import datetime

        membership = ProjectMember(
            tenant_id=self.tenant_id,
            project_id=project_id,
            user_id=user_id,
            role_id=role.id,
            invited_by_id=invited_by_id,
            invited_at=datetime.now(UTC),
            joined_at=datetime.now(UTC),
            is_active=True,
        )

        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)

        return membership

    async def remove_project_member(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Remove user from project."""

        membership = await self.member_repo.get_by_fields(
            user_id=user_id, project_id=project_id
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this project",
            )

        await self.member_repo.delete(membership[0].id)
        return True

    async def update_member_role(
        self, project_id: uuid.UUID, user_id: uuid.UUID, new_role_name: str
    ) -> ProjectMember:
        """Update user's role in project."""

        # Get new role
        new_role = await self.role_repo.get_by_field("name", new_role_name)
        if not new_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{new_role_name}' not found",
            )

        # Get membership
        membership = await self.member_repo.get_by_fields(
            user_id=user_id, project_id=project_id
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this project",
            )

        # Update role
        updated_membership = await self.member_repo.update(
            membership[0].id, role_id=new_role.id
        )
        if not updated_membership:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update member role",
            )

        return updated_membership

    async def get_project_members(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get all members of a project with their roles."""

        # Use direct query with eager loading to avoid N+1 pattern
        stmt = (
            select(ProjectMember)
            .options(selectinload(ProjectMember.user), selectinload(ProjectMember.role))
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.tenant_id == self.tenant_id,
                ProjectMember.is_active.is_(True),
                ProjectMember.is_deleted.is_(False),
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        memberships = list(result.scalars().all())

        return [
            {
                "user_id": membership.user_id,
                "user": {
                    "id": membership.user.id,
                    "email": membership.user.email,
                    "username": membership.user.username,
                    "full_name": membership.user.full_name,
                },
                "role": {
                    "id": membership.role.id,
                    "name": membership.role.name,
                    "display_name": membership.role.display_name,
                },
                "joined_at": membership.joined_at,
                "invited_by_id": membership.invited_by_id,
            }
            for membership in memberships
        ]

    async def get_user_projects(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get all projects where user is a member."""

        memberships = await self.member_repo.get_all_with_eager(
            skip=skip,
            limit=limit,
            filters={"user_id": user_id, "is_active": True},
            eager_loads=["project", "role"],
        )

        result = []
        for membership in memberships:
            result.append(
                {
                    "project_id": membership.project_id,
                    "project": {
                        "id": membership.project.id,
                        "name": membership.project.name,
                        "description": membership.project.description,
                        "status": membership.project.status,
                    },
                    "role": {
                        "id": membership.role.id,
                        "name": membership.role.name,
                        "display_name": membership.role.display_name,
                    },
                    "joined_at": membership.joined_at,
                }
            )

        return result

    async def is_project_owner(self, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        """Check if user is owner of the project."""

        return await self.check_permission(
            user_id,
            project_id,
            Permission.PROJECT_ADMIN,
        )

    async def can_manage_project(
        self, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> bool:
        """Check if user can manage project (write access)."""

        return await self.check_permission(
            user_id,
            project_id,
            Permission.PROJECT_WRITE,
        )
