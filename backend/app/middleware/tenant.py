"""
Tenant isolation middleware to ensure multi-tenant data separation.
"""

import uuid
from collections.abc import Iterable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.auth import AuthService
from ..core.database import get_db


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
            return await call_next(request)

        # Extract tenant context from JWT token
        tenant_id = await self._extract_tenant_from_request(request)

        if tenant_id:
            # Add tenant context to request state
            request.state.tenant_id = tenant_id
        else:
            # For authenticated endpoints, tenant is required
            if request.url.path.startswith("/api/"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

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
        try:
            # Get Authorization header
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None

            token = authorization.split(" ")[1]

            # Get database session
            async for db in get_db():
                auth_service = AuthService(db)
                user = await auth_service.get_user_by_token(token)

                if user and user.is_active:
                    return user.tenant_id
                break

            return None

        except Exception:
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
