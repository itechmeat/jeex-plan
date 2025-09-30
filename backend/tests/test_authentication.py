"""
Comprehensive tests for authentication system.
"""
# cSpell:ignore authuser wrongpass correctpassword refreshuser changepass oldpassword wrongcurrent wrongpassword Aemail

import uuid
from datetime import UTC, datetime, timedelta

UTC = UTC
from unittest.mock import patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthService
from app.core.exceptions import AuthenticationError
from app.core.oauth import GitHubOAuthProvider, GoogleOAuthProvider
from app.models.tenant import Tenant
from app.models.user import User
from app.services.user import UserService


class TestAuthService:
    """Test suite for AuthService."""

    @pytest.fixture
    async def auth_service(self, async_db: AsyncSession):
        """Create AuthService instance for testing."""
        return AuthService(async_db)

    @pytest.fixture
    async def test_user(self, async_db: AsyncSession):
        """Create test user."""
        unique_suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            name=f"Test Tenant {unique_suffix}",
            slug=f"test-tenant-{unique_suffix}",
            description="Test tenant for auth tests",
            is_active=True,
        )
        async_db.add(tenant)
        await async_db.commit()
        await async_db.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email=f"test-{unique_suffix}@example.com",
            username=f"testuser-{unique_suffix}",
            full_name="Test User",
            hashed_password="$2b$12$dummy_hash_for_testing",
            is_active=True,
            oauth_provider=None,
            oauth_id=None,
        )
        async_db.add(user)
        await async_db.commit()
        await async_db.refresh(user)

        return user

    def test_password_hashing(self, auth_service) -> None:
        """Test password hashing and verification."""
        password = "test_password123"

        # Hash password using password service
        hashed = auth_service.password_service.get_password_hash(password)

        # Verify hash is different from original password
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long

        # Verify password verification works
        assert auth_service.password_service.verify_password(password, hashed) is True
        assert (
            auth_service.password_service.verify_password("wrong_password", hashed)
            is False
        )

    def test_create_access_token(self, auth_service) -> None:
        """Test JWT access token creation."""
        data = {
            "sub": str(uuid.uuid4()),
            "email": "test@example.com",
            "tenant_id": str(uuid.uuid4()),
        }

        token = auth_service.token_service.create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long

        # Verify token can be decoded
        payload = auth_service.token_service.verify_token(token)
        assert payload is not None
        assert payload["sub"] == data["sub"]
        assert payload["email"] == data["email"]
        assert payload["type"] == "access"

    def test_create_refresh_token(self, auth_service) -> None:
        """Test JWT refresh token creation."""
        data = {"sub": str(uuid.uuid4()), "email": "test@example.com"}

        token = auth_service.token_service.create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 100

        # Verify token can be decoded
        payload = auth_service.token_service.verify_token(token, "refresh")
        assert payload is not None
        assert payload["sub"] == data["sub"]
        assert payload["type"] == "refresh"

    def test_verify_invalid_token(self, auth_service) -> None:
        """Test verification of invalid tokens."""
        # Test completely invalid token
        assert auth_service.token_service.verify_token("invalid_token") is None

        # Test wrong token type
        refresh_token = auth_service.token_service.create_refresh_token({"sub": "test"})
        assert auth_service.token_service.verify_token(refresh_token, "access") is None

    def test_create_tokens_with_custom_expiry(self, auth_service) -> None:
        """Test token creation with custom expiry time."""
        data = {"sub": "test"}
        expires_delta = timedelta(minutes=5)

        token = auth_service.token_service.create_access_token(data, expires_delta)
        payload = auth_service.token_service.verify_token(token)

        # Check that expiry is approximately 5 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"], UTC)
        expected_time = datetime.now(UTC) + expires_delta
        time_diff = abs((exp_time - expected_time).total_seconds())

        assert time_diff < 5  # Allow 5 seconds tolerance


