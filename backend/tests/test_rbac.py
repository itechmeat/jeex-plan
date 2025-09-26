"""
Tests for Role-Based Access Control (RBAC) system.
"""

import uuid

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus
from app.models.rbac import (
    Permission,
    PermissionModel,
    ProjectMember,
    ProjectRole,
    Role,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.services.rbac import RBACService


class TestRBACModels:
    """Test RBAC model functionality."""

    @pytest.fixture
    async def test_tenant(self, async_db: AsyncSession):
        """Create test tenant."""
        tenant = Tenant(
            name="Test Tenant",
            slug=f"test-rbac-tenant-{uuid.uuid4()}",
            description="Test tenant for RBAC",
            is_active=True
        )
        async_db.add(tenant)
        await async_db.commit()
        await async_db.refresh(tenant)
        return tenant

    @pytest.fixture
    async def test_user(self, async_db: AsyncSession, test_tenant):
        """Create test user."""
        user = User(
            tenant_id=test_tenant.id,
            email="rbac@example.com",
            username="rbacuser",
            full_name="RBAC Test User",
            hashed_password="hashed_password",
            is_active=True
        )
        async_db.add(user)
        await async_db.commit()
        await async_db.refresh(user)
        return user

    @pytest.fixture
    async def test_project(self, async_db: AsyncSession, test_tenant, test_user):
        """Create test project."""
        project = Project(
            tenant_id=test_tenant.id,
            name="Test Project",
            description="Test project for RBAC",
            status=ProjectStatus.DRAFT,
            owner_id=test_user.id
        )
        async_db.add(project)
        await async_db.commit()
        await async_db.refresh(project)
        return project

    @pytest.mark.asyncio
    async def test_create_role(self, async_db: AsyncSession, test_tenant) -> None:
        """Test role creation."""
        role = Role(
            tenant_id=test_tenant.id,
            name="TEST_ROLE",
            display_name="Test Role",
            description="Test role for testing",
            is_system=False,
            is_active=True
        )

        async_db.add(role)
        await async_db.commit()
        await async_db.refresh(role)

        assert role.id is not None
        assert role.name == "TEST_ROLE"
        assert role.display_name == "Test Role"
        assert role.is_active is True

    @pytest.mark.asyncio
    async def test_create_permission(self, async_db: AsyncSession, test_tenant) -> None:
        """Test permission creation."""
        permission = PermissionModel(
            tenant_id=test_tenant.id,
            name="TEST_PERMISSION",
            display_name="Test Permission",
            description="Test permission for testing",
            resource_type="test",
            action="read",
            is_system=False
        )

        async_db.add(permission)
        await async_db.commit()
        await async_db.refresh(permission)

        assert permission.id is not None
        assert permission.name == "TEST_PERMISSION"
        assert permission.resource_type == "test"
        assert permission.action == "read"

    @pytest.mark.asyncio
    async def test_role_permission_relationship(self, async_db: AsyncSession, test_tenant) -> None:
        """Test role-permission many-to-many relationship."""
        # Create role
        role = Role(
            tenant_id=test_tenant.id,
            name="TEST_ROLE",
            display_name="Test Role",
            description="Test role",
            is_system=False,
            is_active=True
        )
        async_db.add(role)

        # Create permissions
        perm1 = PermissionModel(
            tenant_id=test_tenant.id,
            name="PERM1",
            display_name="Permission 1",
            description="First permission",
            resource_type="test",
            action="read",
            is_system=False
        )
        perm2 = PermissionModel(
            tenant_id=test_tenant.id,
            name="PERM2",
            display_name="Permission 2",
            description="Second permission",
            resource_type="test",
            action="write",
            is_system=False
        )

        async_db.add_all([perm1, perm2])
        await async_db.commit()

        # Associate permissions with role
        role.permissions.append(perm1)
        role.permissions.append(perm2)
        await async_db.commit()

        # Verify relationship
        await async_db.refresh(role)
        assert len(role.permissions) == 2
        permission_names = [p.name for p in role.permissions]
        assert "PERM1" in permission_names
        assert "PERM2" in permission_names

    @pytest.mark.asyncio
    async def test_project_member_creation(self, async_db: AsyncSession, test_tenant, test_user, test_project) -> None:
        """Test project member creation."""
        # Create role
        role = Role(
            tenant_id=test_tenant.id,
            name="MEMBER_ROLE",
            display_name="Member Role",
            description="Member role",
            is_system=False,
            is_active=True
        )
        async_db.add(role)
        await async_db.commit()
        await async_db.refresh(role)

        # Create project member
        member = ProjectMember(
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            user_id=test_user.id,
            role_id=role.id,
            invited_by_id=test_user.id,
            is_active=True
        )

        async_db.add(member)
        await async_db.commit()
        await async_db.refresh(member)

        assert member.id is not None
        assert member.project_id == test_project.id
        assert member.user_id == test_user.id
        assert member.role_id == role.id
        assert member.is_active is True


class TestRBACService:
    """Test RBACService functionality."""

    @pytest.fixture
    async def rbac_service(self, async_db: AsyncSession, test_tenant):
        """Create RBACService instance."""
        return RBACService(async_db, tenant_id=test_tenant.id)

    @pytest.fixture
    async def test_tenant(self, async_db: AsyncSession):
        """Create test tenant."""
        tenant = Tenant(
            name="RBAC Service Test Tenant",
            slug=f"rbac-service-test-{uuid.uuid4()}",
            description="Test tenant for RBAC service",
            is_active=True
        )
        async_db.add(tenant)
        await async_db.commit()
        await async_db.refresh(tenant)
        return tenant

    @pytest.fixture
    async def test_users(self, async_db: AsyncSession, test_tenant):
        """Create test users."""
        users = []
        for i in range(3):
            user = User(
                tenant_id=test_tenant.id,
                email=f"user{i}@example.com",
                username=f"user{i}",
                full_name=f"User {i}",
                hashed_password="hashed_password",
                is_active=True
            )
            async_db.add(user)
            users.append(user)

        await async_db.commit()
        for user in users:
            await async_db.refresh(user)
        return users

    @pytest.fixture
    async def test_project(self, async_db: AsyncSession, test_tenant, test_users):
        """Create test project."""
        project = Project(
            tenant_id=test_tenant.id,
            name="RBAC Test Project",
            description="Test project for RBAC service",
            status=ProjectStatus.DRAFT,
            owner_id=test_users[0].id
        )
        async_db.add(project)
        await async_db.commit()
        await async_db.refresh(project)
        return project

    @pytest.mark.asyncio
    async def test_initialize_default_roles_and_permissions(self, rbac_service, test_tenant) -> None:
        """Test initialization of default roles and permissions."""
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Check that system roles were created
        owner_role = await rbac_service.role_repo.get_by_field("name", "OWNER")
        editor_role = await rbac_service.role_repo.get_by_field("name", "EDITOR")
        viewer_role = await rbac_service.role_repo.get_by_field("name", "VIEWER")

        assert owner_role is not None
        assert editor_role is not None
        assert viewer_role is not None

        assert owner_role.is_system is True
        assert owner_role.display_name == "Project Owner"

        # Check that permissions were created and associated
        assert len(owner_role.permissions) > 0
        assert len(editor_role.permissions) > 0
        assert len(viewer_role.permissions) > 0

        # Owner should have more permissions than editor
        assert len(owner_role.permissions) > len(editor_role.permissions)
        # Editor should have more permissions than viewer
        assert len(editor_role.permissions) > len(viewer_role.permissions)

    @pytest.mark.asyncio
    async def test_add_project_member(self, rbac_service, test_tenant, test_users, test_project) -> None:
        """Test adding a user to a project with a role."""
        # Initialize default roles
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Add user as editor
        member = await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id,
            role_name="EDITOR",
            invited_by_id=test_users[0].id
        )

        assert member is not None
        assert member.project_id == test_project.id
        assert member.user_id == test_users[1].id
        assert member.is_active is True

    @pytest.mark.asyncio
    async def test_add_project_member_duplicate(self, rbac_service, test_tenant, test_users, test_project) -> None:
        """Test adding the same user twice to a project."""
        # Initialize default roles
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Add user first time
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id,
            role_name="EDITOR",
            invited_by_id=test_users[0].id
        )

        # Try to add same user again
        with pytest.raises(HTTPException) as exc_info:
            await rbac_service.add_project_member(
                project_id=test_project.id,
                user_id=test_users[1].id,
                role_name="VIEWER",
                invited_by_id=test_users[0].id
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already a member" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_add_project_member_invalid_role(self, rbac_service, test_users, test_project) -> None:
        """Test adding member with invalid role."""
        with pytest.raises(HTTPException) as exc_info:
            await rbac_service.add_project_member(
                project_id=test_project.id,
                user_id=test_users[1].id,
                role_name="INVALID_ROLE",
                invited_by_id=test_users[0].id
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Role 'INVALID_ROLE' not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_user_permissions(self, rbac_service, test_tenant, test_users, test_project) -> None:
        """Test getting user permissions for a project."""
        # Initialize default roles
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Add user as editor
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id,
            role_name="EDITOR",
            invited_by_id=test_users[0].id
        )

        # Get user permissions
        permissions = await rbac_service.get_user_permissions(
            user_id=test_users[1].id,
            project_id=test_project.id
        )

        assert len(permissions) > 0
        assert Permission.PROJECT_READ in permissions
        assert Permission.PROJECT_WRITE in permissions
        assert Permission.DOCUMENT_READ in permissions
        assert Permission.DOCUMENT_WRITE in permissions

        # Editor should not have admin permissions
        assert Permission.PROJECT_ADMIN not in permissions

    @pytest.mark.asyncio
    async def test_check_permission(self, rbac_service, test_tenant, test_users, test_project) -> None:
        """Test checking specific permission for user."""
        # Initialize default roles
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Add user as viewer
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id,
            role_name="VIEWER",
            invited_by_id=test_users[0].id
        )

        # Check read permission (should have)
        has_read = await rbac_service.check_permission(
            user_id=test_users[1].id,
            project_id=test_project.id,
            required_permission=Permission.PROJECT_READ
        )
        assert has_read is True

        # Check write permission (should not have)
        has_write = await rbac_service.check_permission(
            user_id=test_users[1].id,
            project_id=test_project.id,
            required_permission=Permission.PROJECT_WRITE
        )
        assert has_write is False

        # Check admin permission (should not have)
        has_admin = await rbac_service.check_permission(
            user_id=test_users[1].id,
            project_id=test_project.id,
            required_permission=Permission.PROJECT_ADMIN
        )
        assert has_admin is False

    @pytest.mark.asyncio
    async def test_update_member_role(self, rbac_service, test_tenant, test_users, test_project) -> None:
        """Test updating member's role in project."""
        # Initialize default roles
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Add user as viewer
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id,
            role_name="VIEWER",
            invited_by_id=test_users[0].id
        )

        # Verify initial permissions
        has_write_before = await rbac_service.check_permission(
            user_id=test_users[1].id,
            project_id=test_project.id,
            required_permission=Permission.PROJECT_WRITE
        )
        assert has_write_before is False

        # Update to editor role
        updated_member = await rbac_service.update_member_role(
            project_id=test_project.id,
            user_id=test_users[1].id,
            new_role_name="EDITOR"
        )

        assert updated_member is not None

        # Verify new permissions
        has_write_after = await rbac_service.check_permission(
            user_id=test_users[1].id,
            project_id=test_project.id,
            required_permission=Permission.PROJECT_WRITE
        )
        assert has_write_after is True

    @pytest.mark.asyncio
    async def test_remove_project_member(self, rbac_service, test_tenant, test_users, test_project) -> None:
        """Test removing user from project."""
        # Initialize default roles
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Add user to project
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id,
            role_name="EDITOR",
            invited_by_id=test_users[0].id
        )

        # Verify user has permissions
        has_permission_before = await rbac_service.check_permission(
            user_id=test_users[1].id,
            project_id=test_project.id,
            required_permission=Permission.PROJECT_READ
        )
        assert has_permission_before is True

        # Remove user from project
        success = await rbac_service.remove_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id
        )
        assert success is True

        # Verify user no longer has permissions
        has_permission_after = await rbac_service.check_permission(
            user_id=test_users[1].id,
            project_id=test_project.id,
            required_permission=Permission.PROJECT_READ
        )
        assert has_permission_after is False

    @pytest.mark.asyncio
    async def test_remove_nonexistent_member(self, rbac_service, test_project, test_users) -> None:
        """Test removing user who is not a project member."""
        with pytest.raises(HTTPException) as exc_info:
            await rbac_service.remove_project_member(
                project_id=test_project.id,
                user_id=test_users[1].id
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not a member" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_project_members(self, rbac_service, test_tenant, test_users, test_project) -> None:
        """Test getting all project members."""
        # Initialize default roles
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Add multiple users to project
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id,
            role_name="EDITOR",
            invited_by_id=test_users[0].id
        )

        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[2].id,
            role_name="VIEWER",
            invited_by_id=test_users[0].id
        )

        # Get project members
        members = await rbac_service.get_project_members(test_project.id)

        assert len(members) == 2
        member_user_ids = [member["user_id"] for member in members]
        assert test_users[1].id in member_user_ids
        assert test_users[2].id in member_user_ids

        # Verify member data structure
        member_data = members[0]
        assert "user" in member_data
        assert "role" in member_data
        assert "joined_at" in member_data
        assert "invited_by_id" in member_data

    @pytest.mark.asyncio
    async def test_get_user_projects(self, rbac_service, test_tenant, test_users, test_project) -> None:
        """Test getting all projects for a user."""
        # Initialize default roles
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Add user to project
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id,
            role_name="EDITOR",
            invited_by_id=test_users[0].id
        )

        # Get user's projects
        projects = await rbac_service.get_user_projects(test_users[1].id)

        assert len(projects) == 1
        assert projects[0]["project_id"] == test_project.id

        # Verify project data structure
        project_data = projects[0]
        assert "project" in project_data
        assert "role" in project_data
        assert "joined_at" in project_data
        assert project_data["project"]["name"] == test_project.name

    @pytest.mark.asyncio
    async def test_is_project_owner(self, rbac_service, test_tenant, test_users, test_project) -> None:
        """Test checking if user is project owner."""
        # Initialize default roles
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Add user as owner
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id,
            role_name="OWNER",
            invited_by_id=test_users[0].id
        )

        # Check if user is owner
        is_owner = await rbac_service.is_project_owner(
            user_id=test_users[1].id,
            project_id=test_project.id
        )
        assert is_owner is True

        # Add different user as editor
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[2].id,
            role_name="EDITOR",
            invited_by_id=test_users[0].id
        )

        # Check if editor is owner (should be false)
        is_editor_owner = await rbac_service.is_project_owner(
            user_id=test_users[2].id,
            project_id=test_project.id
        )
        assert is_editor_owner is False

    @pytest.mark.asyncio
    async def test_can_manage_project(self, rbac_service, test_tenant, test_users, test_project) -> None:
        """Test checking if user can manage project."""
        # Initialize default roles
        await rbac_service.initialize_default_roles_and_permissions(test_tenant.id)

        # Add user as editor (can manage)
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[1].id,
            role_name="EDITOR",
            invited_by_id=test_users[0].id
        )

        can_manage = await rbac_service.can_manage_project(
            user_id=test_users[1].id,
            project_id=test_project.id
        )
        assert can_manage is True

        # Add user as viewer (cannot manage)
        await rbac_service.add_project_member(
            project_id=test_project.id,
            user_id=test_users[2].id,
            role_name="VIEWER",
            invited_by_id=test_users[0].id
        )

        cannot_manage = await rbac_service.can_manage_project(
            user_id=test_users[2].id,
            project_id=test_project.id
        )
        assert cannot_manage is False


