"""
Tests for middleware components.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, Request, status
from starlette.responses import Response

from app.middleware.rate_limit import RateLimitMiddleware, RateLimitService
from app.middleware.security import (
    CSRFProtectionMiddleware,
    SecurityHeadersMiddleware,
    SecurityService,
)
from app.middleware.tenant import TenantContextManager, TenantIsolationMiddleware


class DummyRedisPipeline:
    """Simple pipeline stub for Redis operations in tests."""

    def __init__(self, results) -> None:
        self._results = results

    def zremrangebyscore(self, *args, **kwargs):
        return self

    def zcard(self, *args, **kwargs):
        return self

    def zadd(self, *args, **kwargs):
        return self

    def expire(self, *args, **kwargs):
        return self

    async def execute(self):
        return self._results


class DummyRedisClient:
    """Simple Redis client stub returning pre-defined pipeline results."""

    def __init__(self, results, ttl=60) -> None:
        self._results = results
        self._ttl = ttl

    def pipeline(self):
        return DummyRedisPipeline(self._results)

    async def ttl(self, key):
        return self._ttl

    async def zrem(self, key, member) -> int:
        return 1


class TestTenantIsolationMiddleware:
    """Test tenant isolation middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = Mock()
        return TenantIsolationMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url.path = "/api/v1/projects"
        request.headers = {}
        request.state = SimpleNamespace(tenant_id=None)
        request.app = Mock()
        request.app.state = Mock()
        request.app.state.redis_client = None
        request.client = Mock(host="127.0.0.1")
        return request

    def test_excluded_paths(self, middleware) -> None:
        """Test that excluded paths are configured correctly."""
        expected_prefixes = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/health",
        ]

        for path in expected_prefixes:
            assert middleware._is_excluded_path(path)
            assert middleware._is_excluded_path(f"{path}/subpath")

    @pytest.mark.asyncio
    async def test_excluded_path_bypass(self, middleware, mock_request) -> None:
        """Test that excluded paths bypass tenant isolation."""
        mock_request.url.path = "/docs"
        call_next = AsyncMock(return_value=Response())

        response = await middleware.dispatch(mock_request, call_next)

        # Should call next middleware without tenant checks
        call_next.assert_called_once()
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_auth_for_api_path(self, middleware, mock_request) -> None:
        """Test that API paths require authentication."""
        mock_request.url.path = "/api/v1/projects"
        mock_request.headers = {}  # No Authorization header

        with patch.object(
            middleware,
            '_extract_tenant_from_request',
            new=AsyncMock(return_value=None)
        ):
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(mock_request, AsyncMock())

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_valid_tenant_extraction(self, middleware, mock_request) -> None:
        """Test successful tenant extraction and context setting."""
        tenant_id = uuid.uuid4()
        mock_request.url.path = "/api/v1/projects"

        with patch.object(
            middleware,
            '_extract_tenant_from_request',
            new=AsyncMock(return_value=tenant_id)
        ):
            call_next = AsyncMock(return_value=Response())
            await middleware.dispatch(mock_request, call_next)

            # Should set tenant context
            assert hasattr(mock_request.state, 'tenant_id')
            assert mock_request.state.tenant_id == tenant_id
            call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_tenant_from_valid_token(self, middleware, mock_request) -> None:
        """Test tenant extraction from valid JWT token."""
        mock_request.headers = {"Authorization": "Bearer valid_token"}

        async def fake_get_db():
            yield mock_db

        mock_db = AsyncMock()

        with patch('app.middleware.tenant.get_db', side_effect=fake_get_db):

            with patch('app.middleware.tenant.AuthService') as mock_auth_service:
                mock_user = Mock()
                mock_user.is_active = True
                mock_user.tenant_id = uuid.uuid4()

                mock_auth_service.return_value.get_user_by_token = AsyncMock(return_value=mock_user)

                tenant_id = await middleware._extract_tenant_from_request(mock_request)

                assert tenant_id == mock_user.tenant_id

    @pytest.mark.asyncio
    async def test_extract_tenant_from_invalid_token(self, middleware, mock_request) -> None:
        """Test tenant extraction from invalid token."""
        mock_request.headers = {"Authorization": "Bearer invalid_token"}

        async def fake_get_db():
            yield mock_db

        mock_db = AsyncMock()

        with patch('app.middleware.tenant.get_db', side_effect=fake_get_db):

            with patch('app.middleware.tenant.AuthService') as mock_auth_service:
                mock_auth_service.return_value.get_user_by_token = AsyncMock(
                    side_effect=HTTPException(status_code=401, detail="Invalid token")
                )

                tenant_id = await middleware._extract_tenant_from_request(mock_request)

                assert tenant_id is None

    def test_tenant_context_manager_get_tenant_id(self) -> None:
        """Test TenantContextManager get_tenant_id."""
        request = Mock(spec=Request)
        tenant_id = uuid.uuid4()
        request.state.tenant_id = tenant_id

        result = TenantContextManager.get_tenant_id(request)
        assert result == tenant_id

    def test_tenant_context_manager_require_tenant_id_success(self) -> None:
        """Test TenantContextManager require_tenant_id with valid tenant."""
        request = Mock(spec=Request)
        tenant_id = uuid.uuid4()
        request.state = SimpleNamespace(tenant_id=tenant_id)

        result = TenantContextManager.require_tenant_id(request)
        assert result == tenant_id

    def test_tenant_context_manager_require_tenant_id_missing(self) -> None:
        """Test TenantContextManager require_tenant_id with missing tenant."""
        request = Mock(spec=Request)
        request.state = SimpleNamespace()
        # No tenant_id attribute

        with pytest.raises(HTTPException) as exc_info:
            TenantContextManager.require_tenant_id(request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    @pytest.fixture
    def mock_redis(self):
        """Create dummy Redis client."""
        return DummyRedisClient([0, 1, 5, 1])

    @pytest.fixture
    def middleware(self, mock_redis):
        """Create rate limit middleware."""
        app = Mock()
        return RateLimitMiddleware(app, mock_redis, default_requests=100, default_window=60)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url.path = "/api/v1/test"
        request.headers = {}
        request.state = SimpleNamespace()
        request.client = SimpleNamespace(host="127.0.0.1")
        request.app = SimpleNamespace(state=SimpleNamespace())
        return request

    @pytest.mark.asyncio
    async def test_excluded_paths_bypass(self, middleware, mock_request) -> None:
        """Test that excluded paths bypass rate limiting."""
        mock_request.url.path = "/health"
        call_next = AsyncMock(return_value=Response())

        response = await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once()
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_no_redis_bypass(self, mock_request) -> None:
        """Test that missing Redis client bypasses rate limiting."""
        app = Mock()
        middleware = RateLimitMiddleware(app, None)
        call_next = AsyncMock(return_value=Response())

        mock_request.app.state.redis_client = None

        response = await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once()
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_within_bounds(self, middleware, mock_request, mock_redis) -> None:
        """Test request within rate limits."""
        call_next = AsyncMock()
        response_mock = Response()
        call_next.return_value = response_mock

        middleware = RateLimitMiddleware(Mock(), DummyRedisClient([0, 1, 50, 1]))

        response = await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once()
        assert response == response_mock

        # Check that rate limit headers are added
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, middleware, mock_request, mock_redis) -> None:
        """Test request exceeding rate limits."""
        middleware = RateLimitMiddleware(Mock(), DummyRedisClient([0, 1, 150, 1]))

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, AsyncMock())

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit exceeded" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_rate_limit_config_default(self, middleware, mock_request) -> None:
        """Test default rate limit configuration."""
        config = await middleware._get_rate_limit_config(mock_request)

        assert config["requests"] == 100  # Default
        assert config["window"] == 60  # Default

    @pytest.mark.asyncio
    async def test_get_rate_limit_config_login_endpoint(self, middleware, mock_request) -> None:
        """Test rate limit configuration for login endpoint."""
        mock_request.url.path = "/auth/login"

        config = await middleware._get_rate_limit_config(mock_request)

        assert config["requests"] == 5  # Stricter for login
        assert config["window"] == 300  # 5 minutes

    @pytest.mark.asyncio
    async def test_generate_rate_limit_key(self, middleware, mock_request) -> None:
        """Test rate limit key generation."""
        with patch.object(
            middleware,
            '_get_client_identifier',
            new=AsyncMock(return_value="client_123")
        ):
            key = await middleware._generate_rate_limit_key(mock_request)

            assert key.startswith("rl:")
            assert len(key) > 10  # Should be a hash

    @pytest.mark.asyncio
    async def test_get_client_identifier_with_tenant(self, middleware, mock_request) -> None:
        """Test client identifier with tenant context."""
        tenant_id = uuid.uuid4()
        mock_request.state.tenant_id = tenant_id

        identifier = await middleware._get_client_identifier(mock_request)

        assert identifier == f"tenant:{tenant_id}"

    @pytest.mark.asyncio
    async def test_get_client_identifier_with_ip(self, middleware, mock_request) -> None:
        """Test client identifier fallback to IP."""
        # No tenant context
        mock_request.state = SimpleNamespace(tenant_id=None)

        identifier = await middleware._get_client_identifier(mock_request)

        assert identifier == "ip:127.0.0.1"

    def test_get_client_ip_forwarded(self, middleware, mock_request) -> None:
        """Test client IP extraction from X-Forwarded-For header."""
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}

        ip = middleware._get_client_ip(mock_request)

        assert ip == "192.168.1.1"

    def test_get_client_ip_real_ip(self, middleware, mock_request) -> None:
        """Test client IP extraction from X-Real-IP header."""
        mock_request.headers = {"X-Real-IP": "192.168.1.2"}

        ip = middleware._get_client_ip(mock_request)

        assert ip == "192.168.1.2"


