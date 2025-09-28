"""
Test repositories for Epic 01 - Multi-tenant foundation.
"""

import uuid

import pytest

from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository


class TestTenantRepository:
    """Test TenantRepository functionality."""

    @pytest.mark.asyncio
    async def test_create_tenant(self, test_session) -> None:
        """Test creating a tenant through repository."""
        repo = TenantRepository(test_session)

        tenant = await repo.create_tenant(
            name="Test Company", slug="test-company", description="A test company"
        )

        assert tenant.id is not None
        assert tenant.name == "Test Company"
        assert tenant.slug == "test-company"
        assert tenant.is_active is True

    @pytest.mark.asyncio
    async def test_get_by_slug(self, test_session) -> None:
        """Test getting tenant by slug."""
        repo = TenantRepository(test_session)

        # Create tenant
        created_tenant = await repo.create_tenant(name="Slug Test", slug="slug-test")

        # Get by slug
        found_tenant = await repo.get_by_slug("slug-test")

        assert found_tenant is not None
        assert found_tenant.id == created_tenant.id
        assert found_tenant.slug == "slug-test"

    @pytest.mark.asyncio
    async def test_get_by_slug_inactive(self, test_session) -> None:
        """Test that inactive tenants are not returned by slug lookup."""
        repo = TenantRepository(test_session)

        # Create and deactivate tenant
        tenant = await repo.create_tenant(name="Inactive", slug="inactive")
        await repo.deactivate_tenant(tenant.id)

        # Try to find inactive tenant
        found_tenant = await repo.get_by_slug("inactive")
        assert found_tenant is None

    @pytest.mark.asyncio
    async def test_get_active_tenants(self, test_session) -> None:
        """Test getting only active tenants."""
        repo = TenantRepository(test_session)

        # Create active tenant
        active_tenant = await repo.create_tenant(name="Active", slug="active")

        # Create and deactivate tenant
        inactive_tenant = await repo.create_tenant(name="Inactive", slug="inactive")
        await repo.deactivate_tenant(inactive_tenant.id)

        # Get active tenants
        active_tenants = await repo.get_active_tenants()

        assert len(active_tenants) >= 1
        tenant_ids = [t.id for t in active_tenants]
        assert active_tenant.id in tenant_ids
        assert inactive_tenant.id not in tenant_ids

    @pytest.mark.asyncio
    async def test_check_slug_availability(self, test_session) -> None:
        """Test checking slug availability."""
        repo = TenantRepository(test_session)

        # Create tenant
        tenant = await repo.create_tenant(name="Test", slug="taken-slug")

        # Check availability
        assert await repo.check_slug_availability("taken-slug") is False
        assert await repo.check_slug_availability("available-slug") is True
        assert (
            await repo.check_slug_availability(
                "taken-slug", exclude_tenant_id=tenant.id
            )
            is True
        )

    @pytest.mark.asyncio
    async def test_update_limits(self, test_session) -> None:
        """Test updating tenant limits."""
        repo = TenantRepository(test_session)

        tenant = await repo.create_tenant(name="Limits", slug="limits")

        updated_tenant = await repo.update_limits(
            tenant.id, max_projects=10, max_storage_mb=1000
        )

        assert updated_tenant is not None
        assert updated_tenant.max_projects == 10
        assert updated_tenant.max_storage_mb == 1000


