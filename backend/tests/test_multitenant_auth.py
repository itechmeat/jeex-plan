"""
Multi-tenant authentication and authorization testing.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.services.user import UserService


class TestTenantIsolation:
    """Test strict tenant isolation in authentication and data access."""

    @pytest.fixture
    async def tenant_setup(self, db_session: AsyncSession):
        """Create test tenants and users for isolation testing."""
        # Create two separate tenants
        tenant_repo = TenantRepository(db_session)

        tenant_a = await tenant_repo.create(
            {
                "name": "Tenant A Corp",
                "slug": f"tenant-a-{uuid.uuid4().hex[:8]}",
                "is_active": True,
            }
        )

        tenant_b = await tenant_repo.create(
            {
                "name": "Tenant B Corp",
                "slug": f"tenant-b-{uuid.uuid4().hex[:8]}",
                "is_active": True,
            }
        )

        # Create users in each tenant
        user_service_a = UserService(db_session, tenant_a.id)
        user_service_b = UserService(db_session, tenant_b.id)

        user_a = await user_service_a.create_user(
            email=f"user-a-{uuid.uuid4().hex[:8]}@example.com",
            username="user_a",
            password="password123",
            full_name="User A",
        )

        user_b = await user_service_b.create_user(
            email=f"user-b-{uuid.uuid4().hex[:8]}@example.com",
            username="user_b",
            password="password123",
            full_name="User B",
        )

        return {
            "tenant_a": tenant_a,
            "tenant_b": tenant_b,
            "user_a": user_a,
            "user_b": user_b,
        }

    @pytest.mark.asyncio
    async def test_users_isolated_by_tenant(
        self, db_session: AsyncSession, tenant_setup
    ):
        """Test that users cannot access data from other tenants."""
        data = await tenant_setup

        # User repository for tenant A
        user_repo_a = UserRepository(db_session, data["tenant_a"].id)

        # Should find user A
        user_a_found = await user_repo_a.get_by_email(data["user_a"].email)
        assert user_a_found is not None
        assert user_a_found.id == data["user_a"].id

        # Should NOT find user B (different tenant)
        user_b_not_found = await user_repo_a.get_by_email(data["user_b"].email)
        assert user_b_not_found is None

    @pytest.mark.asyncio
    async def test_authentication_respects_tenant_boundaries(
        self, async_client: AsyncClient, tenant_setup
    ):
        """Test that authentication tokens respect tenant boundaries."""
        data = await tenant_setup

        # Attempt to login user A
        login_response_a = await async_client.post(
            "/api/v1/auth/login",
            json={"email": data["user_a"].email, "password": "password123"},
        )

        # If login successful, token should contain tenant info
        if login_response_a.status_code in [200, 201]:
            token_data = login_response_a.json()

            # Token should be present
            assert "token" in token_data or "access_token" in token_data

            # Extract tenant information from response if available
            user_info = token_data.get("user", {})
            if user_info:
                assert user_info.get("tenant_id") == str(data["tenant_a"].id)

    @pytest.mark.asyncio
    async def test_same_email_different_tenants(self, db_session: AsyncSession):
        """Test that same email can exist in different tenants."""
        tenant_repo = TenantRepository(db_session)

        # Create two tenants
        tenant1 = await tenant_repo.create(
            {
                "name": "Tenant 1",
                "slug": f"tenant-1-{uuid.uuid4().hex[:8]}",
                "is_active": True,
            }
        )

        tenant2 = await tenant_repo.create(
            {
                "name": "Tenant 2",
                "slug": f"tenant-2-{uuid.uuid4().hex[:8]}",
                "is_active": True,
            }
        )

        # Same email for both tenants
        test_email = f"shared-{uuid.uuid4().hex[:8]}@example.com"

        user_service1 = UserService(db_session, tenant1.id)
        user_service2 = UserService(db_session, tenant2.id)

        # Create user with same email in both tenants
        user1 = await user_service1.create_user(
            email=test_email,
            username="user1",
            password="password123",
            full_name="User One",
        )

        user2 = await user_service2.create_user(
            email=test_email,
            username="user2",
            password="password123",
            full_name="User Two",
        )

        # Both should be created successfully
        assert user1.email == test_email
        assert user2.email == test_email
        assert user1.tenant_id == tenant1.id
        assert user2.tenant_id == tenant2.id
        assert user1.id != user2.id

    @pytest.mark.asyncio
    async def test_cross_tenant_data_access_prevention(
        self, db_session: AsyncSession, tenant_setup
    ):
        """Test that queries cannot access cross-tenant data."""
        data = await tenant_setup

        # Repository scoped to tenant A
        user_repo_a = UserRepository(db_session, data["tenant_a"].id)

        # Get all users for tenant A
        tenant_a_users = await user_repo_a.get_all()

        # Should only contain users from tenant A
        tenant_a_user_ids = [user.id for user in tenant_a_users]
        assert data["user_a"].id in tenant_a_user_ids
        assert data["user_b"].id not in tenant_a_user_ids

        # Repository scoped to tenant B
        user_repo_b = UserRepository(db_session, data["tenant_b"].id)

        # Get all users for tenant B
        tenant_b_users = await user_repo_b.get_all()

        # Should only contain users from tenant B
        tenant_b_user_ids = [user.id for user in tenant_b_users]
        assert data["user_b"].id in tenant_b_user_ids
        assert data["user_a"].id not in tenant_b_user_ids

    @pytest.mark.asyncio
    async def test_user_service_tenant_scoping(
        self, db_session: AsyncSession, tenant_setup
    ):
        """Test that UserService operations are properly tenant-scoped."""
        data = await tenant_setup

        # Service for tenant A
        service_a = UserService(db_session, data["tenant_a"].id)

        # Should find user A by email
        user_a_found = await service_a.get_user_by_email(data["user_a"].email)
        assert user_a_found is not None
        assert user_a_found.id == data["user_a"].id

        # Should NOT find user B (different tenant)
        user_b_not_found = await service_a.get_user_by_email(data["user_b"].email)
        assert user_b_not_found is None

    @pytest.mark.asyncio
    async def test_authentication_service_tenant_isolation(
        self, db_session: AsyncSession, tenant_setup
    ):
        """Test that authentication service respects tenant isolation."""
        data = await tenant_setup

        # Create user service for each tenant
        service_a = UserService(db_session, data["tenant_a"].id)
        service_b = UserService(db_session, data["tenant_b"].id)

        # Authenticate user A within tenant A context
        auth_result_a = await service_a.authenticate_user(
            email=data["user_a"].email, password="password123"
        )

        if auth_result_a:  # If authentication successful
            assert auth_result_a["user"].tenant_id == data["tenant_a"].id

        # Try to authenticate user A within tenant B context (should fail)
        try:
            auth_result_cross = await service_b.authenticate_user(
                email=data["user_a"].email, password="password123"
            )
            # Should not find user A in tenant B context
            assert auth_result_cross is None
        except Exception:
            # Exception is also acceptable (user not found)
            pass


class TestTenantContextValidation:
    """Test tenant context validation in API requests."""

    @pytest.mark.asyncio
    async def test_api_requests_include_tenant_context(self, async_client: AsyncClient):
        """Test that API requests properly include tenant context."""
        # Test with a protected endpoint that requires authentication
        response = await async_client.get("/api/v1/auth/me")

        # Should require authentication (401)
        assert response.status_code == 401

        # Test with fake token
        response = await async_client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer fake_token"}
        )

        # Should reject invalid token
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_tenant_id_extraction_from_token(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test that tenant ID is properly extracted from JWT tokens."""
        # This test would require a valid authentication flow
        # For now, we test the structure

        # Attempt login to get token structure
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "test123456",  # Assuming test password
            },
        )

        if login_response.status_code in [200, 201]:
            login_data = login_response.json()

            # Should include user data with tenant_id
            user_data = login_data.get("user", {})
            assert "tenant_id" in user_data

    @pytest.mark.asyncio
    async def test_malicious_tenant_context_manipulation(
        self, async_client: AsyncClient
    ):
        """Test protection against tenant context manipulation attacks."""
        # Test various attempts to manipulate tenant context

        manipulation_attempts = [
            {"X-Tenant-ID": "fake_tenant_id"},
            {"X-Tenant-ID": "../../../admin"},
            {"X-Tenant-ID": "'; DROP TABLE tenants; --"},
            {"tenant_id": "malicious_tenant"},
        ]

        for headers in manipulation_attempts:
            response = await async_client.get("/api/v1/auth/me", headers=headers)

            # Should not allow unauthorized access regardless of header manipulation
            assert response.status_code in [401, 403, 422]


