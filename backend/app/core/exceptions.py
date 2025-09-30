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

    def __repr__(self) -> str:
        """Return detailed string representation for logging and debugging."""
        return f"AuthenticationError(message={self.message!r}, status_code={self.status_code})"


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

    def __repr__(self) -> str:
        """Return detailed string representation for logging and debugging."""
        return f"AuthorizationError(message={self.message!r}, status_code={self.status_code})"


class ValidationError(Exception):
    """Domain-specific validation error."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int = 422,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.details = details or {}
        self.status_code = status_code

    def __repr__(self) -> str:
        """Return detailed string representation for logging and debugging."""
        field_info = f", field={self.field!r}" if self.field else ""
        return f"ValidationError(message={self.message!r}{field_info}, status_code={self.status_code})"


class TenantError(Exception):
    """Domain-specific tenant-related error."""

    def __init__(
        self,
        message: str,
        tenant_id: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.tenant_id = tenant_id
        self.details = details or {}
        self.status_code = status_code

    def __repr__(self) -> str:
        """Return detailed string representation for logging and debugging."""
        tenant_info = f", tenant_id={self.tenant_id!r}" if self.tenant_id else ""
        return f"TenantError(message={self.message!r}{tenant_info}, status_code={self.status_code})"
