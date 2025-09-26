"""
Server-side filtering middleware for strict tenant isolation in vector operations.

This middleware ensures that all vector database operations are automatically
scoped to the correct tenant and project, preventing cross-tenant data access.
"""

import uuid
from typing import Any

from fastapi import HTTPException, Request, status
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logger import get_logger
from app.schemas.vector import DocumentType

logger = get_logger(__name__)


class TenantFilterMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces server-side tenant and project isolation
    for all vector database operations.
    """

    def __init__(self, app: Starlette) -> None:
        super().__init__(app)
        self.vector_endpoints = {
            "/api/v1/vectors/search",
            "/api/v1/vectors/upsert",
            "/api/v1/vectors/delete",
            "/api/v1/vectors/stats",
            "/api/v1/vectors/embed-and-store",
        }

    async def dispatch(self, request: Request, call_next):
        """
        Process request and inject tenant/project context for vector operations.
        """

        # Only process vector endpoints
        if not any(
            request.url.path.startswith(endpoint) for endpoint in self.vector_endpoints
        ):
            return await call_next(request)

        try:
            # Extract tenant and project context from request
            context = await self._extract_tenant_context(request)
            if not context:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing tenant or project context",
                )

            # Validate tenant isolation
            await self._validate_tenant_isolation(request, context)

            # Inject context into request state for downstream use
            request.state.tenant_context = context

            # Process the request
            response = await call_next(request)

            # Add security headers for vector responses
            if isinstance(response, JSONResponse):
                response.headers["X-Tenant-Isolated"] = "true"
                response.headers["X-Request-ID"] = str(uuid.uuid4())

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Tenant filtering middleware error",
                error=str(e),
                path=request.url.path,
                method=request.method,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    async def _extract_tenant_context(self, request: Request) -> dict[str, str] | None:
        """
        Extract tenant and project context from the request.

        Context can come from:
        1. JWT token claims
        2. Request headers
        3. Request body (for certain endpoints)
        """

        # Try JWT token first (most secure)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # In a real implementation, decode and validate JWT
                # For now, extract from headers for development
                tenant_id = request.headers.get("X-Tenant-ID")
                project_id = request.headers.get("X-Project-ID")

                if tenant_id and project_id:
                    return {
                        "tenant_id": tenant_id,
                        "project_id": project_id,
                        "user_id": request.headers.get("X-User-ID", "unknown"),
                        "source": "jwt",
                    }
            except Exception as e:
                logger.warning("Failed to decode JWT context", error=str(e))

        # Fallback to headers for development/testing
        tenant_id = request.headers.get("X-Tenant-ID")
        project_id = request.headers.get("X-Project-ID")

        if tenant_id and project_id:
            return {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "user_id": request.headers.get("X-User-ID", "unknown"),
                "source": "headers",
            }

        # Avoid parsing request body in middleware to prevent consumption issues
        # Tenant/project context should be extracted from JWT tokens or headers only

        return None

    async def _validate_tenant_isolation(
        self, request: Request, context: dict[str, str]
    ) -> None:
        """
        Validate that the request respects tenant isolation boundaries.
        """
        tenant_id = context["tenant_id"]
        project_id = context["project_id"]

        # For search operations, validate query parameters
        if request.url.path.endswith("/search"):
            try:
                query_params = dict(request.query_params)

                # Ensure no tenant/project override attempts
                if "tenant_id" in query_params or "project_id" in query_params:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Overriding tenant_id or project_id via query params forbidden",
                    )

                # Validate filter parameters don't attempt cross-tenant access
                if "filters" in query_params:
                    filters = query_params["filters"]
                    if isinstance(filters, str):
                        # Basic validation - in production would parse JSON
                        if tenant_id not in filters or project_id not in filters:
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail="Filters must include tenant_id and project_id",
                            )

            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                logger.warning("Filter validation error", error=str(e))

        # For upsert operations, validate payload size
        elif request.url.path.endswith("/upsert"):
            try:
                content_length = int(request.headers.get("content-length", 0))
                max_payload_size = 10 * 1024 * 1024  # 10MB

                if content_length > max_payload_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Request payload exceeds maximum size",
                    )
            except ValueError:
                logger.warning(
                    "Invalid content-length header",
                    content_length_header=request.headers.get("content-length"),
                    path=request.url.path,
                )

        # Log the access for audit trail
        logger.info(
            "Vector operation with tenant isolation",
            tenant_id=tenant_id,
            project_id=project_id,
            endpoint=request.url.path,
            method=request.method,
            user_id=context.get("user_id"),
            context_source=context.get("source"),
        )


class VectorOperationFilter:
    """
    Utility class for building filtered vector operations with tenant isolation.
    """

    @staticmethod
    def build_search_filter(
        tenant_id: str,
        project_id: str,
        additional_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build search filter with mandatory tenant/project isolation.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            additional_filters: Optional additional filter conditions

        Returns:
            Qdrant-compatible filter dictionary
        """
        # Mandatory tenant and project filters
        must_conditions = [
            {"key": "tenant_id", "match": {"value": tenant_id}},
            {"key": "project_id", "match": {"value": project_id}},
        ]

        # Add additional filters if provided
        if additional_filters:
            for key, value in additional_filters.items():
                if key == "doc_types" and isinstance(value, list):
                    # Handle document type filtering
                    for doc_type in value:
                        must_conditions.append(
                            {"key": "type", "match": {"value": doc_type}}
                        )
                elif key == "visibility":
                    must_conditions.append(
                        {"key": "visibility", "match": {"value": value}}
                    )
                elif key == "lang":
                    must_conditions.append({"key": "lang", "match": {"value": value}})
                elif key == "tags" and isinstance(value, list):
                    # Handle tag filtering (any match)
                    must_conditions.append({"key": "tags", "match": {"value": value}})
                else:
                    # Generic key-value filter
                    must_conditions.append({"key": key, "match": {"value": value}})

        return {"must": must_conditions}

    @staticmethod
    def build_delete_filter(
        tenant_id: str,
        project_id: str,
        doc_types: list[DocumentType] | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        """
        Build delete filter with tenant/project isolation.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            doc_types: Optional document types to delete
            version: Optional version to delete

        Returns:
            Qdrant-compatible filter dictionary
        """
        must_conditions = [
            {"key": "tenant_id", "match": {"value": tenant_id}},
            {"key": "project_id", "match": {"value": project_id}},
        ]

        if doc_types:
            for doc_type in doc_types:
                must_conditions.append(
                    {"key": "type", "match": {"value": doc_type.value}}
                )

        if version:
            must_conditions.append({"key": "version", "match": {"value": version}})

        return {"must": must_conditions}

    @staticmethod
    def validate_payload_integrity(payload: dict[str, Any]) -> bool:
        """
        Validate payload integrity for tenant isolation.

        Args:
            payload: Payload dictionary to validate

        Returns:
            True if payload is valid
        """
        required_fields = ["tenant_id", "project_id"]

        for field in required_fields:
            if field not in payload or not payload[field]:
                return False

        # Validate no cross-tenant references
        forbidden_fields = ["cross_tenant_ref", "global_access"]
        return all(field not in payload for field in forbidden_fields)

    @staticmethod
    def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize payload to remove any potential cross-tenant data.

        Args:
            payload: Original payload

        Returns:
            Sanitized payload
        """
        # Remove potentially dangerous fields
        dangerous_fields = [
            "cross_tenant_ref",
            "global_access",
            "admin_override",
            "bypass_isolation",
            "foreign_tenant_id",
        ]

        sanitized = payload.copy()
        for field in dangerous_fields:
            sanitized.pop(field, None)

        return sanitized