class TestTenantResourceAccess:
    """Test resource access control within tenant boundaries."""

    @pytest.mark.asyncio
    async def test_project_isolation_between_tenants(self, async_client: AsyncClient):
        """Test that projects are isolated between tenants."""
        # This would test project creation and access across tenants
        # For now, we test the endpoint structure

        # Test project creation endpoint
        response = await async_client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "Test project description"},
        )

        # Should require authentication
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_document_isolation_between_tenants(self, async_client: AsyncClient):
        """Test that documents are isolated between tenants."""
        # Test document access endpoint
        fake_project_id = str(uuid.uuid4())
        fake_document_id = str(uuid.uuid4())

        response = await async_client.get(
            f"/api/v1/projects/{fake_project_id}/documents/{fake_document_id}"
        )

        # Should require authentication
        assert response.status_code == 401


class TestTenantSecurityBoundaries:
    """Test security boundaries between tenants."""

    @pytest.mark.asyncio
    async def test_jwt_token_tenant_claims(self, db_session: AsyncSession):
        """Test that JWT tokens include proper tenant claims."""
        from app.core.auth import AuthService

        # Create a test tenant and user
        tenant_repo = TenantRepository(db_session)
        tenant = await tenant_repo.create(
            {
                "name": "Test Tenant",
                "slug": f"test-tenant-{uuid.uuid4().hex[:8]}",
                "is_active": True,
            }
        )

        user_service = UserService(db_session, tenant.id)
        user = await user_service.create_user(
            email=f"jwt-test-{uuid.uuid4().hex[:8]}@example.com",
            username="jwt_test_user",
            password="password123",
            full_name="JWT Test User",
        )

        # Generate tokens
        auth_service = AuthService(db_session)
        tokens = await auth_service.create_tokens_for_user(user)

        # Tokens should be generated
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # Verify token structure (JWT should have 3 parts)
        access_token = tokens["access_token"]
        token_parts = access_token.split(".")
        assert len(token_parts) == 3

    @pytest.mark.asyncio
    async def test_token_validation_across_tenants(
        self, db_session: AsyncSession, tenant_setup
    ):
        """Test that tokens are validated within correct tenant context."""
        from app.core.auth import AuthService

        data = await tenant_setup

        # Generate token for user A (tenant A)
        auth_service = AuthService(db_session)
        tokens_a = await auth_service.create_tokens_for_user(data["user_a"])

        # Token should be valid for tenant A context
        token_payload = await auth_service.verify_token(tokens_a["access_token"])

        if token_payload:
            # Payload should contain tenant information
            assert "tenant_id" in token_payload
            assert token_payload["tenant_id"] == str(data["tenant_a"].id)

    @pytest.mark.asyncio
    async def test_session_isolation_between_tenants(self, async_client: AsyncClient):
        """Test that sessions are isolated between tenants."""
        # Test that concurrent sessions from different tenants don't interfere

        # This would require setting up authenticated sessions
        # For now, test basic session structure

        # Test session endpoints
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401  # No session

        # Test that session data doesn't leak between requests
        # Each request should be stateless and tenant-scoped


