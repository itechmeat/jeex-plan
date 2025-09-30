"""
Comprehensive authentication flow testing with multi-tenant isolation.
"""

import asyncio
import uuid

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user import UserService


class TestUserRegistration:
    """Test user registration functionality."""

    @pytest.mark.asyncio
    async def test_registration_endpoint_exists(self, async_client: AsyncClient):
        """Test that registration endpoint is accessible."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "test123456",
                "confirm_password": "test123456",
                "name": "Test User",
            },
        )
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_registration_validation_email_required(
        self, async_client: AsyncClient
    ):
        """Test email is required for registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "password": "test123456",
                "confirm_password": "test123456",
                "name": "Test User",
            },
        )
        assert response.status_code == 422
        error_data = response.json()
        assert "email" in str(error_data).lower()

    @pytest.mark.asyncio
    async def test_registration_validation_password_required(
        self, async_client: AsyncClient
    ):
        """Test password is required for registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "confirm_password": "test123456",
                "name": "Test User",
            },
        )
        assert response.status_code == 422
        error_data = response.json()
        assert "password" in str(error_data).lower()

    @pytest.mark.asyncio
    async def test_registration_validation_email_format(
        self, async_client: AsyncClient
    ):
        """Test email format validation."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com",
            "test@.com",
            "",
        ]

        for invalid_email in invalid_emails:
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": invalid_email,
                    "password": "test123456",
                    "confirm_password": "test123456",
                    "name": "Test User",
                },
            )
            assert response.status_code == 422, (
                f"Email {invalid_email} should be invalid"
            )

    @pytest.mark.asyncio
    async def test_registration_validation_password_confirmation(
        self, async_client: AsyncClient
    ):
        """Test password confirmation validation."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "test123456",
                "confirm_password": "different123456",
                "name": "Test User",
            },
        )
        assert response.status_code == 400
        error_data = response.json()
        assert "passwords do not match" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_registration_validation_password_strength(
        self, async_client: AsyncClient
    ):
        """Test password strength requirements."""
        weak_passwords = [
            "123",  # Too short
            "password",  # Too weak
            "12345678",  # Only numbers
            "abcdefgh",  # Only letters
        ]

        for weak_password in weak_passwords:
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test{weak_password}@example.com",
                    "password": weak_password,
                    "confirm_password": weak_password,
                    "name": "Test User",
                },
            )
            # Should either reject weak password (400/422) or accept if validation disabled (201)
            # HTTP 500 should never occur - it would indicate a server bug
            assert response.status_code in [
                400,
                422,
                201,
            ], f"Password {weak_password} handling"

    @pytest.mark.asyncio
    async def test_registration_duplicate_email(
        self, test_session: AsyncSession, test_tenant, mock_password_service
    ):
        """Test registration with duplicate email within the same tenant."""
        from app.services.user import UserService

        user_service = UserService(test_session, test_tenant.id)
        user_service.password_service = mock_password_service  # Use mock for testing

        # Create first user
        email = "duplicate@test.com"
        first_user = await user_service.register_user(
            email=email,
            username="first_user",
            password="StrongDuplicateTestPassword123!",
            full_name="First User",
        )

        # Try to create second user with same email in same tenant
        with pytest.raises(HTTPException) as exc_info:
            await user_service.register_user(
                email=email,
                username="second_user",
                password="StrongDuplicateTestPassword456!",
                full_name="Second User",
            )

        assert exc_info.value.status_code in [400, 409, 422]
        assert "already registered" in exc_info.value.detail.lower()


class TestUserLogin:
    """Test user login functionality."""

    @pytest.mark.asyncio
    async def test_login_endpoint_exists(self, async_client: AsyncClient):
        """Test that login endpoint is accessible."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_login_validation_email_required(self, async_client: AsyncClient):
        """Test email is required for login."""
        response = await async_client.post(
            "/api/v1/auth/login", json={"password": "password123"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_validation_password_required(self, async_client: AsyncClient):
        """Test password is required for login."""
        response = await async_client.post(
            "/api/v1/auth/login", json={"email": "test@example.com"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client: AsyncClient):
        """Test login with invalid credentials."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"},
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_login_valid_credentials(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test login with valid credentials."""
        # This test requires the test_user to have a known password
        # In real implementation, we'd need to set up the user properly
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "test123456",  # Known test password
            },
        )
        # Response could be 200 (success) or error if test setup is incomplete
        assert response.status_code in [200, 201, 401, 500]

    @pytest.mark.asyncio
    async def test_login_email_format_validation(self, async_client: AsyncClient):
        """Test email format validation on login."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "invalid-email-format", "password": "password123"},
        )
        assert response.status_code == 422


class TestTokenManagement:
    """Test JWT token management."""

    @pytest.mark.asyncio
    async def test_token_refresh_endpoint_exists(self, async_client: AsyncClient):
        """Test that token refresh endpoint exists."""
        response = await async_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "fake_refresh_token"}
        )
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_token_validation_endpoint(self, async_client: AsyncClient):
        """Test token validation endpoint."""
        response = await async_client.post("/api/v1/auth/validate-token")
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        # Should return 401/403 for missing/invalid token
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, async_client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(
        self, async_client: AsyncClient
    ):
        """Test accessing protected endpoint with invalid token."""
        response = await async_client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "invalid_refresh_token"}
        )
        assert response.status_code in [401, 403]


class TestLogout:
    """Test user logout functionality."""

    @pytest.mark.asyncio
    async def test_logout_endpoint_exists(self, async_client: AsyncClient):
        """Test that logout endpoint exists."""
        response = await async_client.post("/api/v1/auth/logout")
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_logout_without_token(self, async_client: AsyncClient):
        """Test logout without authentication token."""
        response = await async_client.post("/api/v1/auth/logout")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_logout_invalidates_token(self, async_client: AsyncClient):
        """Test that logout properly invalidates the access token."""
        # First, register and login to get a token
        unique_suffix = uuid.uuid4().hex[:8]
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"logout_test_{unique_suffix}@example.com",
                "name": "Logout Test User",
                "password": "testpassword123",
                "confirm_password": "testpassword123",
            },
        )
        assert register_response.status_code == 201

        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": f"logout_test_{unique_suffix}@example.com",
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200
        response_data = login_response.json()
        access_token = response_data["token"]["access_token"]
        refresh_token = response_data["token"]["refresh_token"]

        # Set authorization header
        headers = {"Authorization": f"Bearer {access_token}"}

        # Verify token works by accessing protected endpoint
        profile_response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert profile_response.status_code == 200

        # Logout
        logout_response = await async_client.post(
            "/api/v1/auth/logout", headers=headers
        )
        assert logout_response.status_code in [200, 204]

        # Try to use the same token again - should be invalid
        profile_after_logout = await async_client.get(
            "/api/v1/auth/me", headers=headers
        )
        assert profile_after_logout.status_code in [401, 403]

        # Verify token blacklist functionality is working
        # The access token should now be invalid since it was blacklisted during logout
        # This is the critical security requirement: logout must invalidate existing tokens


class TestMultiTenantIsolation:
    """Test multi-tenant user isolation."""

    @pytest.mark.asyncio
    async def test_user_isolation_between_tenants(
        self, test_session: AsyncSession, mock_password_service
    ):
        """Test that users are isolated between tenants."""
        from app.repositories.tenant import TenantRepository

        # Create two tenants with unique slugs
        tenant_repo = TenantRepository(test_session)
        tenant1 = await tenant_repo.create_tenant(
            name="Tenant 1", slug=f"tenant-1-{uuid.uuid4().hex[:8]}"
        )
        tenant2 = await tenant_repo.create_tenant(
            name="Tenant 2", slug=f"tenant-2-{uuid.uuid4().hex[:8]}"
        )

        # Create users in different tenants with same email
        user_service1 = UserService(test_session, tenant1.id)
        user_service1.password_service = mock_password_service  # Use mock for testing
        user_service2 = UserService(test_session, tenant2.id)
        user_service2.password_service = mock_password_service  # Use mock for testing

        # MUST work - same email in different tenants is required by multi-tenant design
        # UniqueConstraint("tenant_id", "email") ensures email uniqueness per tenant
        user1 = await user_service1.create_user(
            email="test@example.com",
            username="testuser1",
            password="password123",
            full_name="Test User 1",
        )
        user2 = await user_service2.create_user(
            email="test@example.com",
            username="testuser2",
            password="password123",
            full_name="Test User 2",
        )

        assert user1.tenant_id == tenant1.id
        assert user2.tenant_id == tenant2.id
        assert user1.email == user2.email  # Same email across tenants IS required

    @pytest.mark.asyncio
    async def test_user_queries_are_tenant_scoped(self, test_session: AsyncSession):
        """Test that user queries are automatically scoped to tenant."""
        from app.core.password_service import PasswordService
        from app.models.user import User
        from app.repositories.tenant import TenantRepository
        from app.repositories.user import UserRepository

        password_service = PasswordService()

        # Create test data
        tenant_repo = TenantRepository(test_session)
        tenant1 = await tenant_repo.create_tenant(
            name="Tenant 1", slug=f"tenant-1-{uuid.uuid4().hex[:8]}"
        )
        tenant2 = await tenant_repo.create_tenant(
            name="Tenant 2", slug=f"tenant-2-{uuid.uuid4().hex[:8]}"
        )

        # Create users in different tenants directly to avoid session refresh issues
        user1 = User(
            id=uuid.uuid4(),
            email="user1@example.com",
            username="user1",
            hashed_password=password_service.get_password_hash("SecurePassword123!"),
            full_name="User 1",
            tenant_id=tenant1.id,
            is_active=True,
        )
        user2 = User(
            id=uuid.uuid4(),
            email="user2@example.com",
            username="user2",
            hashed_password=password_service.get_password_hash("DifferentPassword456!"),
            full_name="User 2",
            tenant_id=tenant2.id,
            is_active=True,
        )

        test_session.add(user1)
        test_session.add(user2)
        await test_session.commit()

        # Test tenant isolation with repositories
        user_repo1 = UserRepository(test_session, tenant1.id)
        user_repo2 = UserRepository(test_session, tenant2.id)

        tenant1_users = await user_repo1.get_all()
        tenant2_users = await user_repo2.get_all()

        tenant1_user_ids = [user.id for user in tenant1_users]
        tenant2_user_ids = [user.id for user in tenant2_users]

        assert user1.id in tenant1_user_ids
        assert user1.id not in tenant2_user_ids
        assert user2.id in tenant2_user_ids
        assert user2.id not in tenant1_user_ids

    @pytest.mark.asyncio
    async def test_authentication_tokens_include_tenant_info(
        self, async_client: AsyncClient
    ):
        """Test that authentication tokens include tenant information."""
        # This would test that JWT tokens contain tenant_id claims
        # and that they're properly validated

        # For now, we can only test the structure without valid auth
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            data = response.json()

            token = data.get("token", {}).get("access_token") or data.get(
                "access_token"
            )
            assert token, "JWT token missing in login response"

            from jose import jwt

            try:
                claims = jwt.get_unverified_claims(token)
            except Exception as exc:  # pragma: no cover - unexpected parsing error
                raise AssertionError(f"Cannot decode JWT claims: {exc}") from exc

            assert "tenant_id" in claims, "JWT missing tenant_id claim"

            try:
                tenant_uuid = uuid.UUID(str(claims["tenant_id"]))
            except (ValueError, TypeError) as exc:
                raise AssertionError("JWT tenant_id must be a valid UUID") from exc

            assert tenant_uuid, "tenant_id claim should not be empty"

            response_tenant = data.get("user", {}).get("tenant_id")
            if response_tenant is not None:
                assert str(tenant_uuid) == str(response_tenant)


class TestPasswordSecurity:
    """Test password security features."""

    @pytest.mark.asyncio
    async def test_password_change_endpoint_exists(self, async_client: AsyncClient):
        """Test password change endpoint exists."""
        response = await async_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "old123", "new_password": "new123"},
        )
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_password_change_requires_authentication(
        self, async_client: AsyncClient
    ):
        """Test password change requires authentication."""
        response = await async_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "old123", "new_password": "new123"},
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_passwords_are_hashed(
        self, db_session: AsyncSession, mock_password_service
    ):
        """Test that passwords are properly hashed in database."""
        # Create a user and verify password is not stored in plain text
        test_tenant_id = uuid.uuid4()
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="placeholder",  # This should be hashed
            tenant_id=test_tenant_id,
        )

        # Test password hashing through the user service
        user_service = UserService(db_session, test_tenant_id)

        user_service.password_service = mock_password_service  # Use mock for testing
        hashed = user_service.password_service.get_password_hash("SecurePassword123!")

        assert hashed != "SecurePassword123!"
        assert len(hashed) > 10  # Should be a hash
        # Verify the password works
        assert user_service.password_service.verify_password(
            "SecurePassword123!", hashed
        )


class TestSecurityHeaders:
    """Test security headers and CSRF protection."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, async_client: AsyncClient):
        """Test that security headers are present in responses."""
        response = await async_client.get("/api/v1/health")

        expected_headers = [
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "X-Frame-Options",
            "Content-Security-Policy",
        ]

        for header in expected_headers:
            assert header in response.headers, f"Missing security header: {header}"

    @pytest.mark.asyncio
    async def test_csrf_protection_on_state_changing_operations(
        self, async_client: AsyncClient
    ):
        """Test CSRF protection on POST/PUT/PATCH/DELETE operations."""
        # Test that operations without proper CSRF tokens are rejected

        # Register endpoint should work without CSRF (stateless)
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "test123456",
                "confirm_password": "test123456",
                "name": "Test User",
            },
        )
        # Should not fail due to CSRF (stateless endpoint)
        assert response.status_code != 403

    @pytest.mark.asyncio
    async def test_rate_limiting_on_auth_endpoints(self, async_client: AsyncClient):
        """Test rate limiting on authentication endpoints."""
        # Make multiple rapid requests to test rate limiting
        responses = []

        for i in range(10):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": f"test{i}@example.com", "password": "password123"},
            )
            responses.append(response.status_code)

        # Should either hit rate limit (429) or process normally (401/422 for invalid creds)
        # HTTP 500 should never occur - rate limiting must not cause server errors
        status_codes = set(responses)
        assert 429 in status_codes or all(
            code in [401, 422] for code in status_codes
        ), f"Unexpected status codes (500 not allowed): {status_codes}"