class TestPermissionEnums:
    """Test permission enum functionality."""

    def test_permission_enum_values(self) -> None:
        """Test that permission enum has expected values."""
        expected_permissions = [
            "PROJECT_READ", "PROJECT_WRITE", "PROJECT_DELETE", "PROJECT_ADMIN",
            "DOCUMENT_READ", "DOCUMENT_WRITE", "DOCUMENT_DELETE",
            "AGENT_READ", "AGENT_WRITE", "AGENT_DELETE", "AGENT_EXECUTE",
            "ANALYTICS_READ", "EXPORT_DOCUMENTS"
        ]

        for perm_name in expected_permissions:
            assert hasattr(Permission, perm_name)
            assert isinstance(getattr(Permission, perm_name), str)

    def test_project_role_enum_values(self) -> None:
        """Test that project role enum has expected values."""
        expected_roles = ["OWNER", "EDITOR", "VIEWER"]

        for role_name in expected_roles:
            assert hasattr(ProjectRole, role_name)
            assert isinstance(getattr(ProjectRole, role_name), str)

    def test_permission_enum_in_lists(self) -> None:
        """Test that permissions can be used in lists and comparisons."""
        permissions = [Permission.PROJECT_READ, Permission.PROJECT_WRITE]

        assert Permission.PROJECT_READ in permissions
        assert Permission.PROJECT_DELETE not in permissions
        assert len(permissions) == 2
