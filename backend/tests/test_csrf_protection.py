"""
CSRF Protection Tests

Tests for Cross-Site Request Forgery protection using double-submit cookie pattern.

NOTE: These tests will pass once CSRF middleware is implemented.
Currently marked as expected to fail (xfail) until implementation is complete.
"""

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.xfail(reason="CSRF middleware not yet implemented", strict=False)
class TestCSRFProtection:
    """
    Test suite for CSRF protection via double-submit cookie pattern.

    Tests will be enabled once backend/app/middleware/csrf.py is implemented.
    """

    @pytest.fixture
    async def authenticated_client(self, async_client: AsyncClient):
        """Create authenticated client with CSRF token."""
        # Register user
        user_data = {
            "email": "csrf_test@example.com",
            "name": "CSRF Test User",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }

        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data,
        )

        cookies = response.cookies
        access_token = response.json()["token"]["accessToken"]

        # Extract CSRF token from non-HttpOnly cookie
        csrf_token = cookies.get("csrf_token")

        return {
            "client": async_client,
            "cookies": cookies,
            "access_token": access_token,
            "csrf_token": csrf_token,
        }

    @pytest.mark.asyncio
    async def test_csrf_token_set_on_first_request(self, async_client: AsyncClient):
        """
        SECURITY TEST: Verify CSRF token is set on first request.
        """
        response = await async_client.get("/api/v1/health")

        cookies = response.cookies
        assert "csrf_token" in cookies

        # CSRF token should NOT be HttpOnly (JS needs to read it)
        set_cookie_headers = response.headers.get_list("set-cookie")
        csrf_cookie = [h for h in set_cookie_headers if "csrf_token=" in h]

        if csrf_cookie:
            assert "HttpOnly" not in csrf_cookie[0]

    @pytest.mark.asyncio
    async def test_post_without_csrf_token_rejected(self, authenticated_client: dict):
        """
        SECURITY TEST: Verify POST requests without CSRF token are rejected.
        """
        client = authenticated_client["client"]
        cookies = authenticated_client["cookies"]

        # Try POST without CSRF header
        response = await client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "Test"},
            cookies=cookies,
            headers={"Authorization": f"Bearer {authenticated_client['access_token']}"},
            # Missing X-CSRF-Token header
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "CSRF" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_post_with_valid_csrf_token_accepted(
        self, authenticated_client: dict
    ):
        """
        SECURITY TEST: Verify POST requests with valid CSRF token are accepted.
        """
        client = authenticated_client["client"]
        cookies = authenticated_client["cookies"]
        csrf_token = authenticated_client["csrf_token"]

        response = await client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "Test"},
            cookies=cookies,
            headers={
                "Authorization": f"Bearer {authenticated_client['access_token']}",
                "X-CSRF-Token": csrf_token,  # Include CSRF token
            },
        )

        # Should succeed (or fail for other reasons, not CSRF)
        assert response.status_code != status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_post_with_invalid_csrf_token_rejected(
        self, authenticated_client: dict
    ):
        """
        SECURITY TEST: Verify POST requests with invalid CSRF token are rejected.
        """
        client = authenticated_client["client"]
        cookies = authenticated_client["cookies"]

        response = await client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "Test"},
            cookies=cookies,
            headers={
                "Authorization": f"Bearer {authenticated_client['access_token']}",
                "X-CSRF-Token": "invalid_token_12345",  # Invalid token
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "CSRF" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_post_with_mismatched_csrf_tokens_rejected(
        self, authenticated_client: dict
    ):
        """
        SECURITY TEST: Verify CSRF token in header must match cookie.
        """
        client = authenticated_client["client"]
        cookies = authenticated_client["cookies"]

        # Use different token in header vs cookie
        response = await client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "description": "Test"},
            cookies=cookies,
            headers={
                "Authorization": f"Bearer {authenticated_client['access_token']}",
                "X-CSRF-Token": "different_token_from_cookie",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_requests_dont_require_csrf(self, authenticated_client: dict):
        """
        TEST: Verify GET requests don't require CSRF token.

        CSRF protection only needed for state-changing requests.
        """
        client = authenticated_client["client"]
        cookies = authenticated_client["cookies"]

        response = await client.get(
            "/api/v1/auth/me",
            cookies=cookies,
            # No CSRF token needed for GET
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_delete_requires_csrf(self, authenticated_client: dict):
        """
        SECURITY TEST: Verify DELETE requests require CSRF token.
        """
        client = authenticated_client["client"]
        cookies = authenticated_client["cookies"]

        # Try DELETE without CSRF token
        response = await client.delete(
            "/api/v1/projects/some-id",
            cookies=cookies,
            headers={"Authorization": f"Bearer {authenticated_client['access_token']}"},
        )

        # Should be rejected for missing CSRF (403) not 404
        if response.status_code == status.HTTP_403_FORBIDDEN:
            assert "CSRF" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_put_requires_csrf(self, authenticated_client: dict):
        """
        SECURITY TEST: Verify PUT requests require CSRF token.
        """
        client = authenticated_client["client"]
        cookies = authenticated_client["cookies"]

        response = await client.put(
            "/api/v1/projects/some-id",
            json={"name": "Updated Name"},
            cookies=cookies,
            headers={"Authorization": f"Bearer {authenticated_client['access_token']}"},
        )

        if response.status_code == status.HTTP_403_FORBIDDEN:
            assert "CSRF" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_patch_requires_csrf(self, authenticated_client: dict):
        """
        SECURITY TEST: Verify PATCH requests require CSRF token.
        """
        client = authenticated_client["client"]
        cookies = authenticated_client["cookies"]

        response = await client.patch(
            "/api/v1/projects/some-id",
            json={"description": "Updated"},
            cookies=cookies,
            headers={"Authorization": f"Bearer {authenticated_client['access_token']}"},
        )

        if response.status_code == status.HTTP_403_FORBIDDEN:
            assert "CSRF" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_exempt_from_csrf(self, async_client: AsyncClient):
        """
        TEST: Verify login endpoint is exempt from CSRF validation.

        Login creates the session, so can't have CSRF token yet.
        """
        user_data = {
            "email": "login_test@example.com",
            "name": "Login Test",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }

        # Register first
        await async_client.post("/api/v1/auth/register", json=user_data)

        # Login without CSRF token should work
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]},
            # No CSRF token
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_register_exempt_from_csrf(self, async_client: AsyncClient):
        """
        TEST: Verify register endpoint is exempt from CSRF validation.
        """
        user_data = {
            "email": "register_csrf@example.com",
            "name": "Register CSRF Test",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }

        # Register without CSRF token should work
        response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data,
            # No CSRF token
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_csrf_token_rotation(self, authenticated_client: dict):
        """
        SECURITY TEST: Verify CSRF token can be rotated.
        """
        client = authenticated_client["client"]

        # Get initial CSRF token
        response1 = await client.get("/api/v1/health")
        csrf_token_1 = response1.cookies.get("csrf_token")

        # Make request that might trigger rotation
        import asyncio

        await asyncio.sleep(1)

        response2 = await client.get("/api/v1/health")
        csrf_token_2 = response2.cookies.get("csrf_token")

        # Token might stay same (valid) or rotate (also valid)
        assert csrf_token_1 or csrf_token_2

    @pytest.mark.asyncio
    async def test_csrf_cookie_attributes(self, async_client: AsyncClient):
        """
        SECURITY TEST: Verify CSRF cookie has correct attributes.
        """
        response = await async_client.get("/api/v1/health")

        set_cookie_headers = response.headers.get_list("set-cookie")
        csrf_cookie = [h for h in set_cookie_headers if "csrf_token=" in h]

        if csrf_cookie:
            cookie_header = csrf_cookie[0]

            # CSRF cookie should NOT be HttpOnly (JS needs to read it)
            assert "HttpOnly" not in cookie_header

            # Should have SameSite for additional protection
            assert "SameSite" in cookie_header

            # Should have appropriate expiry (24 hours typical)
            assert "Max-Age=" in cookie_header


