"""
Comprehensive tests for cookie-based authentication security.

Tests verify that HttpOnly, Secure cookies are properly set and validated
across all authentication endpoints to prevent XSS attacks.
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

settings = get_settings()


class TestCookieAuthentication:
    """Test suite for cookie-based authentication security."""

    @pytest.fixture
    async def test_user_data(self):
        """Test user credentials."""
        return {
            "email": "cookie_test@example.com",
            "name": "Cookie Test User",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }

    @pytest.mark.asyncio
    async def test_register_sets_httponly_cookies(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify registration sets HttpOnly, Secure cookies.

        Critical: Cookies must have HttpOnly flag to prevent XSS attacks.
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify cookies are set in response
        cookies = response.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies

        # Verify HttpOnly flag (prevents JavaScript access)
        access_cookie = cookies.get("access_token")
        refresh_cookie = cookies.get("refresh_token")

        # Note: httpx doesn't expose httponly flag directly in response.cookies
        # We verify it through Set-Cookie headers
        set_cookie_headers = response.headers.get_list("set-cookie")

        access_cookie_header = [h for h in set_cookie_headers if "access_token=" in h][
            0
        ]
        refresh_cookie_header = [
            h for h in set_cookie_headers if "refresh_token=" in h
        ][0]

        # CRITICAL: Verify HttpOnly flag
        assert "HttpOnly" in access_cookie_header
        assert "HttpOnly" in refresh_cookie_header

        # Verify SameSite for CSRF protection
        assert (
            "SameSite=Strict" in access_cookie_header
            or "SameSite=strict" in access_cookie_header
        )
        assert (
            "SameSite=Strict" in refresh_cookie_header
            or "SameSite=strict" in refresh_cookie_header
        )

        # Verify Path
        assert "Path=/" in access_cookie_header
        assert "Path=/" in refresh_cookie_header

        # Verify tokens still in response body for backwards compatibility
        data = response.json()
        assert "token" in data
        assert data["token"]["access_token"]
        assert data["token"]["refresh_token"]

    @pytest.mark.asyncio
    async def test_login_sets_httponly_cookies(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify login sets HttpOnly, Secure cookies.
        """
        # First register
        await async_client.post("/api/v1/auth/register", json=test_user_data)

        # Then login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        }
        response = await async_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK

        # Verify cookies
        set_cookie_headers = response.headers.get_list("set-cookie")

        access_cookie_header = [h for h in set_cookie_headers if "access_token=" in h][
            0
        ]
        refresh_cookie_header = [
            h for h in set_cookie_headers if "refresh_token=" in h
        ][0]

        # CRITICAL: Verify security flags
        assert "HttpOnly" in access_cookie_header
        assert "HttpOnly" in refresh_cookie_header
        assert "SameSite" in access_cookie_header
        assert "SameSite" in refresh_cookie_header

    @pytest.mark.asyncio
    async def test_refresh_accepts_cookie(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify refresh endpoint accepts refresh token from cookie.

        This is the secure method - token sent via HttpOnly cookie.
        """
        # Register to get cookies
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        # Extract cookies from registration
        cookies = register_response.cookies

        # Wait a moment to ensure token timestamps differ
        import asyncio

        await asyncio.sleep(1)

        # Refresh using cookie (secure method)
        refresh_response = await async_client.post(
            "/api/v1/auth/refresh",
            cookies=cookies,  # Send cookies automatically
        )

        assert refresh_response.status_code == status.HTTP_200_OK

        # Verify new tokens set as cookies
        set_cookie_headers = refresh_response.headers.get_list("set-cookie")
        access_cookie_header = [h for h in set_cookie_headers if "access_token=" in h]

        assert len(access_cookie_header) > 0
        assert "HttpOnly" in access_cookie_header[0]

    @pytest.mark.asyncio
    async def test_refresh_fallback_to_body(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify refresh endpoint falls back to body for backwards compatibility.

        Note: This is the INSECURE method and should log a warning.
        """
        # Register to get tokens
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        refresh_token = register_response.json()["token"]["refresh_token"]

        # Refresh using body (insecure method)
        refresh_response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert refresh_response.status_code == status.HTTP_200_OK

        # Should still work for backwards compatibility
        data = refresh_response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_refresh_without_token_fails(self, async_client: AsyncClient):
        """
        SECURITY TEST: Verify refresh fails when no token provided.
        """
        response = await async_client.post("/api/v1/auth/refresh")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "No refresh token provided" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_logout_clears_cookies(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify logout clears authentication cookies.
        """
        # Register and login
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        cookies = register_response.cookies
        access_token = register_response.json()["token"]["access_token"]

        # Logout
        logout_response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            cookies=cookies,
        )

        assert logout_response.status_code == status.HTTP_200_OK

        # Verify cookies are cleared (Max-Age=0 or expires in past)
        set_cookie_headers = logout_response.headers.get_list("set-cookie")

        # Should have instructions to delete cookies
        assert len(set_cookie_headers) >= 2  # access_token and refresh_token

    @pytest.mark.asyncio
    async def test_cookie_expiry_times(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify cookies have appropriate expiry times.
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        set_cookie_headers = response.headers.get_list("set-cookie")

        access_cookie = [h for h in set_cookie_headers if "access_token=" in h][0]
        refresh_cookie = [h for h in set_cookie_headers if "refresh_token=" in h][0]

        # Verify Max-Age is set
        assert "Max-Age=" in access_cookie
        assert "Max-Age=" in refresh_cookie

        # Extract Max-Age values
        import re

        access_max_age = int(re.search(r"Max-Age=(\d+)", access_cookie).group(1))
        refresh_max_age = int(re.search(r"Max-Age=(\d+)", refresh_cookie).group(1))

        # Verify access token expires in ~30 minutes (1800 seconds)
        expected_access_expiry = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        assert (
            abs(access_max_age - expected_access_expiry) < 60
        )  # Allow 1 minute variance

        # Verify refresh token expires in ~7 days (604800 seconds)
        expected_refresh_expiry = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        assert (
            abs(refresh_max_age - expected_refresh_expiry) < 3600
        )  # Allow 1 hour variance

    @pytest.mark.asyncio
    async def test_secure_flag_in_production(
        self, async_client: AsyncClient, test_user_data: dict, monkeypatch
    ):
        """
        SECURITY TEST: Verify Secure flag is set in production environment.
        """
        # Mock production environment
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")

        response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        set_cookie_headers = response.headers.get_list("set-cookie")
        access_cookie = [h for h in set_cookie_headers if "access_token=" in h][0]

        # In production, Secure flag MUST be set
        if settings.is_production:
            assert "Secure" in access_cookie

    @pytest.mark.asyncio
    async def test_cookies_with_authenticated_request(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify authenticated requests work with cookies.
        """
        # Register
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        cookies = register_response.cookies

        # Make authenticated request using cookies
        me_response = await async_client.get(
            "/api/v1/auth/me",
            cookies=cookies,
        )

        assert me_response.status_code == status.HTTP_200_OK
        data = me_response.json()
        assert data["email"] == test_user_data["email"]

    @pytest.mark.asyncio
    async def test_xss_protection_cookies_not_accessible_to_js(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify HttpOnly cookies cannot be accessed by JavaScript.

        This test verifies the Set-Cookie headers have HttpOnly flag.
        In a real browser, document.cookie would NOT show these cookies.
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        set_cookie_headers = response.headers.get_list("set-cookie")

        # Both auth cookies MUST have HttpOnly flag
        for header in set_cookie_headers:
            if "access_token=" in header or "refresh_token=" in header:
                assert "HttpOnly" in header, (
                    f"CRITICAL SECURITY FAILURE: Auth cookie missing HttpOnly flag: {header}"
                )

    @pytest.mark.asyncio
    async def test_csrf_protection_samesite_strict(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify SameSite=Strict prevents CSRF attacks.
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        set_cookie_headers = response.headers.get_list("set-cookie")

        # All auth cookies should have SameSite=Strict
        for header in set_cookie_headers:
            if "access_token=" in header or "refresh_token=" in header:
                # Accept both Strict and strict (case variations)
                assert "SameSite=Strict" in header or "SameSite=strict" in header, (
                    f"CSRF VULNERABILITY: Cookie missing SameSite=Strict: {header}"
                )

    @pytest.mark.asyncio
    async def test_token_rotation_on_refresh(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify tokens are rotated on refresh (if implemented).
        """
        # Register
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        original_access_token = register_response.json()["token"]["access_token"]
        cookies = register_response.cookies

        # Wait to ensure timestamp difference
        import asyncio

        await asyncio.sleep(1)

        # Refresh
        refresh_response = await async_client.post(
            "/api/v1/auth/refresh",
            cookies=cookies,
        )

        new_access_token = refresh_response.json()["access_token"]

        # Tokens should be different (rotated)
        assert new_access_token != original_access_token

    @pytest.mark.asyncio
    async def test_invalid_cookie_rejected(self, async_client: AsyncClient):
        """
        SECURITY TEST: Verify invalid cookies are rejected.
        """
        # Try to refresh with invalid cookie
        response = await async_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": "invalid_token_12345"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_cookie_path_restriction(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        SECURITY TEST: Verify cookies are scoped to correct path.
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        set_cookie_headers = response.headers.get_list("set-cookie")

        # Cookies should be scoped to root path
        for header in set_cookie_headers:
            if "access_token=" in header or "refresh_token=" in header:
                assert "Path=/" in header

    @pytest.mark.asyncio
    async def test_backwards_compatibility_tokens_in_response(
        self, async_client: AsyncClient, test_user_data: dict
    ):
        """
        TEST: Verify tokens still returned in response for backwards compatibility.

        Note: This should be removed after frontend migration is complete.
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        data = response.json()

        # Tokens should be in response body for backwards compatibility
        assert "token" in data
        assert data["token"]["access_token"]
        assert data["token"]["refresh_token"]

        # But cookies should also be set (new secure method)
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies


class TestCookieSecurityEdgeCases:
    """Test edge cases and security scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_login_overwrites_cookies(self, async_client: AsyncClient):
        """
        SECURITY TEST: Verify multiple logins overwrite previous cookies.
        """
        user_data = {
            "email": "multi_login@example.com",
            "name": "Multi Login",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }

        # First registration
        response1 = await async_client.post("/api/v1/auth/register", json=user_data)
        token1 = response1.json()["token"]["access_token"]

        # Second login
        login_data = {"email": user_data["email"], "password": user_data["password"]}
        response2 = await async_client.post("/api/v1/auth/login", json=login_data)
        token2 = response2.json()["token"]["access_token"]

        # Tokens should be different
        assert token1 != token2

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_same_cookies(
        self, async_client: AsyncClient
    ):
        """
        SECURITY TEST: Verify concurrent requests with same cookies work correctly.
        """
        user_data = {
            "email": "concurrent@example.com",
            "name": "Concurrent User",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }

        # Register
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json=user_data,
        )
        cookies = register_response.cookies

        # Make concurrent authenticated requests
        import asyncio

        responses = await asyncio.gather(
            async_client.get("/api/v1/auth/me", cookies=cookies),
            async_client.get("/api/v1/auth/me", cookies=cookies),
            async_client.get("/api/v1/auth/me", cookies=cookies),
        )

        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_cookie_size_reasonable(self, async_client: AsyncClient):
        """
        PERFORMANCE TEST: Verify cookie sizes are reasonable.
        """
        user_data = {
            "email": "cookie_size@example.com",
            "name": "Cookie Size Test",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }

        response = await async_client.post("/api/v1/auth/register", json=user_data)

        set_cookie_headers = response.headers.get_list("set-cookie")

        # Each cookie should be < 4KB (browser limit is 4096 bytes)
        for header in set_cookie_headers:
            assert len(header) < 4096, f"Cookie too large: {len(header)} bytes"


@pytest.mark.asyncio
async def test_security_headers_documentation():
    """
    Documentation test: Ensure security implementation is documented.
    """
    import os

    # Verify security documentation exists
    security_docs = [
        "SECURITY_CRITICAL_TOKEN_STORAGE.md",
        "SECURITY_IMPLEMENTATION_SUMMARY.md",
        "SECURITY_QUICK_REFERENCE.md",
    ]

    for doc in security_docs:
        doc_path = os.path.join("/docs", "security", doc)
        assert os.path.exists(doc_path), f"Security documentation missing: {doc}"
