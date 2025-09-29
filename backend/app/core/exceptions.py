"""Application-specific exceptions."""

from typing import Any


class AuthenticationError(Exception):
    """Domain-specific authentication error."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        status_code: int = 401,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.status_code = status_code


class AuthorizationError(Exception):
    """Domain-specific authorization error."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        status_code: int = 403,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.status_code = status_code


class ValidationError(Exception):
    """Domain-specific validation error."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.details = details or {}


class TenantError(Exception):
    """Domain-specific tenant-related error."""

    def __init__(
        self,
        message: str,
        tenant_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.tenant_id = tenant_id
        self.details = details or {}