class TestUserRepository:
    """Test UserRepository functionality."""

    @pytest.fixture
    async def sample_tenant(self, test_session):
        """Create a sample tenant for testing."""
        tenant_repo = TenantRepository(test_session)
        return await tenant_repo.create_tenant(name="Test Tenant", slug="test-tenant")

    @pytest.mark.asyncio
    async def test_create_user(self, test_session, sample_tenant) -> None:
        """Test creating a user through repository."""
        repo = UserRepository(test_session, sample_tenant.id)

        user = await repo.create_user(
            email="test@example.com", username="testuser", full_name="Test User"
        )

        assert user.id is not None
        assert user.tenant_id == sample_tenant.id
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_superuser is False

    @pytest.mark.asyncio
    async def test_get_by_email(self, test_session, sample_tenant) -> None:
        """Test getting user by email."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create user
        created_user = await repo.create_user(
            email="email@example.com", username="emailuser"
        )

        # Get by email
        found_user = await repo.get_by_email("email@example.com")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "email@example.com"

    @pytest.mark.asyncio
    async def test_get_by_username(self, test_session, sample_tenant) -> None:
        """Test getting user by username."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create user
        created_user = await repo.create_user(
            email="username@example.com", username="uniqueuser"
        )

        # Get by username
        found_user = await repo.get_by_username("uniqueuser")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == "uniqueuser"

    @pytest.mark.asyncio
    async def test_get_by_oauth(self, test_session, sample_tenant) -> None:
        """Test getting user by OAuth credentials."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create OAuth user
        oauth_user = await repo.create_oauth_user(
            email="oauth@example.com",
            username="oauthuser",
            full_name="OAuth User",
            oauth_provider="google",
            oauth_id="google_123456",
        )

        # Get by OAuth
        found_user = await repo.get_by_oauth("google", "google_123456")

        assert found_user is not None
        assert found_user.id == oauth_user.id
        assert found_user.oauth_provider == "google"
        assert found_user.oauth_id == "google_123456"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, test_session) -> None:
        """Test that users are isolated by tenant."""
        tenant1_repo = TenantRepository(test_session)
        tenant2_repo = TenantRepository(test_session)

        tenant1 = await tenant1_repo.create_tenant(name="Tenant 1", slug="tenant1")
        tenant2 = await tenant2_repo.create_tenant(name="Tenant 2", slug="tenant2")

        user1_repo = UserRepository(test_session, tenant1.id)
        user2_repo = UserRepository(test_session, tenant2.id)

        # Create users in different tenants
        user1 = await user1_repo.create_user(email="user@tenant1.com", username="user1")
        user2 = await user2_repo.create_user(email="user@tenant2.com", username="user2")

        # Test isolation - user1_repo should not find user2
        found_user = await user1_repo.get_by_email("user@tenant2.com")
        assert found_user is None

        # Test isolation - user2_repo should not find user1
        found_user = await user2_repo.get_by_email("user@tenant1.com")
        assert found_user is None

        # Each repo should find its own user
        found_user1 = await user1_repo.get_by_email("user@tenant1.com")
        found_user2 = await user2_repo.get_by_email("user@tenant2.com")

        assert found_user1 is not None
        assert found_user1.id == user1.id
        assert found_user2 is not None
        assert found_user2.id == user2.id

    @pytest.mark.asyncio
    async def test_check_email_availability(self, test_session, sample_tenant) -> None:
        """Test checking email availability."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create user
        user = await repo.create_user(email="taken@example.com", username="takenuser")

        # Check availability
        assert await repo.check_email_availability("taken@example.com") is False
        assert await repo.check_email_availability("available@example.com") is True
        assert (
            await repo.check_email_availability(
                "taken@example.com", exclude_user_id=user.id
            )
            is True
        )

    @pytest.mark.asyncio
    async def test_check_username_availability(
        self, test_session, sample_tenant
    ) -> None:
        """Test checking username availability."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create user
        user = await repo.create_user(email="test@example.com", username="takenuser")

        # Check availability
        assert await repo.check_username_availability("takenuser") is False
        assert await repo.check_username_availability("availableuser") is True
        assert (
            await repo.check_username_availability("takenuser", exclude_user_id=user.id)
            is True
        )

    @pytest.mark.asyncio
    async def test_check_oauth_availability(self, test_session, sample_tenant) -> None:
        """Test checking OAuth availability."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create OAuth user
        oauth_user = await repo.create_oauth_user(
            email="oauth@example.com",
            username="oauthuser",
            full_name="OAuth User",
            oauth_provider="google",
            oauth_id="google_123456",
        )

        # Check availability
        assert await repo.check_oauth_availability("google", "google_123456") is False
        assert await repo.check_oauth_availability("google", "google_789012") is True
        assert await repo.check_oauth_availability("github", "google_123456") is True
        assert (
            await repo.check_oauth_availability(
                "google", "google_123456", exclude_user_id=oauth_user.id
            )
            is True
        )

    @pytest.mark.asyncio
    async def test_link_unlink_oauth(self, test_session, sample_tenant) -> None:
        """Test linking and unlinking OAuth accounts."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create regular user
        user = await repo.create_user(email="regular@example.com", username="regular")

        # Link OAuth
        linked_user = await repo.link_oauth_account(user.id, "github", "github_789")
        assert linked_user is not None
        assert linked_user.oauth_provider == "github"
        assert linked_user.oauth_id == "github_789"

        # Unlink OAuth
        unlinked_user = await repo.unlink_oauth_account(user.id)
        assert unlinked_user is not None
        assert unlinked_user.oauth_provider is None
        assert unlinked_user.oauth_id is None

    @pytest.mark.asyncio
    async def test_find_user_for_login(self, test_session, sample_tenant) -> None:
        """Test finding user for login by email or username."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create user
        user = await repo.create_user(email="login@example.com", username="loginuser")

        # Find by email
        found_by_email = await repo.find_user_for_login("login@example.com")
        assert found_by_email is not None
        assert found_by_email.id == user.id

        # Find by username
        found_by_username = await repo.find_user_for_login("loginuser")
        assert found_by_username is not None
        assert found_by_username.id == user.id

        # Not found
        not_found = await repo.find_user_for_login("nonexistent@example.com")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_get_active_users(self, test_session, sample_tenant) -> None:
        """Test getting only active users."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create active user
        active_user = await repo.create_user(
            email="active@example.com", username="active"
        )

        # Create and deactivate user
        inactive_user = await repo.create_user(
            email="inactive@example.com", username="inactive"
        )
        await repo.deactivate_user(inactive_user.id)

        # Get active users
        active_users = await repo.get_active_users()

        user_ids = [u.id for u in active_users]
        assert active_user.id in user_ids
        assert inactive_user.id not in user_ids

    @pytest.mark.asyncio
    async def test_get_superusers(self, test_session, sample_tenant) -> None:
        """Test getting superusers."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create regular user
        regular_user = await repo.create_user(
            email="regular@example.com", username="regular"
        )

        # Create superuser
        superuser = await repo.create_user(
            email="super@example.com", username="super", is_superuser=True
        )

        # Get superusers
        superusers = await repo.get_superusers()

        user_ids = [u.id for u in superusers]
        assert superuser.id in user_ids
        assert regular_user.id not in user_ids

    @pytest.mark.asyncio
    async def test_search_users(self, test_session, sample_tenant) -> None:
        """Test searching users."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create users
        await repo.create_user(
            email="john.doe@example.com", username="johndoe", full_name="John Doe"
        )
        await repo.create_user(
            email="jane.smith@example.com", username="janesmith", full_name="Jane Smith"
        )
        await repo.create_user(
            email="bob.jones@example.com", username="bobjones", full_name="Bob Jones"
        )

        # Search by first name
        john_results = await repo.search_users("John")
        assert len(john_results) >= 1
        assert any(u.full_name == "John Doe" for u in john_results)

        # Search by email domain
        example_results = await repo.search_users("example.com")
        assert len(example_results) >= 3

        # Search by username
        jane_results = await repo.search_users("jane")
        assert len(jane_results) >= 1
        assert any(u.username == "janesmith" for u in jane_results)

    @pytest.mark.asyncio
    async def test_get_user_count_by_status(self, test_session, sample_tenant) -> None:
        """Test getting user count statistics."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create users with different statuses
        await repo.create_user(
            email="active1@example.com", username="active1", is_active=True
        )
        await repo.create_user(
            email="active2@example.com", username="active2", is_active=True
        )

        inactive_user = await repo.create_user(
            email="inactive@example.com", username="inactive"
        )
        await repo.deactivate_user(inactive_user.id)

        await repo.create_user(
            email="super@example.com", username="super", is_superuser=True
        )

        # Get counts
        counts = await repo.get_user_count_by_status()

        assert counts["active"] >= 2  # At least 2 active users
        assert counts["inactive"] >= 1  # At least 1 inactive user
        assert counts["superusers"] >= 1  # At least 1 superuser
        assert counts["total"] >= 4  # At least 4 total users


