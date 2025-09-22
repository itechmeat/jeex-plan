"""
Tenant isolation middleware to ensure multi-tenant data separation.
"""

import uuid
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.auth import AuthService
from ..core.database import get_db


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce tenant isolation for all API requests."""

    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/health",
            "/auth/login",
            "/auth/register",
            "/auth/oauth",
            "/auth/callback"
        ]

    async def dispatch(self, request: Request, call_next):
        """Process request with tenant isolation checks."""

        # Skip tenant isolation for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
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
                    detail="Authentication required"
                )

        response = await call_next(request)
        return response

    async def _extract_tenant_from_request(self, request: Request) -> Optional[uuid.UUID]:
        """Extract tenant ID from JWT token in request."""
        try:
            # Get Authorization header
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None

            token = authorization.split(" ")[1]

            # Get database session
            async with get_db() as db:
                auth_service = AuthService(db)
                user = await auth_service.get_user_by_token(token)

                if user and user.is_active:
                    return user.tenant_id

            return None

        except Exception:
            return None


class TenantContextManager:
    """Helper class to manage tenant context in request processing."""

    @staticmethod
    def get_tenant_id(request: Request) -> Optional[uuid.UUID]:
        """Get tenant ID from request state."""
        return getattr(request.state, 'tenant_id', None)

    @staticmethod
    def require_tenant_id(request: Request) -> uuid.UUID:
        """Get tenant ID from request state or raise error."""
        tenant_id = TenantContextManager.get_tenant_id(request)
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant context required"
            )
        return tenant_id

    @staticmethod
    def set_tenant_id(request: Request, tenant_id: uuid.UUID):
        """Set tenant ID in request state."""
        request.state.tenant_id = tenant_id


def get_tenant_context(request: Request) -> uuid.UUID:
    """Dependency function to get tenant context from request."""
    return TenantContextManager.require_tenant_id(request)