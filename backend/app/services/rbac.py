"""
Role-Based Access Control (RBAC) service for managing permissions and roles.
"""

import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from ..models.rbac import Role, PermissionModel, ProjectMember, Permission, ProjectRole
from ..models.user import User
from ..models.project import Project
from ..repositories.base import TenantRepository


class RBACService:
    """Service for RBAC operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.role_repo = TenantRepository(db, Role)
        self.permission_repo = TenantRepository(db, PermissionModel)
        self.member_repo = TenantRepository(db, ProjectMember)

    async def initialize_default_roles_and_permissions(self, tenant_id: uuid.UUID):
        """Initialize default system roles and permissions for a tenant."""

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

        created_permissions = {}
        for perm_name, display_name, resource_type, action in permissions_data:
            permission = PermissionModel(
                tenant_id=tenant_id,
                name=perm_name,
                display_name=display_name,
                description=f"Permission to {action} {resource_type}",
                resource_type=resource_type,
                action=action,
                is_system=True
            )
            self.db.add(permission)
            created_permissions[perm_name] = permission

        await self.db.flush()

        # Create default roles with associated permissions
        roles_config = {
            "OWNER": {
                "display_name": "Project Owner",
                "description": "Full access to project including administration",
                "permissions": [
                    "PROJECT_READ", "PROJECT_WRITE", "PROJECT_DELETE", "PROJECT_ADMIN",
                    "DOCUMENT_READ", "DOCUMENT_WRITE", "DOCUMENT_DELETE",
                    "AGENT_READ", "AGENT_WRITE", "AGENT_DELETE", "AGENT_EXECUTE",
                    "ANALYTICS_READ", "EXPORT_DOCUMENTS"
                ]
            },
            "EDITOR": {
                "display_name": "Project Editor",
                "description": "Can read and write project content",
                "permissions": [
                    "PROJECT_READ", "PROJECT_WRITE",
                    "DOCUMENT_READ", "DOCUMENT_WRITE",
                    "AGENT_READ", "AGENT_WRITE", "AGENT_EXECUTE",
                    "ANALYTICS_READ", "EXPORT_DOCUMENTS"
                ]
            },
            "VIEWER": {
                "display_name": "Project Viewer",
                "description": "Read-only access to project content",
                "permissions": [
                    "PROJECT_READ",
                    "DOCUMENT_READ",
                    "AGENT_READ",
                    "ANALYTICS_READ", "EXPORT_DOCUMENTS"
                ]
            }
        }

        for role_name, config in roles_config.items():
            role = Role(
                tenant_id=tenant_id,
                name=role_name,
                display_name=config["display_name"],
                description=config["description"],
                is_system=True,
                is_active=True
            )

            # Add permissions to role
            for perm_name in config["permissions"]:
                if perm_name in created_permissions:
                    role.permissions.append(created_permissions[perm_name])

            self.db.add(role)

        await self.db.commit()

    async def get_user_permissions(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID
    ) -> List[Permission]:
        """Get all permissions for a user in a specific project."""

        # Get user's role in the project
        membership = await self.member_repo.get_by_fields(
            user_id=user_id,
            project_id=project_id,
            is_active=True
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
        project_id: uuid.UUID,
        required_permission: Permission
    ) -> bool:
        """Check if user has specific permission in project."""

        user_permissions = await self.get_user_permissions(user_id, project_id)
        return required_permission in user_permissions

    async def add_project_member(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role_name: str,
        invited_by_id: uuid.UUID
    ) -> ProjectMember:
        """Add user to project with specified role."""

        # Get role by name
        role = await self.role_repo.get_by_field("name", role_name)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_name}' not found"
            )

        # Check if user is already a member
        existing_membership = await self.member_repo.get_by_fields(
            user_id=user_id,
            project_id=project_id
        )

        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this project"
            )

        # Create membership
        from datetime import datetime
        membership = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role_id=role.id,
            invited_by_id=invited_by_id,
            invited_at=datetime.utcnow(),
            joined_at=datetime.utcnow(),
            is_active=True
        )

        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)

        return membership

    async def remove_project_member(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Remove user from project."""

        membership = await self.member_repo.get_by_fields(
            user_id=user_id,
            project_id=project_id
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this project"
            )

        await self.member_repo.delete(membership[0].id)
        return True

    async def update_member_role(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        new_role_name: str
    ) -> ProjectMember:
        """Update user's role in project."""

        # Get new role
        new_role = await self.role_repo.get_by_field("name", new_role_name)
        if not new_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{new_role_name}' not found"
            )

        # Get membership
        membership = await self.member_repo.get_by_fields(
            user_id=user_id,
            project_id=project_id
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this project"
            )

        # Update role
        updated_membership = await self.member_repo.update(
            membership[0].id,
            role_id=new_role.id
        )

        return updated_membership

    async def get_project_members(
        self,
        project_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all members of a project with their roles."""

        memberships = await self.member_repo.get_all(
            skip=skip,
            limit=limit,
            filters={"project_id": project_id, "is_active": True}
        )

        result = []
        for membership in memberships:
            user = await membership.user
            role = await membership.role

            result.append({
                "user_id": membership.user_id,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name
                },
                "role": {
                    "id": role.id,
                    "name": role.name,
                    "display_name": role.display_name
                },
                "joined_at": membership.joined_at,
                "invited_by_id": membership.invited_by_id
            })

        return result

    async def get_user_projects(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all projects where user is a member."""

        memberships = await self.member_repo.get_all(
            skip=skip,
            limit=limit,
            filters={"user_id": user_id, "is_active": True}
        )

        result = []
        for membership in memberships:
            project = await membership.project
            role = await membership.role

            result.append({
                "project_id": membership.project_id,
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "status": project.status
                },
                "role": {
                    "id": role.id,
                    "name": role.name,
                    "display_name": role.display_name
                },
                "joined_at": membership.joined_at
            })

        return result

    async def is_project_owner(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID
    ) -> bool:
        """Check if user is owner of the project."""

        return await self.check_permission(
            user_id,
            project_id,
            Permission.PROJECT_ADMIN
        )

    async def can_manage_project(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID
    ) -> bool:
        """Check if user can manage project (write access)."""

        return await self.check_permission(
            user_id,
            project_id,
            Permission.PROJECT_WRITE
        )