class TestRepositorySoftDelete:
    """Test soft delete functionality in repositories."""

    @pytest.fixture
    async def sample_tenant(self, test_session):
        """Create a sample tenant for testing."""
        tenant_repo = TenantRepository(test_session)
        return await tenant_repo.create_tenant(name="Test Tenant", slug="test-tenant")

    @pytest.mark.asyncio
    async def test_soft_delete_user(self, test_session, sample_tenant) -> None:
        """Test soft deleting a user."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create user
        user = await repo.create_user(email="delete@example.com", username="deleteuser")

        # Soft delete
        success = await repo.delete(user.id, soft_delete=True)
        assert success is True

        # User should not be found by normal queries
        found_user = await repo.get_by_id(user.id)
        assert found_user is None

        found_by_email = await repo.get_by_email("delete@example.com")
        assert found_by_email is None

    @pytest.mark.asyncio
    async def test_hard_delete_user(self, test_session, sample_tenant) -> None:
        """Test hard deleting a user."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Create user
        user = await repo.create_user(
            email="harddelete@example.com", username="harddeleteuser"
        )
        user_id = user.id

        # Hard delete
        success = await repo.delete(user.id, soft_delete=False)
        assert success is True

        # User should not exist at all
        found_user = await repo.get_by_id(user_id)
        assert found_user is None


class TestRepositoryErrorHandling:
    """Test error handling in repositories."""

    @pytest.fixture
    async def sample_tenant(self, test_session):
        """Create a sample tenant for testing."""
        tenant_repo = TenantRepository(test_session)
        return await tenant_repo.create_tenant(name="Test Tenant", slug="test-tenant")

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, test_session, sample_tenant) -> None:
        """Test getting a nonexistent user."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Try to get nonexistent user
        nonexistent_id = uuid.uuid4()
        user = await repo.get_by_id(nonexistent_id)
        assert user is None

    @pytest.mark.asyncio
    async def test_update_nonexistent_user(self, test_session, sample_tenant) -> None:
        """Test updating a nonexistent user."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Try to update nonexistent user
        nonexistent_id = uuid.uuid4()
        result = await repo.update(nonexistent_id, full_name="Updated Name")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, test_session, sample_tenant) -> None:
        """Test deleting a nonexistent user."""
        repo = UserRepository(test_session, sample_tenant.id)

        # Try to delete nonexistent user
        nonexistent_id = uuid.uuid4()
        success = await repo.delete(nonexistent_id)
        assert success is False
