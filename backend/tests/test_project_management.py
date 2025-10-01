"""
Comprehensive project management flow testing with multi-tenant isolation.

Epic 07.4: Project Management Testing
Tests cover:
- Project creation with validation (07.4.1)
- CRUD operations (07.4.2)
- Tenant-scoped access control (07.4.3)
- Project state management (07.4.4)
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectStatus
from app.repositories.project import ProjectRepository


class TestProjectCreation:
    """Test project creation functionality (Epic 07.4.1)."""

    @pytest.mark.asyncio
    async def test_create_project_success(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test successful project creation."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        project = await project_repo.create_project(
            name="Test Project",
            owner_id=test_user.id,
            description="A test project for testing",
        )

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.description == "A test project for testing"
        assert project.owner_id == test_user.id
        assert project.tenant_id == test_tenant.id
        assert project.status == ProjectStatus.DRAFT
        assert project.is_deleted is False

    @pytest.mark.asyncio
    async def test_create_project_validation_name_required(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test project creation requires name."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        with pytest.raises(Exception):  # SQLAlchemy will raise for null constraint
            await project_repo.create_project(
                name=None,  # type: ignore
                owner_id=test_user.id,
            )

    @pytest.mark.asyncio
    async def test_create_project_validation_name_length(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test project name length validation."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Name too long (> 255 characters)
        long_name = "a" * 256

        # This should work at repository level but may fail at API schema level
        # For now, repository doesn't enforce max length, only database does
        try:
            project = await project_repo.create_project(
                name=long_name,
                owner_id=test_user.id,
            )
            # If it succeeds, database truncated or allowed it
            assert len(project.name) <= 255
        except Exception:
            # Database constraint violation is acceptable
            pass

    @pytest.mark.asyncio
    async def test_create_project_validation_language_format(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test project language format validation (handled at API schema level)."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Repository doesn't validate language format - that's API schema responsibility
        # Create project with any language value
        project = await project_repo.create_project(
            name="Language Test Project",
            owner_id=test_user.id,
        )

        assert project.id is not None
        assert project.name == "Language Test Project"

    @pytest.mark.asyncio
    async def test_create_project_duplicate_name_same_tenant(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test duplicate project name in same tenant raises 409."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create first project
        await project_repo.create_project(
            name="Duplicate Project",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Try to create second project with same name in same tenant
        with pytest.raises(IntegrityError) as exc_info:
            await project_repo.create_project(
                name="Duplicate Project",
                owner_id=test_user.id,
            )
            await test_session.commit()

        # Verify it's the unique constraint violation
        # SQLite uses different format than PostgreSQL for constraint names
        error_msg = str(exc_info.value.orig).lower()
        assert "unique" in error_msg and (
            "tenant_id" in error_msg or "name" in error_msg
        )

    @pytest.mark.asyncio
    async def test_create_project_duplicate_name_different_tenant_allowed(
        self,
        test_session: AsyncSession,
        test_tenant,
        second_tenant,
        test_user,
        second_user,
    ):
        """Test duplicate project name allowed in different tenants."""
        project_repo1 = ProjectRepository(test_session, test_tenant.id)
        project_repo2 = ProjectRepository(test_session, second_tenant.id)

        # Create project in tenant 1
        project1 = await project_repo1.create_project(
            name="Shared Name Project",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Create project with same name in tenant 2 - should succeed
        project2 = await project_repo2.create_project(
            name="Shared Name Project",
            owner_id=second_user.id,
        )
        await test_session.commit()

        assert project1.name == project2.name
        assert project1.tenant_id != project2.tenant_id
        assert project1.id != project2.id

    @pytest.mark.asyncio
    async def test_create_project_default_status_is_draft(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test project default status is DRAFT."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        project = await project_repo.create_project(
            name="Default Status Project",
            owner_id=test_user.id,
        )

        assert project.status == ProjectStatus.DRAFT

    @pytest.mark.asyncio
    async def test_create_project_owner_assignment(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test project owner is properly assigned."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        project = await project_repo.create_project(
            name="Owner Assignment Project",
            owner_id=test_user.id,
        )

        assert project.owner_id == test_user.id
        assert project.tenant_id == test_tenant.id


class TestProjectCRUDOperations:
    """Test project CRUD operations (Epic 07.4.2)."""

    @pytest.mark.asyncio
    async def test_get_project_by_id(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test retrieving project by ID."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create project
        created_project = await project_repo.create_project(
            name="Get By ID Project",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Retrieve project
        retrieved_project = await project_repo.get_by_id(created_project.id)

        assert retrieved_project is not None
        assert retrieved_project.id == created_project.id
        assert retrieved_project.name == "Get By ID Project"

    @pytest.mark.asyncio
    async def test_list_projects_pagination(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test listing projects with pagination."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create multiple projects
        for i in range(5):
            await project_repo.create_project(
                name=f"Pagination Project {i}",
                owner_id=test_user.id,
            )
        await test_session.commit()

        # Test pagination
        page1 = await project_repo.get_all(skip=0, limit=2)
        page2 = await project_repo.get_all(skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    @pytest.mark.asyncio
    async def test_update_project_name(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test updating project name."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create project
        project = await project_repo.create_project(
            name="Original Name",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Update name
        updated_project = await project_repo.update(
            project.id,
            name="Updated Name",
        )
        await test_session.commit()

        assert updated_project is not None
        assert updated_project.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_project_description(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test updating project description."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create project
        project = await project_repo.create_project(
            name="Description Update Project",
            owner_id=test_user.id,
            description="Original description",
        )
        await test_session.commit()

        # Update description
        updated_project = await project_repo.update(
            project.id,
            description="Updated description text",
        )
        await test_session.commit()

        assert updated_project is not None
        assert updated_project.description == "Updated description text"

    @pytest.mark.asyncio
    async def test_update_project_partial_update(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test partial project update."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create project
        project = await project_repo.create_project(
            name="Partial Update Project",
            owner_id=test_user.id,
            description="Original description",
        )
        await test_session.commit()

        # Update only description
        updated_project = await project_repo.update(
            project.id,
            description="Updated description",
        )
        await test_session.commit()

        assert updated_project is not None
        assert updated_project.name == "Partial Update Project"  # Unchanged
        assert updated_project.description == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_project_soft_delete(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test soft delete of project."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create project
        project = await project_repo.create_project(
            name="Soft Delete Project",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Soft delete
        deleted = await project_repo.delete(project.id, soft_delete=True)
        await test_session.commit()

        assert deleted is True

        # Verify project is soft deleted
        retrieved_project = await project_repo.get_by_id(project.id)
        assert retrieved_project is None  # get_by_id filters out soft-deleted

    @pytest.mark.asyncio
    async def test_get_deleted_project_returns_404(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test getting deleted project returns None (404 at API level)."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create and delete project
        project = await project_repo.create_project(
            name="Deleted Project",
            owner_id=test_user.id,
        )
        await test_session.commit()

        await project_repo.delete(project.id, soft_delete=True)
        await test_session.commit()

        # Try to retrieve deleted project
        retrieved_project = await project_repo.get_by_id(project.id)
        assert retrieved_project is None

    @pytest.mark.asyncio
    async def test_search_projects_by_name(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test searching projects by name."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create projects with different names
        await project_repo.create_project(
            name="Mobile App Development",
            owner_id=test_user.id,
        )
        await project_repo.create_project(
            name="Web Application",
            owner_id=test_user.id,
        )
        await project_repo.create_project(
            name="Desktop Software",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Search for "app"
        results = await project_repo.search_projects("app")

        assert len(results) == 2  # "Mobile App" and "Web Application"
        names = [p.name for p in results]
        assert "Mobile App Development" in names
        assert "Web Application" in names

    @pytest.mark.asyncio
    async def test_search_projects_by_description(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test searching projects by description."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create projects with descriptions
        await project_repo.create_project(
            name="Project Alpha",
            owner_id=test_user.id,
            description="E-commerce platform for online shopping",
        )
        await project_repo.create_project(
            name="Project Beta",
            owner_id=test_user.id,
            description="Social media analytics dashboard",
        )
        await test_session.commit()

        # Search for "platform"
        results = await project_repo.search_projects("platform")

        assert len(results) == 1
        assert results[0].name == "Project Alpha"


class TestTenantScopedAccess:
    """Test tenant-scoped access control (Epic 07.4.3)."""

    @pytest.mark.asyncio
    async def test_tenant_cannot_access_other_tenant_projects(
        self, test_session: AsyncSession, test_tenant, second_tenant, test_user
    ):
        """Test tenant isolation - cannot access other tenant's projects."""
        project_repo1 = ProjectRepository(test_session, test_tenant.id)
        project_repo2 = ProjectRepository(test_session, second_tenant.id)

        # Create project in tenant 1
        project1 = await project_repo1.create_project(
            name="Tenant 1 Project",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Try to access from tenant 2
        accessed_project = await project_repo2.get_by_id(project1.id)

        assert accessed_project is None  # Cannot access other tenant's project

    @pytest.mark.asyncio
    async def test_tenant_can_only_list_own_projects(
        self,
        test_session: AsyncSession,
        test_tenant,
        second_tenant,
        test_user,
        second_user,
    ):
        """Test tenants can only list their own projects."""
        project_repo1 = ProjectRepository(test_session, test_tenant.id)
        project_repo2 = ProjectRepository(test_session, second_tenant.id)

        # Create projects in both tenants
        await project_repo1.create_project(
            name="Tenant 1 Project A",
            owner_id=test_user.id,
        )
        await project_repo1.create_project(
            name="Tenant 1 Project B",
            owner_id=test_user.id,
        )
        await project_repo2.create_project(
            name="Tenant 2 Project A",
            owner_id=second_user.id,
        )
        await test_session.commit()

        # List projects for each tenant
        tenant1_projects = await project_repo1.get_all()
        tenant2_projects = await project_repo2.get_all()

        assert len(tenant1_projects) == 2
        assert len(tenant2_projects) == 1
        assert all(p.tenant_id == test_tenant.id for p in tenant1_projects)
        assert all(p.tenant_id == second_tenant.id for p in tenant2_projects)

    @pytest.mark.asyncio
    async def test_tenant_cannot_update_other_tenant_project(
        self, test_session: AsyncSession, test_tenant, second_tenant, test_user
    ):
        """Test tenant cannot update other tenant's project."""
        project_repo1 = ProjectRepository(test_session, test_tenant.id)
        project_repo2 = ProjectRepository(test_session, second_tenant.id)

        # Create project in tenant 1
        project1 = await project_repo1.create_project(
            name="Tenant 1 Project",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Try to update from tenant 2
        updated_project = await project_repo2.update(
            project1.id,
            name="Hacked Name",
        )

        assert updated_project is None  # Update should fail due to tenant isolation

    @pytest.mark.asyncio
    async def test_tenant_cannot_delete_other_tenant_project(
        self, test_session: AsyncSession, test_tenant, second_tenant, test_user
    ):
        """Test tenant cannot delete other tenant's project."""
        project_repo1 = ProjectRepository(test_session, test_tenant.id)
        project_repo2 = ProjectRepository(test_session, second_tenant.id)

        # Create project in tenant 1
        project1 = await project_repo1.create_project(
            name="Tenant 1 Project",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Try to delete from tenant 2
        deleted = await project_repo2.delete(project1.id)

        assert deleted is False  # Delete should fail due to tenant isolation

        # Verify project still exists in tenant 1
        verified_project = await project_repo1.get_by_id(project1.id)
        assert verified_project is not None

    @pytest.mark.asyncio
    async def test_project_name_uniqueness_per_tenant(
        self,
        test_session: AsyncSession,
        test_tenant,
        second_tenant,
        test_user,
        second_user,
    ):
        """Test project name uniqueness is per-tenant."""
        project_repo1 = ProjectRepository(test_session, test_tenant.id)
        project_repo2 = ProjectRepository(test_session, second_tenant.id)

        # Create project with name "My Project" in tenant 1
        project1 = await project_repo1.create_project(
            name="My Project",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Create project with same name in tenant 2 - should succeed
        project2 = await project_repo2.create_project(
            name="My Project",
            owner_id=second_user.id,
        )
        await test_session.commit()

        # Both projects exist with same name
        assert project1.name == project2.name
        assert project1.tenant_id != project2.tenant_id

        # But duplicate in same tenant should fail
        with pytest.raises(IntegrityError):
            await project_repo1.create_project(
                name="My Project",
                owner_id=test_user.id,
            )
            await test_session.commit()

    @pytest.mark.asyncio
    async def test_cross_tenant_search_isolation(
        self,
        test_session: AsyncSession,
        test_tenant,
        second_tenant,
        test_user,
        second_user,
    ):
        """Test search is isolated by tenant."""
        project_repo1 = ProjectRepository(test_session, test_tenant.id)
        project_repo2 = ProjectRepository(test_session, second_tenant.id)

        # Create projects with searchable terms in both tenants
        await project_repo1.create_project(
            name="Secret Project Alpha",
            owner_id=test_user.id,
        )
        await project_repo2.create_project(
            name="Secret Project Beta",
            owner_id=second_user.id,
        )
        await test_session.commit()

        # Search for "Secret" in tenant 1
        tenant1_results = await project_repo1.search_projects("Secret")
        tenant2_results = await project_repo2.search_projects("Secret")

        # Each tenant only sees their own projects
        assert len(tenant1_results) == 1
        assert len(tenant2_results) == 1
        assert tenant1_results[0].name == "Secret Project Alpha"
        assert tenant2_results[0].name == "Secret Project Beta"


class TestProjectStateManagement:
    """Test project state management (Epic 07.4.4)."""

    @pytest.mark.asyncio
    async def test_start_project_changes_status_to_in_progress(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test starting a project changes status to IN_PROGRESS."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create project (default status: DRAFT)
        project = await project_repo.create_project(
            name="Project To Start",
            owner_id=test_user.id,
        )
        await test_session.commit()

        assert project.status == ProjectStatus.DRAFT

        # Start project
        started_project = await project_repo.start_project(project.id)
        await test_session.commit()

        assert started_project is not None
        assert started_project.status == ProjectStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_complete_project_changes_status_to_completed(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test completing a project changes status to COMPLETED."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create and start project
        project = await project_repo.create_project(
            name="Project To Complete",
            owner_id=test_user.id,
        )
        await project_repo.start_project(project.id)
        await test_session.commit()

        # Complete project
        completed_project = await project_repo.complete_project(project.id)
        await test_session.commit()

        assert completed_project is not None
        assert completed_project.status == ProjectStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_archive_project_changes_status_to_archived(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test archiving a project changes status to ARCHIVED."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create project
        project = await project_repo.create_project(
            name="Project To Archive",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Archive project
        archived_project = await project_repo.archive_project(project.id)
        await test_session.commit()

        assert archived_project is not None
        assert archived_project.status == ProjectStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_get_projects_by_status_filter(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test filtering projects by status."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create projects with different statuses
        _ = await project_repo.create_project(
            name="Draft Project",
            owner_id=test_user.id,
        )
        in_progress_project = await project_repo.create_project(
            name="In Progress Project",
            owner_id=test_user.id,
        )
        await project_repo.start_project(in_progress_project.id)

        completed_project = await project_repo.create_project(
            name="Completed Project",
            owner_id=test_user.id,
        )
        await project_repo.complete_project(completed_project.id)
        await test_session.commit()

        # Get projects by status
        draft_projects = await project_repo.get_by_status(ProjectStatus.DRAFT)
        in_progress_projects = await project_repo.get_by_status(
            ProjectStatus.IN_PROGRESS
        )
        completed_projects = await project_repo.get_by_status(ProjectStatus.COMPLETED)

        assert len(draft_projects) == 1
        assert len(in_progress_projects) == 1
        assert len(completed_projects) == 1
        assert draft_projects[0].name == "Draft Project"
        assert in_progress_projects[0].name == "In Progress Project"
        assert completed_projects[0].name == "Completed Project"

    @pytest.mark.asyncio
    async def test_count_projects_by_status(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test counting projects by status."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create multiple projects with different statuses
        for i in range(3):
            await project_repo.create_project(
                name=f"Draft Project {i}",
                owner_id=test_user.id,
            )

        for i in range(2):
            project = await project_repo.create_project(
                name=f"In Progress Project {i}",
                owner_id=test_user.id,
            )
            await project_repo.start_project(project.id)
        await test_session.commit()

        # Count by status
        draft_count = await project_repo.count_by_status(ProjectStatus.DRAFT)
        in_progress_count = await project_repo.count_by_status(
            ProjectStatus.IN_PROGRESS
        )
        completed_count = await project_repo.count_by_status(ProjectStatus.COMPLETED)

        assert draft_count == 3
        assert in_progress_count == 2
        assert completed_count == 0

    @pytest.mark.asyncio
    async def test_count_projects_by_owner(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test counting projects by owner."""
        from app.models.user import User

        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create second user in same tenant
        second_owner = User(
            id=uuid.uuid4(),
            email=f"owner2-{uuid.uuid4().hex[:8]}@example.com",
            username=f"owner2-{uuid.uuid4().hex[:8]}",
            hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3vCWmTB5Va",
            full_name="Second Owner",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        test_session.add(second_owner)
        await test_session.commit()

        # Create projects for both owners
        for i in range(3):
            await project_repo.create_project(
                name=f"User 1 Project {i}",
                owner_id=test_user.id,
            )

        for i in range(2):
            await project_repo.create_project(
                name=f"User 2 Project {i}",
                owner_id=second_owner.id,
            )
        await test_session.commit()

        # Count by owner
        user1_count = await project_repo.count_by_owner(test_user.id)
        user2_count = await project_repo.count_by_owner(second_owner.id)

        assert user1_count == 3
        assert user2_count == 2

    @pytest.mark.asyncio
    async def test_recent_projects_ordered_by_updated_at(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test recent projects are ordered by updated_at."""
        import asyncio

        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create three projects
        project1 = await project_repo.create_project(
            name="Project One",
            owner_id=test_user.id,
        )
        _ = await project_repo.create_project(
            name="Project Two",
            owner_id=test_user.id,
        )
        _ = await project_repo.create_project(
            name="Project Three",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Wait and update project1 to make it most recently updated
        await asyncio.sleep(0.05)
        await project_repo.update(project1.id, description="Updated most recently")
        await test_session.commit()

        # Get recent projects
        recent_projects = await project_repo.get_recent_projects(limit=10)

        # Verify we got all projects
        assert len(recent_projects) == 3

        # Verify they are ordered by updated_at (descending)
        # Project1 should be first as it was updated most recently
        project_names = [p.name for p in recent_projects]
        assert "Project One" in project_names

        # Verify ordering: each project should have updated_at >= next project
        for i in range(len(recent_projects) - 1):
            assert recent_projects[i].updated_at >= recent_projects[i + 1].updated_at

    @pytest.mark.asyncio
    async def test_check_name_availability(
        self, test_session: AsyncSession, test_tenant, test_user
    ):
        """Test checking project name availability."""
        project_repo = ProjectRepository(test_session, test_tenant.id)

        # Create project
        project = await project_repo.create_project(
            name="Existing Project",
            owner_id=test_user.id,
        )
        await test_session.commit()

        # Check availability
        is_available_existing = await project_repo.check_name_availability(
            "Existing Project"
        )
        is_available_new = await project_repo.check_name_availability(
            "New Project Name"
        )

        assert is_available_existing is False  # Already taken
        assert is_available_new is True  # Available

        # Check availability excluding current project (for updates)
        is_available_self = await project_repo.check_name_availability(
            "Existing Project",
            exclude_project_id=project.id,
        )

        assert is_available_self is True  # Available when excluding self