class TestRateLimitService:
    """Test rate limit service."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        return AsyncMock()

    @pytest.fixture
    def rate_limit_service(self, mock_redis):
        """Create rate limit service."""
        return RateLimitService(mock_redis)

    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self, rate_limit_service, mock_redis) -> None:
        """Test getting rate limit status."""
        mock_redis.zcount.return_value = 25
        mock_redis.ttl.return_value = 30

        status = await rate_limit_service.get_rate_limit_status("test_key")

        assert status["requests_made"] == 25
        assert status["requests_remaining"] == 75  # 100 - 25
        assert status["reset_time"] is not None

    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, rate_limit_service, mock_redis) -> None:
        """Test resetting rate limit."""
        mock_redis.delete.return_value = 1

        result = await rate_limit_service.reset_rate_limit("test_key")

        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_set_custom_limit(self, rate_limit_service, mock_redis) -> None:
        """Test setting custom rate limit."""
        result = await rate_limit_service.set_custom_limit(
            "user_123",
            requests=200,
            window=120,
            duration=3600
        )

        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_expired_limits(self, rate_limit_service, mock_redis) -> None:
        """Test cleanup of expired rate limits."""
        async def scan_iter(*args, **kwargs):
            for key in ["rl:key1", "rl:key2"]:
                yield key

        mock_redis.scan_iter = scan_iter
        mock_redis.zremrangebyscore = AsyncMock(return_value=5)
        mock_redis.zcard = AsyncMock(return_value=0)
        mock_redis.delete = AsyncMock(return_value=1)

        expired_count = await rate_limit_service.cleanup_expired_limits()

        assert expired_count == 10  # 5 + 5
        assert mock_redis.delete.await_count == 2  # Both keys deleted


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""

    @pytest.fixture
    def middleware(self):
        """Create security headers middleware."""
        app = Mock()
        return SecurityHeadersMiddleware(app)

    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        response = Response()
        return response

    @pytest.mark.asyncio
    async def test_security_headers_added(self, middleware) -> None:
        """Test that security headers are added to response."""
        call_next = AsyncMock(return_value=Response())
        request = Mock(spec=Request)

        response = await middleware.dispatch(request, call_next)

        # Check for important security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "Strict-Transport-Security" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_csp_header_content(self, middleware) -> None:
        """Test Content Security Policy header content."""
        call_next = AsyncMock(return_value=Response())
        request = Mock(spec=Request)

        response = await middleware.dispatch(request, call_next)

        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp
        assert "frame-ancestors 'none'" in csp


class TestCSRFProtectionMiddleware:
    """Test CSRF protection middleware."""

    @pytest.fixture
    def middleware(self):
        """Create CSRF protection middleware."""
        app = Mock()
        return CSRFProtectionMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url.path = "/api/form-submit"
        request.method = "POST"
        request.headers = {}
        request.cookies = {}
        return request

    @pytest.mark.asyncio
    async def test_excluded_paths_bypass(self, middleware, mock_request) -> None:
        """Test that excluded paths bypass CSRF protection."""
        mock_request.url.path = "/docs"
        call_next = AsyncMock(return_value=Response())

        await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_method_bypass(self, middleware, mock_request) -> None:
        """Test that GET requests bypass CSRF protection."""
        mock_request.method = "GET"
        call_next = AsyncMock(return_value=Response())

        await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_endpoints_bypass(self, middleware, mock_request) -> None:
        """Test that API endpoints bypass CSRF protection."""
        mock_request.url.path = "/api/v1/projects"
        call_next = AsyncMock(return_value=Response())

        await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_csrf_token(self, middleware, mock_request) -> None:
        """Test CSRF protection with missing token."""
        # Non-API, state-changing request without CSRF token
        mock_request.url.path = "/form-submit"

        with patch.object(
            middleware,
            '_validate_csrf_token',
            new=AsyncMock(return_value=False)
        ):
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(mock_request, AsyncMock())

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "CSRF token validation failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_csrf_token_success(self, middleware, mock_request) -> None:
        """Test successful CSRF token validation."""
        token = "valid_csrf_token"
        mock_request.headers = {"X-CSRF-Token": token}
        mock_request.cookies = {"csrf_token": token}

        with patch('app.middleware.security.secrets.compare_digest', return_value=True) as mock_compare:
            result = await middleware._validate_csrf_token(mock_request)
            assert result is True
            mock_compare.assert_called_once_with(token, token)

    @pytest.mark.asyncio
    async def test_validate_csrf_token_mismatch(self, middleware, mock_request) -> None:
        """Test CSRF token validation with mismatch."""
        mock_request.headers = {"X-CSRF-Token": "token1"}
        mock_request.cookies = {"csrf_token": "token2"}

        with patch('app.middleware.security.secrets.compare_digest', return_value=False) as mock_compare:
            result = await middleware._validate_csrf_token(mock_request)
            assert result is False
            mock_compare.assert_called_once_with("token1", "token2")


class TestSecurityService:
    """Test security service functionality."""

    def test_generate_csrf_token(self) -> None:
        """Test CSRF token generation."""
        token = SecurityService.generate_csrf_token()

        assert isinstance(token, str)
        assert len(token) > 20  # Should be reasonably long

    def test_hash_password(self) -> None:
        """Test password hashing."""
        password = "test_password123"

        hashed, salt = SecurityService.hash_password(password)

        assert isinstance(hashed, str)
        assert isinstance(salt, str)
        assert hashed != password
        assert len(hashed) > 50  # PBKDF2 hashes are long

    def test_verify_password_hash_success(self) -> None:
        """Test password hash verification success."""
        password = "test_password123"
        hashed, salt = SecurityService.hash_password(password)

        result = SecurityService.verify_password_hash(password, hashed, salt)
        assert result is True

    def test_verify_password_hash_failure(self) -> None:
        """Test password hash verification failure."""
        password = "test_password123"
        wrong_password = "wrong_password"
        hashed, salt = SecurityService.hash_password(password)

        result = SecurityService.verify_password_hash(wrong_password, hashed, salt)
        assert result is False

    def test_generate_secure_token(self) -> None:
        """Test secure token generation."""
        token = SecurityService.generate_secure_token(32)

        assert isinstance(token, str)
        assert len(token) > 20  # URL-safe base64 encoded

    def test_sanitize_filename(self) -> None:
        """Test filename sanitization."""
        dangerous_filename = "../../../etc/passwd"
        sanitized = SecurityService.sanitize_filename(dangerous_filename)

        assert "../" not in sanitized
        assert "passwd" in sanitized  # Original filename preserved

        # Test dangerous characters
        filename_with_dangerous_chars = "test<>:\"/\\|?*file.txt"
        sanitized = SecurityService.sanitize_filename(filename_with_dangerous_chars)

        dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in dangerous_chars:
            assert char not in sanitized

    def test_validate_email_format_valid(self) -> None:
        """Test email format validation with valid emails."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "test+tag@example.org",
            "123@example.com"
        ]

        for email in valid_emails:
            assert SecurityService.validate_email_format(email) is True

    def test_validate_email_format_invalid(self) -> None:
        """Test email format validation with invalid emails."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test..test@example.com",
            "test@example",
            ""
        ]

        for email in invalid_emails:
            assert SecurityService.validate_email_format(email) is False

    def test_check_password_strength(self) -> None:
        """Test password strength checking."""
        # Strong password
        strong_password = "StrongPass123!"
        result = SecurityService.check_password_strength(strong_password)

        assert result["score"] == 5
        assert result["strength"] == "Very Strong"
        assert result["is_strong"] is True
        assert len(result["issues"]) == 0

        # Weak password
        weak_password = "weak"
        result = SecurityService.check_password_strength(weak_password)

        assert result["score"] < 4
        assert result["is_strong"] is False
        assert len(result["issues"]) > 0

    def test_generate_audit_log_entry(self) -> None:
        """Test audit log entry generation."""
        user_id = str(uuid.uuid4())
        action = "LOGIN"
        resource = "auth"
        details = {"ip": "127.0.0.1"}

        log_entry = SecurityService.generate_audit_log_entry(
            user_id=user_id,
            action=action,
            resource=resource,
            details=details,
            ip_address="127.0.0.1",
            user_agent="test-agent"
        )

        assert log_entry["user_id"] == user_id
        assert log_entry["action"] == action
        assert log_entry["resource"] == resource
        assert log_entry["details"] == details
        assert log_entry["ip_address"] == "127.0.0.1"
        assert log_entry["user_agent"] == "test-agent"
        assert "timestamp" in log_entry
        assert "session_id" in log_entry
