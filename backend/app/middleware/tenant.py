"""
Tenant isolation middleware to ensure multi-tenant data separation.
"""

import uuid
from collections.abc import Iterable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

# Removed auth and database imports - no longer needed in middleware


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce tenant isolation for all API requests."""

    def __init__(
        self, app, excluded_path_prefixes: Iterable[str] | None = None
    ) -> None:
        super().__init__(app)
        default_prefixes = (
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/health",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/agents/health",
            "/",
        )
        self.excluded_prefixes = tuple(excluded_path_prefixes or default_prefixes)

    async def dispatch(self, request: Request, call_next):
        """Process request with tenant isolation checks."""

        # Skip tenant isolation for excluded paths
        if self._is_excluded_path(request.url.path):
            request.state.tenant_id = None
            return await call_next(request)

        # Extract tenant context from JWT token
        tenant_id = await self._extract_tenant_from_request(request)

        # Add tenant context to request state (may be None)
        # Authentication is enforced by individual endpoints via dependencies
        request.state.tenant_id = tenant_id

        response = await call_next(request)
        return response

    def _is_excluded_path(self, path: str) -> bool:
        for prefix in self.excluded_prefixes:
            normalized = prefix.rstrip("/")
            if not normalized:
                continue
            if path == normalized or path.startswith(f"{normalized}/"):
                return True
        return False

    async def _extract_tenant_from_request(self, request: Request) -> uuid.UUID | None:
        """Extract tenant ID from JWT token in request."""
        # Get Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None

        try:
            # Extract tenant_id directly from JWT without database call
            from ..core.token_service import TokenService

            token_service = TokenService()
            payload = token_service.verify_token(token)

            if not payload:
                return None

            tenant_id_str = payload.get("tenant_id")
            if not tenant_id_str:
                return None

            return uuid.UUID(tenant_id_str)

        except (ValueError, TypeError):
            return None


class TenantContextManager:
    """Helper class to manage tenant context in request processing."""

    @staticmethod
    def get_tenant_id(request: Request) -> uuid.UUID | None:
        """Get tenant ID from request state."""
        state = getattr(request, "state", None)
        if state is None:
            return None
        if not hasattr(state, "tenant_id"):
            return None
        tenant_id = state.tenant_id
        # Check for None or empty string (defensive: should never be empty string in practice)
        if tenant_id in (None, ""):
            return None
        return tenant_id

    @staticmethod
    def require_tenant_id(request: Request) -> uuid.UUID:
        """Get tenant ID from request state or raise error."""
        tenant_id = TenantContextManager.get_tenant_id(request)
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant context required",
            )
        return tenant_id

    @staticmethod
    def set_tenant_id(request: Request, tenant_id: uuid.UUID) -> None:
        """Set tenant ID in request state."""
        request.state.tenant_id = tenant_id


def get_tenant_context(request: Request) -> uuid.UUID:
    """Dependency function to get tenant context from request."""
    return TenantContextManager.require_tenant_id(request)


def get_current_tenant_id(request: Request) -> uuid.UUID:
    """FastAPI dependency to get current tenant ID."""
    return get_tenant_context(request)