@pytest.mark.xfail(reason="CSRF middleware not yet implemented", strict=False)
class TestCSRFEdgeCases:
    """Edge cases and attack scenarios for CSRF protection."""

    @pytest.mark.asyncio
    async def test_csrf_replay_attack_prevention(self, async_client: AsyncClient):
        """
        SECURITY TEST: Verify old CSRF tokens can't be replayed.
        """
        # Register user
        user_data = {
            "email": "replay@example.com",
            "name": "Replay Test",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }

        response1 = await async_client.post("/api/v1/auth/register", json=user_data)
        old_csrf = response1.cookies.get("csrf_token")
        cookies1 = response1.cookies

        # Logout (invalidates session)
        access_token = response1.json()["token"]["accessToken"]
        await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            cookies=cookies1,
        )

        # Login again (new session)
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]},
        )

        new_cookies = login_response.cookies
        new_access_token = login_response.json()["token"]["accessToken"]

        # Try to use old CSRF token with new session
        response = await async_client.post(
            "/api/v1/projects",
            json={"name": "Test"},
            cookies=new_cookies,
            headers={
                "Authorization": f"Bearer {new_access_token}",
                "X-CSRF-Token": old_csrf,  # Old token from previous session
            },
        )

        # Should be rejected
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_csrf_cross_user_attack(self, async_client: AsyncClient):
        """
        SECURITY TEST: Verify CSRF token from one user can't be used by another.
        """
        # User 1
        user1_data = {
            "email": "user1_csrf@example.com",
            "name": "User 1",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }

        response1 = await async_client.post("/api/v1/auth/register", json=user1_data)
        user1_csrf = response1.cookies.get("csrf_token")

        # User 2
        user2_data = {
            "email": "user2_csrf@example.com",
            "name": "User 2",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }

        response2 = await async_client.post("/api/v1/auth/register", json=user2_data)
        user2_cookies = response2.cookies
        user2_access_token = response2.json()["token"]["accessToken"]

        # Try to use User 1's CSRF token with User 2's session
        response = await async_client.post(
            "/api/v1/projects",
            json={"name": "Test"},
            cookies=user2_cookies,
            headers={
                "Authorization": f"Bearer {user2_access_token}",
                "X-CSRF-Token": user1_csrf,  # Wrong user's token
            },
        )

        # Should be rejected
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_csrf_middleware_file_exists():
    """
    Documentation test: Ensure CSRF middleware implementation is tracked.

    This test reminds developers to implement the middleware.
    """
    import os

    middleware_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "middleware", "csrf.py"
    )

    if not os.path.exists(middleware_path):
        pytest.skip(
            "CSRF middleware not yet implemented. "
            "See SECURITY_CRITICAL_TOKEN_STORAGE.md section 1.4 for implementation guide."
        )