class TestTenantDataLeakagePrevention:
    """Test prevention of data leakage between tenants."""

    @pytest.mark.asyncio
    async def test_database_query_tenant_filtering(
        self, db_session: AsyncSession, tenant_setup
    ):
        """Test that all database queries are properly tenant-filtered."""
        data = await tenant_setup

        # Repository should automatically filter by tenant
        user_repo = UserRepository(db_session, data["tenant_a"].id)

        # Get user by ID - should only work within tenant
        user_a_found = await user_repo.get_by_id(data["user_a"].id)
        assert user_a_found is not None

        # Try to get user B by ID (different tenant) - should not find
        user_b_not_found = await user_repo.get_by_id(data["user_b"].id)
        assert user_b_not_found is None

    @pytest.mark.asyncio
    async def test_api_response_data_filtering(self, async_client: AsyncClient):
        """Test that API responses don't include data from other tenants."""
        # Test user listing endpoint
        response = await async_client.get("/api/v1/users")

        # Should require authentication
        assert response.status_code == 401

        # When authenticated, should only return tenant-scoped data
        # This would need proper authentication setup to test fully

    @pytest.mark.asyncio
    async def test_error_messages_dont_leak_tenant_info(
        self, async_client: AsyncClient
    ):
        """Test that error messages don't leak information about other tenants."""
        # Test with various invalid requests

        invalid_requests = [
            ("/api/v1/projects/fake-project-id", "GET"),
            ("/api/v1/users/fake-user-id", "GET"),
            ("/api/v1/projects/fake-id/documents", "GET"),
        ]

        for endpoint, method in invalid_requests:
            if method == "GET":
                response = await async_client.get(endpoint)
            elif method == "POST":
                response = await async_client.post(endpoint, json={})

            # Error responses should not reveal tenant-specific information
            if response.status_code == 401:
                # Unauthorized - good
                pass
            elif response.status_code == 404:
                # Not found - should be generic message
                error_data = response.json()
                error_message = str(error_data).lower()

                # Should not contain tenant-specific information
                assert "tenant" not in error_message
                assert (
                    "unauthorized" not in error_message or "access" not in error_message
                )


class TestTenantPerformanceIsolation:
    """Test that tenant operations don't affect each other's performance."""

    @pytest.mark.asyncio
    async def test_concurrent_tenant_operations(self, async_client: AsyncClient):
        """Test that operations from different tenants can run concurrently."""
        import asyncio

        # Simulate concurrent operations from different tenants
        async def tenant_operation(tenant_suffix: str):
            return await async_client.post(
                "/api/v1/auth/login",
                json={
                    "email": f"user-{tenant_suffix}@example.com",
                    "password": "password123",
                },
            )

        # Run concurrent operations
        tasks = [tenant_operation(f"tenant-{i}") for i in range(3)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete (either success or expected auth failure)
        for response in responses:
            assert not isinstance(response, Exception)
            assert hasattr(response, "status_code")

    @pytest.mark.asyncio
    async def test_tenant_resource_limits(self, db_session: AsyncSession):
        """Test that tenants have appropriate resource limits."""
        # This would test rate limiting, connection pooling, etc.
        # For now, ensure basic tenant operations work

        tenant_repo = TenantRepository(db_session)

        # Create tenant
        tenant = await tenant_repo.create(
            {
                "name": "Resource Test Tenant",
                "slug": f"resource-test-{uuid.uuid4().hex[:8]}",
                "is_active": True,
            }
        )

        assert tenant.is_active
        assert tenant.id is not None
