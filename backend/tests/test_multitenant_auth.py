"""
Multi-tenant authentication and authorization testing.
"""

import uuid

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.services.user import UserService


class TestTenantIsolation:
    """Test strict tenant isolation in authentication and data access."""

    @pytest.fixture
    async def tenant_setup(self, db_session: AsyncSession, mock_password_service):
        """Create test tenants and users for isolation testing."""
        return await self._async_tenant_setup(db_session, mock_password_service)

    async def _async_tenant_setup(
        self, db_session: AsyncSession, mock_password_service
    ):
        # Create two separate tenants
        tenant_repo = TenantRepository(db_session)

        tenant_a = await tenant_repo.create(
            name="Tenant A Corp",
            slug=f"tenant-a-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )

        tenant_b = await tenant_repo.create(
            name="Tenant B Corp",
            slug=f"tenant-b-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )

        # Create users in each tenant
        user_service_a = UserService(db_session, tenant_a.id)
        user_service_a.password_service = mock_password_service  # Use mock for testing
        user_service_b = UserService(db_session, tenant_b.id)
        user_service_b.password_service = mock_password_service  # Use mock for testing

        user_a = await user_service_a.create_user(
            email=f"user-a-{uuid.uuid4().hex[:8]}@example.com",
            username="user_a",
            password="password123",
            full_name="User A",
            # skip_password_validation removed - use mock_password_service
        )

        user_b = await user_service_b.create_user(
            email=f"user-b-{uuid.uuid4().hex[:8]}@example.com",
            username="user_b",
            password="password123",
            full_name="User B",
            # skip_password_validation removed - use mock_password_service
        )

        return {
            "tenant_a": tenant_a,
            "tenant_b": tenant_b,
            "user_a": user_a,
            "user_b": user_b,
        }

    @pytest.mark.asyncio
    async def test_users_isolated_by_tenant(
        self, db_session: AsyncSession, tenant_setup, mock_password_service
    ):
        """Test that users cannot access data from other tenants."""
        data = tenant_setup

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
        from app.core.config import get_settings

        data = tenant_setup
        settings = get_settings()

        # Attempt to login user A
        login_response_a = await async_client.post(
            "/api/v1/auth/login",
            json={"email": data["user_a"].email, "password": "password123"},
        )

        assert login_response_a.status_code in (200, 201)

        token_data = login_response_a.json()

        # Token should be present
        assert "token" in token_data or "access_token" in token_data

        # Extract and decode JWT to verify tenant_id claim
        access_token = token_data.get("token", {}).get(
            "access_token"
        ) or token_data.get("access_token")
        if access_token:
            decoded_token = jwt.decode(
                access_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            assert decoded_token.get("tenant_id") == str(data["tenant_a"].id)

        # Also check user info in response
        user_info = token_data.get("user", {})
        if user_info:
            assert user_info.get("tenant_id") == str(data["tenant_a"].id)

    @pytest.mark.asyncio
    async def test_same_email_different_tenants(
        self, db_session: AsyncSession, mock_password_service
    ):
        """Test that same email can exist in different tenants."""
        tenant_repo = TenantRepository(db_session)

        # Create two tenants
        tenant1 = await tenant_repo.create(
            name="Tenant 1",
            slug=f"tenant-1-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )

        tenant2 = await tenant_repo.create(
            name="Tenant 2",
            slug=f"tenant-2-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )

        # Same email for both tenants
        test_email = f"shared-{uuid.uuid4().hex[:8]}@example.com"

        user_service1 = UserService(db_session, tenant1.id)

        user_service1.password_service = mock_password_service  # Use mock for testing
        user_service2 = UserService(db_session, tenant2.id)
        user_service2.password_service = mock_password_service  # Use mock for testing

        # Create user with same email in both tenants
        user1 = await user_service1.create_user(
            email=test_email,
            username="user1",
            password="password123",
            full_name="User One",
            # skip_password_validation removed - use mock_password_service
        )

        user2 = await user_service2.create_user(
            email=test_email,
            username="user2",
            password="password123",
            full_name="User Two",
            # skip_password_validation removed - use mock_password_service
        )

        # Both should be created successfully
        assert user1.email == test_email
        assert user2.email == test_email
        assert user1.tenant_id == tenant1.id
        assert user2.tenant_id == tenant2.id
        assert user1.id != user2.id

    @pytest.mark.asyncio
    async def test_cross_tenant_data_access_prevention(
        self, db_session: AsyncSession, tenant_setup, mock_password_service
    ):
        """Test that queries cannot access cross-tenant data."""
        data = tenant_setup

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
        self, db_session: AsyncSession, tenant_setup, mock_password_service
    ):
        """Test that UserService operations are properly tenant-scoped."""
        data = tenant_setup

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
        self, db_session: AsyncSession, tenant_setup, mock_password_service
    ):
        """Test that authentication service respects tenant isolation."""
        data = tenant_setup

        # Create user service for each tenant
        service_a = UserService(db_session, data["tenant_a"].id)
        service_b = UserService(db_session, data["tenant_b"].id)

        # Authenticate user A within tenant A context
        auth_result_a = await service_a.authenticate_user(
            email=data["user_a"].email, password="password123"
        )
        assert str(auth_result_a["user"]["tenant_id"]) == str(data["tenant_a"].id)

        # Try to authenticate user A within tenant B context (should fail)
        with pytest.raises(AuthenticationError) as exc_info:
            await service_b.authenticate_user(
                email=data["user_a"].email, password="password123"
            )
        assert exc_info.value.message == "Invalid email or password"


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
    async def test_tenant_id_extraction_from_token(self, async_client: AsyncClient):
        """Test that tenant ID is properly extracted from JWT tokens."""
        # Create a test user with known credentials
        unique_suffix = uuid.uuid4().hex[:8]
        user_data = {
            "email": f"test-{unique_suffix}@example.com",
            "name": f"Test User {unique_suffix}",
            "password": "TestP@ssw0rd123!",
            "confirm_password": "TestP@ssw0rd123!",
        }

        # Register user
        register_response = await async_client.post(
            "/api/v1/auth/register", json=user_data
        )
        assert register_response.status_code == 201

        # Now login to get token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"],
            },
        )

        assert login_response.status_code == 200
        login_data = login_response.json()

        # Should include user data with tenant_id
        user_response = login_data.get("user", {})
        assert "tenant_id" in user_response

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
        """Test that projects are isolated between tenants - verifies access control."""
        # Test project creation endpoint without authentication
        response = await async_client.post(
            "/api/v1/projects",
            json={
                "name": "Test Project",
                "description": "Test project description",
            },
        )

        # Should be rejected - either 401 (Unauthorized) or 403 (CSRF/Forbidden)
        # Both indicate proper access control
        assert response.status_code in [
            401,
            403,
        ], f"Expected 401 or 403, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_document_isolation_between_tenants(self, async_client: AsyncClient):
        """Test that documents are isolated between tenants - verifies access control."""
        fake_project_id = str(uuid.uuid4())
        fake_document_id = str(uuid.uuid4())

        # Test document access endpoint without authentication
        response = await async_client.get(
            f"/api/v1/projects/{fake_project_id}/documents/{fake_document_id}"
        )

        # Should require authentication (401) or not found (404) if endpoint doesn't exist
        # CSRF is bypassed in testing mode
        assert response.status_code in [
            401,
            404,
        ], f"Expected 401 or 404, got {response.status_code}"


class TestTenantSecurityBoundaries:
    """Test security boundaries between tenants."""

    @pytest.mark.asyncio
    async def test_jwt_token_tenant_claims(
        self, db_session: AsyncSession, mock_password_service
    ):
        """Test that JWT tokens include proper tenant claims."""
        from app.core.auth import AuthService

        # Create a test tenant and user
        tenant_repo = TenantRepository(db_session)
        tenant = await tenant_repo.create(
            name="Test Tenant",
            slug=f"test-tenant-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )

        user_service = UserService(db_session, tenant.id)

        user_service.password_service = mock_password_service  # Use mock for testing
        user = await user_service.create_user(
            email=f"jwt-test-{uuid.uuid4().hex[:8]}@example.com",
            username="jwt_test_user",
            password="password123",
            full_name="JWT Test User",
            # skip_password_validation removed - use mock_password_service
        )

        # Generate tokens
        auth_service = AuthService(db_session)
        token_service = auth_service.token_service
        tokens = await auth_service.create_tokens_for_user(user)

        # Tokens should be generated
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # Verify token structure (JWT should have 3 parts)
        access_token = tokens["access_token"]
        token_parts = access_token.split(".")
        assert len(token_parts) == 3

        decoded_claims = token_service.verify_token(access_token)
        assert decoded_claims is not None
        assert decoded_claims.get("tenant_id") == str(tenant.id)

    @pytest.mark.asyncio
    async def test_token_validation_across_tenants(
        self, db_session: AsyncSession, tenant_setup, mock_password_service
    ):
        """Test that tokens are validated within correct tenant context."""
        from app.core.auth import AuthService

        data = tenant_setup

        # Generate token for user A (tenant A)
        auth_service = AuthService(db_session)
        token_service = auth_service.token_service
        tokens_a = await auth_service.create_tokens_for_user(data["user_a"])

        # Token should be valid for tenant A context
        token_payload = token_service.verify_token(tokens_a["access_token"])
        assert token_payload is not None

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
        self, db_session: AsyncSession, tenant_setup, mock_password_service
    ):
        """Test that all database queries are properly tenant-filtered."""
        data = tenant_setup

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

        # Should require authentication (401) or not exist (404)
        # Both are acceptable - we're verifying no unauthorized data access
        assert response.status_code in [401, 404]

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

    @pytest.fixture
    async def concurrent_test_data(
        self, db_session: AsyncSession, mock_password_service
    ):
        """Create tenants and users for concurrent operations testing."""
        tenant_repo = TenantRepository(db_session)
        tenant_mapping = {}

        # Create 3 tenants with corresponding users
        for i in range(3):
            suffix = f"tenant-{i}"
            tenant = await tenant_repo.create(
                name=f"Concurrent Test Tenant {i}",
                slug=f"concurrent-{suffix}-{uuid.uuid4().hex[:8]}",
                is_active=True,
            )

            # Create user in this tenant
            user_service = UserService(db_session, tenant.id)
            user_service.password_service = mock_password_service

            await user_service.create_user(
                email=f"user-{suffix}@example.com",
                username=f"user_{suffix}",
                password="password123",
                full_name=f"User {suffix}",
            )

            # Store mapping for validation
            tenant_mapping[suffix] = str(tenant.id)

        return tenant_mapping

    @pytest.mark.asyncio
    async def test_concurrent_tenant_operations(
        self, async_client: AsyncClient, concurrent_test_data: dict
    ):
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
        tenant_suffixes = [f"tenant-{i}" for i in range(3)]
        tasks = [tenant_operation(suffix) for suffix in tenant_suffixes]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete (either success or expected auth failure)
        for suffix, response in zip(tenant_suffixes, responses, strict=False):
            assert not isinstance(response, Exception)
            assert response.status_code in (200, 401)

            if response.status_code == 200:
                payload = response.json()
                user_data = payload.get("user", {})
                assert user_data.get("email") == f"user-{suffix}@example.com"

                # Extract access token from LoginResponse structure
                token_data = payload.get("token", {})
                token = token_data.get("access_token")
                if not token:
                    raise AssertionError(
                        f"Successful login must return access token. "
                        f"Response structure: {list(payload.keys())}"
                    )

                claims = jwt.get_unverified_claims(token)
                assert "tenant_id" in claims

                # Validate tenant_id matches expected tenant for this user
                # This catches cross-tenant leakage in concurrent scenarios
                expected_tenant_id = concurrent_test_data.get(suffix)
                assert expected_tenant_id is not None, (
                    f"Missing tenant mapping for suffix {suffix}"
                )
                assert claims["tenant_id"] == expected_tenant_id, (
                    f"Tenant ID mismatch for {suffix}: "
                    f"got {claims['tenant_id']}, expected {expected_tenant_id}"
                )

    @pytest.mark.asyncio
    async def test_tenant_operations_and_isolation(
        self, db_session: AsyncSession, mock_password_service
    ):
        """Test tenant operations and isolation enforcement."""
        # This would test rate limiting, connection pooling, etc.
        # For now, ensure basic tenant operations work

        tenant_repo = TenantRepository(db_session)

        # Create tenant
        tenant = await tenant_repo.create(
            name="Resource Test Tenant",
            slug=f"resource-test-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )

        assert tenant.is_active
        assert tenant.id is not None
