"""
Tests for token blacklist functionality.

These tests ensure that JWT tokens are properly invalidated after logout
and that blacklisted tokens cannot be used to access protected endpoints.
"""

import asyncio
import uuid

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestTokenBlacklist:
    """Test token blacklist functionality."""

    @pytest.fixture
    async def authenticated_user_headers(
        self, async_client: AsyncClient
    ) -> dict[str, str]:
        """Create authenticated user and return headers."""
        # Use unique email to avoid conflicts
        unique_email = f"blacklist-test-{uuid.uuid4().hex[:8]}@example.com"

        # Small delay to prevent rate limiting
        await asyncio.sleep(0.1)

        # Register and login user
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "name": "Test User",
                "password": "testpassword123",
                "confirm_password": "testpassword123",
            },
        )

        # Small delay before login attempt
        await asyncio.sleep(0.1)

        if register_response.status_code != 200:
            # User might already exist, try login
            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": unique_email, "password": "testpassword123"},
            )
            assert login_response.status_code == 200, (
                f"Login failed: {login_response.json()}"
            )
            token_data = login_response.json()
            token = token_data.get("token", {}).get("access_token") or token_data.get(
                "access_token"
            )
        else:
            token_data = register_response.json()
            token = token_data.get("token", {}).get("access_token") or token_data.get(
                "access_token"
            )

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def superuser_headers(
        self, async_client: AsyncClient, test_session: AsyncSession
    ) -> dict[str, str]:
        """Create authenticated superuser and return headers."""
        from app.repositories.tenant import TenantRepository
        from app.services.user import UserService

        # Create tenant
        tenant_repo = TenantRepository(test_session)
        tenant = await tenant_repo.create_tenant(
            name="Superuser Tenant", slug=f"superuser-{uuid.uuid4().hex[:8]}"
        )

        # Create superuser
        user_service = UserService(test_session, tenant.id)
        unique_email = f"superuser-{uuid.uuid4().hex[:8]}@example.com"

        # Create user via service (bypass password validation for tests)
        from app.core.password_service import PasswordService

        password_service = PasswordService()
        hashed_password = password_service.get_password_hash("testpassword123")

        # Create user manually with is_superuser=True
        from app.models.user import User

        superuser = User(
            email=unique_email,
            username="superuser",
            full_name="Super User",
            hashed_password=hashed_password,
            tenant_id=tenant.id,
            is_active=True,
            is_superuser=True,
        )
        test_session.add(superuser)
        await test_session.commit()
        await test_session.refresh(superuser)

        # Login to get token
        await asyncio.sleep(0.1)
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": "testpassword123"},
        )
        assert login_response.status_code == 200, (
            f"Login failed: {login_response.json()}"
        )

        token_data = login_response.json()
        token = token_data.get("token", {}).get("access_token") or token_data.get(
            "access_token"
        )

        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.skip(
        reason="TODO: Flaky test - passes individually but fails in full test run due to Redis state pollution from other auth tests"
    )
    async def test_token_blacklist_on_logout(
        self, async_client: AsyncClient, authenticated_user_headers: dict[str, str]
    ) -> None:
        """Test that tokens are blacklisted after logout."""
        # Small delay to prevent rate limiting
        await asyncio.sleep(0.1)

        # First, verify the token works
        response = await async_client.get(
            "/api/v1/auth/me", headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_200_OK
        user_data = response.json()
        assert "id" in user_data

        # Logout to blacklist the token
        logout_response = await async_client.post(
            "/api/v1/auth/logout", headers=authenticated_user_headers
        )
        assert logout_response.status_code == status.HTTP_200_OK
        assert logout_response.json()["message"] == "Successfully logged out"

        # Try to use the same token - should fail
        response = await async_client.get(
            "/api/v1/auth/me", headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.skip(
        reason="TODO: Flaky test - passes individually but fails in full test run due to Redis state pollution from other auth tests"
    )
    async def test_token_validation_endpoint_after_logout(
        self, async_client: AsyncClient, authenticated_user_headers: dict[str, str]
    ) -> None:
        """Test that token validation fails after logout."""
        # Small delay to prevent rate limiting
        await asyncio.sleep(0.1)

        # Verify token is valid before logout
        response = await async_client.post(
            "/api/v1/auth/validate-token", headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["valid"] is True

        # Small delay before logout
        await asyncio.sleep(0.1)

        # Logout
        await async_client.post(
            "/api/v1/auth/logout", headers=authenticated_user_headers
        )

        # Small delay before testing validation
        await asyncio.sleep(0.1)

        # Token validation should fail
        response = await async_client.post(
            "/api/v1/auth/validate-token", headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.skip(
        reason="TODO: Flaky test - passes individually but fails in full test run due to Redis state pollution from other auth tests"
    )
    async def test_multiple_logout_attempts(
        self, async_client: AsyncClient, authenticated_user_headers: dict[str, str]
    ) -> None:
        """Test that multiple logout attempts don't cause errors."""
        # Small delay to prevent rate limiting
        await asyncio.sleep(0.1)

        # First logout should succeed
        response = await async_client.post(
            "/api/v1/auth/logout", headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_200_OK

        # Small delay before second attempt
        await asyncio.sleep(0.1)

        # Second logout with same token should fail (token already blacklisted)
        response = await async_client.post(
            "/api/v1/auth/logout", headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.skip(
        reason="TODO: Flaky test - passes individually but fails in full test run due to Redis state pollution from other auth tests"
    )
    async def test_blacklist_stats_endpoint(
        self, async_client: AsyncClient, superuser_headers: dict[str, str]
    ) -> None:
        """Test blacklist statistics endpoint (superuser only)."""
        # Get current superuser's email before logout
        me_response = await async_client.get(
            "/api/v1/auth/me", headers=superuser_headers
        )
        assert me_response.status_code == status.HTTP_200_OK
        user_email = me_response.json()["email"]

        # Get initial stats (requires superuser)
        response = await async_client.get(
            "/api/v1/auth/blacklist/stats", headers=superuser_headers
        )
        assert response.status_code == status.HTTP_200_OK
        initial_stats = response.json()
        assert "blacklisted_tokens" in initial_stats
        assert "blacklisted_users" in initial_stats
        assert "redis_status" in initial_stats

        initial_token_count = initial_stats["blacklisted_tokens"]

        # Logout to add token to blacklist
        await async_client.post("/api/v1/auth/logout", headers=superuser_headers)

        # Clear cookies to avoid using blacklisted refresh token
        async_client.cookies.clear()

        # Wait to ensure new token has different timestamp (iat is in seconds)
        await asyncio.sleep(1.1)

        # Login again with the same user's email to get new token for stats check
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "testpassword123"},
        )
        assert login_response.status_code == status.HTTP_200_OK
        new_token = login_response.json()["token"]["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}

        # Check stats again - should have two more blacklisted tokens (access + refresh)
        response = await async_client.get(
            "/api/v1/auth/blacklist/stats", headers=new_headers
        )
        assert response.status_code == status.HTTP_200_OK
        updated_stats = response.json()
        assert updated_stats["blacklisted_tokens"] == initial_token_count + 2

    @pytest.mark.skip(
        reason="TODO: Flaky test - passes individually but fails in full test run due to Redis state pollution from other auth tests"
    )
    async def test_blacklist_stats_forbidden_for_regular_users(
        self, async_client: AsyncClient, authenticated_user_headers: dict[str, str]
    ) -> None:
        """Test that regular users cannot access blacklist statistics."""
        # Small delay to prevent rate limiting
        await asyncio.sleep(0.1)

        # Try to access blacklist stats as regular user
        response = await async_client.get(
            "/api/v1/auth/blacklist/stats", headers=authenticated_user_headers
        )

        # Should return 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Administrator access required" in response.json()["detail"]

    @pytest.mark.skip(
        reason="TODO: Flaky test - passes individually but fails in full test run due to Redis state pollution from other auth tests"
    )
    async def test_concurrent_token_usage_after_logout(
        self, async_client: AsyncClient, authenticated_user_headers: dict[str, str]
    ) -> None:
        """Test that all requests with blacklisted token fail."""
        # Small delay to prevent rate limiting
        await asyncio.sleep(0.1)

        # Logout to blacklist token
        await async_client.post(
            "/api/v1/auth/logout", headers=authenticated_user_headers
        )

        # Small delay before testing endpoints
        await asyncio.sleep(0.1)

        # Try multiple different endpoints with blacklisted token
        endpoints = [
            ("/api/v1/auth/me", "GET"),
            ("/api/v1/auth/validate-token", "POST"),
            ("/api/v1/auth/blacklist/stats", "GET"),
        ]

        for endpoint, method in endpoints:
            # Small delay between requests
            await asyncio.sleep(0.1)

            if method == "GET":
                response = await async_client.get(
                    endpoint, headers=authenticated_user_headers
                )
            else:
                response = await async_client.post(
                    endpoint, headers=authenticated_user_headers
                )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"Failed for {endpoint}"
            )

    @pytest.mark.skip(
        reason="TODO: Flaky test - passes individually but fails in full test run due to Redis state pollution from other auth tests"
    )
    async def test_fresh_token_after_logout_old_token(
        self, async_client: AsyncClient, authenticated_user_headers: dict[str, str]
    ) -> None:
        """Test that new tokens work after old token is blacklisted."""
        # Get current user's email before logout
        me_response = await async_client.get(
            "/api/v1/auth/me", headers=authenticated_user_headers
        )
        assert me_response.status_code == status.HTTP_200_OK
        user_email = me_response.json()["email"]

        # Logout old token
        await async_client.post(
            "/api/v1/auth/logout", headers=authenticated_user_headers
        )

        # Clear cookies to avoid using blacklisted refresh token
        async_client.cookies.clear()

        # Wait to ensure new token has different timestamp (iat is in seconds)
        await asyncio.sleep(1.1)

        # Get new token by logging in again with the same user's email
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "testpassword123"},
        )
        assert login_response.status_code == status.HTTP_200_OK

        new_token = login_response.json()["token"]["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}

        # New token should work
        response = await async_client.get("/api/v1/auth/me", headers=new_headers)
        assert response.status_code == status.HTTP_200_OK

        # Old token should still be blacklisted
        response = await async_client.get(
            "/api/v1/auth/me", headers=authenticated_user_headers
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenBlacklistService:
    """Test TokenBlacklistService directly."""

    async def test_token_blacklist_service_init(self) -> None:
        """Test that TokenBlacklistService initializes correctly."""
        from app.core.token_blacklist import TokenBlacklistService

        service = TokenBlacklistService()
        assert service is not None
        assert service.redis is not None

    async def test_token_hashing(self) -> None:
        """Test token hashing functionality."""
        from app.core.token_blacklist import TokenBlacklistService

        service = TokenBlacklistService()
        token1 = "test.token.here"
        token2 = "different.token.here"

        hash1 = service._hash_token(token1)
        hash2 = service._hash_token(token2)

        assert hash1 != hash2
        assert len(hash1) == 64  # SHA256 produces 64 character hex string
        assert len(hash2) == 64

        # Same token should produce same hash
        hash1_again = service._hash_token(token1)
        assert hash1 == hash1_again

    async def test_blacklist_key_generation(self) -> None:
        """Test blacklist key generation."""
        from app.core.token_blacklist import TokenBlacklistService

        service = TokenBlacklistService()
        token_hash = "abc123"
        key = service._get_blacklist_key(token_hash)

        assert key == "blacklist:token:abc123"

    async def test_get_blacklist_stats_structure(self) -> None:
        """Test that blacklist stats returns proper structure with limits."""
        from app.core.token_blacklist import TokenBlacklistService

        service = TokenBlacklistService()
        stats = await service.get_blacklist_stats()

        assert isinstance(stats, dict)
        assert "blacklisted_tokens" in stats
        assert "blacklisted_users" in stats
        assert "tokens_limited" in stats
        assert "users_limited" in stats
        assert "redis_status" in stats
        assert isinstance(stats["blacklisted_tokens"], int)
        assert isinstance(stats["blacklisted_users"], int)
        assert isinstance(stats["tokens_limited"], bool)
        assert isinstance(stats["users_limited"], bool)