class TestOAuthProviders:
    """Test suite for OAuth providers."""

    def test_google_oauth_provider_initialization(self) -> None:
        """Test Google OAuth provider initialization."""
        with patch("app.core.oauth.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test_client_id"
            mock_settings.GOOGLE_CLIENT_SECRET = "test_client_secret"

            provider = GoogleOAuthProvider()

            assert provider.client_id == "test_client_id"
            assert provider.client_secret == "test_client_secret"

    def test_google_oauth_provider_missing_credentials(self) -> None:
        """Test Google OAuth provider with missing credentials."""
        with patch("app.core.oauth.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = None
            mock_settings.GOOGLE_CLIENT_SECRET = None

            with pytest.raises(ValueError):
                GoogleOAuthProvider()

    def test_github_oauth_provider_initialization(self) -> None:
        """Test GitHub OAuth provider initialization."""
        with patch("app.core.oauth.settings") as mock_settings:
            mock_settings.GITHUB_CLIENT_ID = "test_client_id"
            mock_settings.GITHUB_CLIENT_SECRET = "test_client_secret"

            provider = GitHubOAuthProvider()

            assert provider.client_id == "test_client_id"
            assert provider.client_secret == "test_client_secret"

    @pytest.mark.asyncio
    async def test_google_authorization_url_generation(self) -> None:
        """Test Google authorization URL generation."""
        with patch("app.core.oauth.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = "test_client_id"
            mock_settings.GOOGLE_CLIENT_SECRET = "test_client_secret"
            mock_settings.OAUTH_REDIRECT_URL = "http://localhost:5210/auth/callback"

            provider = GoogleOAuthProvider()
            state = "test_state"

            auth_url = await provider.get_authorization_url(state)

            assert "accounts.google.com" in auth_url
            assert "client_id=test_client_id" in auth_url
            assert "state=test_state" in auth_url
            assert "scope=openid+email+profile" in auth_url

    @pytest.mark.asyncio
    async def test_github_authorization_url_generation(self) -> None:
        """Test GitHub authorization URL generation."""
        with patch("app.core.oauth.settings") as mock_settings:
            mock_settings.GITHUB_CLIENT_ID = "test_client_id"
            mock_settings.GITHUB_CLIENT_SECRET = "test_client_secret"
            mock_settings.OAUTH_REDIRECT_URL = "http://localhost:5210/auth/callback"

            provider = GitHubOAuthProvider()
            state = "test_state"

            auth_url = await provider.get_authorization_url(state)

            assert "github.com" in auth_url
            assert "client_id=test_client_id" in auth_url
            assert "state=test_state" in auth_url
            assert "scope=user%3Aemail" in auth_url


class TestUserService:
    """Test suite for UserService."""

    @pytest.fixture
    async def user_service(
        self, async_db: AsyncSession, test_tenant, mock_password_service
    ):
        """Create UserService instance for testing."""
        service = UserService(async_db, tenant_id=test_tenant.id)
        # Use bypassed password service for testing
        service.password_service = mock_password_service
        return service

    @pytest.fixture
    async def test_tenant(self, async_db: AsyncSession):
        """Create test tenant."""
        unique_suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            name=f"Test Tenant {unique_suffix}",
            slug=f"test-tenant-{unique_suffix}",
            description="Test tenant",
            is_active=True,
        )
        async_db.add(tenant)
        await async_db.commit()
        await async_db.refresh(tenant)
        return tenant

    @pytest.mark.asyncio
    async def test_user_registration_success(self, user_service, async_db) -> None:
        """Test successful user registration."""
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"newuser-{unique_suffix}@example.com"
        username = f"newuser-{unique_suffix}"
        password = "StrongTestPass123!"
        full_name = "New User"

        result = await user_service.register_user(
            email=email, username=username, password=password, full_name=full_name
        )

        assert "user" in result
        assert "tokens" in result

        user = result["user"]
        assert user["email"] == email
        assert user["username"] == username
        assert user["full_name"] == full_name
        assert user["is_active"] is True
        assert "password" not in user
        assert "hashed_password" not in user

        tokens = result["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_user_registration_duplicate_email(
        self, user_service, test_tenant, async_db
    ) -> None:
        """Test user registration with duplicate email."""
        unique_suffix = uuid.uuid4().hex[:8]
        duplicate_email = f"duplicate-{unique_suffix}@example.com"

        # Create first user
        user1 = User(
            tenant_id=test_tenant.id,
            email=duplicate_email,
            username=f"user1-{unique_suffix}",
            full_name="User 1",
            hashed_password="hash1",
            is_active=True,
            is_deleted=False,
        )
        async_db.add(user1)
        await async_db.commit()

        # Try to register second user with same email
        with pytest.raises(HTTPException) as exc_info:
            await user_service.register_user(
                email=duplicate_email,
                username=f"user2-{unique_suffix}",
                password="password123",
                full_name="User 2",
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_user_authentication_success(self, user_service, async_db) -> None:
        """Test successful user authentication."""
        # First register a user
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"auth-{unique_suffix}@example.com"
        password = "StrongTestPass123!"

        await user_service.register_user(
            email=email,
            username=f"authuser-{unique_suffix}",
            password=password,
            full_name="Auth User",
        )

        # Then authenticate
        result = await user_service.authenticate_user(email, password)

        assert "user" in result
        assert "tokens" in result

        user = result["user"]
        assert user["email"] == email
        assert user["is_active"] is True

    @pytest.mark.asyncio
    async def test_user_authentication_wrong_password(
        self, user_service, async_db
    ) -> None:
        """Test user authentication with wrong password."""
        # Register a user
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"wrongpass-{unique_suffix}@example.com"
        await user_service.register_user(
            email=email,
            username=f"wrongpass-{unique_suffix}",
            password="correctpassword",
            full_name="Wrong Pass User",
        )

        # Try to authenticate with wrong password
        with pytest.raises(AuthenticationError) as exc_info:
            await user_service.authenticate_user(email, "wrongpassword")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_user_authentication_nonexistent_user(self, user_service) -> None:
        """Test authentication with nonexistent user."""
        unique_suffix = uuid.uuid4().hex[:8]
        with pytest.raises(AuthenticationError) as exc_info:
            await user_service.authenticate_user(
                f"nonexistent-{unique_suffix}@example.com", "password"
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, user_service, async_db) -> None:
        """Test successful token refresh."""
        # Register and get tokens
        unique_suffix = uuid.uuid4().hex[:8]
        result = await user_service.register_user(
            email=f"refresh-{unique_suffix}@example.com",
            username=f"refreshuser-{unique_suffix}",
            password="password123",
            full_name="Refresh User",
        )

        refresh_token = result["tokens"]["refresh_token"]

        # Refresh tokens
        new_tokens = await user_service.refresh_tokens(refresh_token)

        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, user_service) -> None:
        """Test token refresh with invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            await user_service.refresh_tokens("invalid_refresh_token")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service, async_db) -> None:
        """Test successful password change."""
        # Register user
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"changepass-{unique_suffix}@example.com"
        result = await user_service.register_user(
            email=email,
            username=f"changepass-{unique_suffix}",
            password="oldpassword",
            full_name="Change Pass User",
        )

        user_id = (
            uuid.UUID(result["user"]["id"])
            if isinstance(result["user"]["id"], str)
            else result["user"]["id"]
        )

        # Change password
        success = await user_service.change_password(
            user_id, "oldpassword", "newpassword123"
        )

        assert success is True

        # Verify new password works
        auth_result = await user_service.authenticate_user(email, "newpassword123")
        assert str(auth_result["user"]["id"]) == str(user_id)

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, user_service, async_db) -> None:
        """Test password change with wrong current password."""
        # Register user
        unique_suffix = uuid.uuid4().hex[:8]
        result = await user_service.register_user(
            email=f"wrongcurrent-{unique_suffix}@example.com",
            username=f"wrongcurrent-{unique_suffix}",
            password="correctpassword",
            full_name="Wrong Current User",
        )

        user_id = (
            uuid.UUID(result["user"]["id"])
            if isinstance(result["user"]["id"], str)
            else result["user"]["id"]
        )

        # Try to change password with wrong current password
        with pytest.raises(HTTPException) as exc_info:
            await user_service.change_password(
                user_id, "wrongpassword", "newpassword123"
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Current password is incorrect" in str(exc_info.value.detail)


class TestAuthenticationEndpoints:
    """Test suite for authentication API endpoints."""

    @pytest.fixture
    def client(self, test_app):
        """Create test client."""
        return TestClient(test_app)

    def test_register_endpoint_success(self, client) -> None:
        """Test user registration endpoint."""
        unique_suffix = uuid.uuid4().hex[:8]
        user_data = {
            "email": f"register-{unique_suffix}@example.com",
            "name": f"Register User {unique_suffix}",
            "password": "StrongP@ssw0rd123!",
            "confirm_password": "StrongP@ssw0rd123!",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()

        assert "user" in data
        assert "token" in data
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["name"] == user_data["name"]
        assert "access_token" in data["token"]
        assert "refresh_token" in data["token"]

    def test_register_endpoint_password_mismatch(self, client) -> None:
        """Test registration with password mismatch."""
        unique_suffix = uuid.uuid4().hex[:8]
        user_data = {
            "email": f"mismatch-{unique_suffix}@example.com",
            "name": f"Mismatch User {unique_suffix}",
            "password": "StrongP@ssw0rd123!",
            "confirm_password": "different_password",
        }

        response = client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 400
        data = response.json()
        assert "Passwords do not match" in data["detail"]

    def test_login_endpoint_success(self, client) -> None:
        """Test user login endpoint."""
        # First register a user
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"login-{unique_suffix}@example.com"
        user_data = {
            "email": email,
            "name": f"Login User {unique_suffix}",
            "password": "StrongP@ssw0rd123!",
            "confirm_password": "StrongP@ssw0rd123!",
        }
        register_response = client.post("/api/v1/auth/register", json=user_data)

        # Ensure registration succeeded before testing login
        if register_response.status_code != 201:
            print(f"Registration failed: {register_response.status_code}")
            print(f"Response: {register_response.json()}")
        assert register_response.status_code == 201, (
            "Registration must succeed before login test"
        )

        # Then login
        login_data = {"email": email, "password": "StrongP@ssw0rd123!"}

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()

        assert "user" in data
        assert "token" in data
        assert data["user"]["email"] == login_data["email"]
        assert "access_token" in data["token"]

    def test_login_endpoint_wrong_password(self, client) -> None:
        """Test login with wrong password."""
        # Register user first
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"wrongpass-{unique_suffix}@example.com"
        user_data = {
            "email": email,
            "name": f"Wrong Pass User {unique_suffix}",
            "password": "correctpassword",
            "confirm_password": "correctpassword",
        }
        client.post("/api/v1/auth/register", json=user_data)

        # Try login with wrong password
        login_data = {"email": email, "password": "wrongpassword"}

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "Invalid credentials" in data["detail"]

    def test_refresh_token_endpoint(self, client) -> None:
        """Test token refresh endpoint."""
        # Register and get tokens
        unique_suffix = uuid.uuid4().hex[:8]
        user_data = {
            "email": f"refresh-{unique_suffix}@example.com",
            "name": f"Refresh User {unique_suffix}",
            "password": "StrongP@ssw0rd123!",
            "confirm_password": "StrongP@ssw0rd123!",
        }
        register_response = client.post("/api/v1/auth/register", json=user_data)
        refresh_token = register_response.json()["token"]["refresh_token"]

        # Refresh tokens
        refresh_data = {"refresh_token": refresh_token}
        response = client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_get_current_user_endpoint(self, client) -> None:
        """Test get current user endpoint."""
        # Register user and get token
        unique_suffix = uuid.uuid4().hex[:8]
        user_data = {
            "email": f"current-{unique_suffix}@example.com",
            "name": f"Current User {unique_suffix}",
            "password": "StrongP@ssw0rd123!",
            "confirm_password": "StrongP@ssw0rd123!",
        }
        register_response = client.post("/api/v1/auth/register", json=user_data)
        access_token = register_response.json()["token"]["access_token"]

        # Get current user
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["name"] == user_data["name"]

    def test_get_current_user_unauthorized(self, client) -> None:
        """Test get current user without token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401  # No Authorization header = Unauthorized

    def test_logout_endpoint(self, client) -> None:
        """Test logout endpoint."""
        # Register user and get token
        unique_suffix = uuid.uuid4().hex[:8]
        user_data = {
            "email": f"logout-{unique_suffix}@example.com",
            "name": f"Logout User {unique_suffix}",
            "password": "StrongP@ssw0rd123!",
            "confirm_password": "StrongP@ssw0rd123!",
        }
        register_response = client.post("/api/v1/auth/register", json=user_data)
        access_token = register_response.json()["token"]["access_token"]

        # Logout
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/api/v1/auth/logout", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "Successfully logged out" in data["message"]

    def test_get_oauth_providers_endpoint(self, client) -> None:
        """Test get available OAuth providers endpoint."""
        response = client.get("/api/v1/auth/providers")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)

    def test_validate_token_endpoint(self, client) -> None:
        """Test token validation endpoint."""
        # Register user and get token
        unique_suffix = uuid.uuid4().hex[:8]
        user_data = {
            "email": f"validate-{unique_suffix}@example.com",
            "name": f"Validate User {unique_suffix}",
            "password": "StrongP@ssw0rd123!",
            "confirm_password": "StrongP@ssw0rd123!",
        }
        register_response = client.post("/api/v1/auth/register", json=user_data)
        access_token = register_response.json()["token"]["access_token"]

        # Validate token
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/api/v1/auth/validate-token", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "user_id" in data
        assert "email" in data