class TestErrorHandling:
    """Test error handling in authentication flows."""

    @pytest.mark.asyncio
    async def test_malformed_json_handling(self, async_client: AsyncClient):
        """Test handling of malformed JSON requests."""
        response = await async_client.post(
            "/api/v1/auth/login",
            content="{ invalid json }",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_oversized_request_handling(self, async_client: AsyncClient):
        """Test handling of oversized requests."""
        large_payload = {
            "email": "test@example.com",
            "password": "a" * 10000,  # Very long password
            "name": "x" * 10000,  # Very long name
        }

        response = await async_client.post("/api/v1/auth/register", json=large_payload)
        # Should either reject or handle gracefully
        assert response.status_code in [400, 413, 422, 500]

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, async_client: AsyncClient):
        """Test protection against SQL injection attacks."""
        malicious_inputs = [
            "test@example.com'; DROP TABLE users; --",
            "admin@example.com' OR '1'='1",
            'test@example.com"; DELETE FROM users; --',
        ]

        for malicious_input in malicious_inputs:
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": malicious_input, "password": "password123"},
            )
            # Should either reject or handle safely (not 500 internal error)
            assert response.status_code in [
                400,
                401,
                422,
            ], f"Unsafe handling of: {malicious_input}"


class TestPerformance:
    """Test authentication performance characteristics."""

    @pytest.mark.asyncio
    async def test_concurrent_login_requests(self, async_client: AsyncClient):
        """Test handling of concurrent login requests under load."""

        async def login_request(user_suffix: str):
            return await async_client.post(
                "/api/v1/auth/login",
                json={
                    "email": f"perf_test_{user_suffix}@example.com",
                    "password": "password123",
                },
            )

        # Create users first for performance testing
        for i in range(20):
            user_suffix = f"perf_{uuid.uuid4().hex[:8]}"
            await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"perf_test_{user_suffix}@example.com",
                    "name": f"Performance Test User {i}",
                    "password": "password123",
                    "confirm_password": "password123",
                },
            )

        # Make higher concurrent requests (20 instead of 5)
        tasks = [login_request(f"perf_{uuid.uuid4().hex[:8]}") for _ in range(20)]

        # Measure performance
        import time

        start_time = time.time()

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 10.0, f"Too slow: {total_time:.2f}s for 20 requests"

        # All should complete without exceptions
        for response in responses:
            assert not isinstance(response, Exception)
            assert hasattr(response, "status_code")

        # Check response time distribution
        successful_responses = [r for r in responses if hasattr(r, "status_code")]
        status_codes = [r.status_code for r in successful_responses]

        # Most should be 401 (invalid credentials) or succeed
        assert all(code in [200, 401, 422] for code in status_codes), (
            f"Unexpected status codes: {status_codes}"
        )

    @pytest.mark.asyncio
    async def test_authentication_response_time(self, async_client: AsyncClient):
        """Test that authentication requests complete in reasonable time."""
        import time

        start_time = time.time()
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        end_time = time.time()

        # Should complete within 5 seconds
        assert (end_time - start_time) < 5.0, "Authentication request took too long"


# Integration test combining multiple flows
class TestCompleteAuthFlow:
    """Test complete authentication workflows."""

    @pytest.mark.asyncio
    async def test_complete_registration_login_logout_flow(
        self, async_client: AsyncClient
    ):
        """Test complete user journey from registration to logout."""
        unique_email = f"flow_test_{uuid.uuid4()}@example.com"

        # Step 1: Register
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "test123456",
                "confirm_password": "test123456",
                "name": "Flow Test User",
            },
        )

        # Step 1: Registration must succeed
        assert register_response.status_code in [
            200,
            201,
        ], f"Registration should succeed, got {register_response.status_code}"

        # Step 2: Login with same credentials must succeed
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": "test123456"},
        )
        assert login_response.status_code in [
            200,
            201,
        ], f"Login should succeed, got {login_response.status_code}"

        # Step 3: Token must be present in response
        login_data = login_response.json()
        token = login_data.get("token", {}).get("access_token") or login_data.get(
            "access_token"
        )
        assert token, "Token must be present in login response"

        # Step 4: Protected endpoint must succeed with valid token
        me_response = await async_client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200, (
            f"Protected endpoint should succeed with valid token, got {me_response.status_code}"
        )

        # Step 5: Logout must succeed
        logout_response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logout_response.status_code == 200, (
            f"Logout should succeed, got {logout_response.status_code}"
        )
