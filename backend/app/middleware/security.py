"""
Security middleware for headers, CSRF protection, and other security measures.
"""

import secrets
import hashlib
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..core.config import get_settings

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""

        response = await call_next(request)

        # Security headers
        response.headers.update({
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Enable XSS filtering
            "X-XSS-Protection": "1; mode=block",

            # Control page embedding in frames
            "X-Frame-Options": "DENY",

            # Strict transport security (HTTPS only)
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",

            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),

            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Permissions policy
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=(), "
                "vibrate=(), "
                "fullscreen=()"
            ),

            # Server header obfuscation
            "Server": "JEEX-API",

            # Remove potentially sensitive headers
            "X-Powered-By": "",
        })

        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing operations."""

    def __init__(self, app, exempt_paths: Optional[list] = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            # Specific stateless auth endpoints that don't set cookies
            "/auth/register",
            "/auth/login",
            "/auth/refresh",
            "/auth/validate-token",
            "/auth/change-password",
            # Note: /auth/oauth/callback excluded because it sets cookies
        ]
        self.state_changing_methods = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        """Check CSRF protection for state-changing requests."""

        # Skip CSRF protection for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Skip for non-state-changing methods
        if request.method not in self.state_changing_methods:
            return await call_next(request)

        # Skip for API endpoints using JWT (stateless)
        if request.url.path.startswith("/api/"):
            return await call_next(request)

        # Validate CSRF token for cookie-based authentication
        if not await self._validate_csrf_token(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed"
            )

        return await call_next(request)

    async def _validate_csrf_token(self, request: Request) -> bool:
        """Validate CSRF token from request."""

        # Get CSRF token from header or form data
        csrf_token = request.headers.get("X-CSRF-Token")

        if not csrf_token:
            # Try to get from form data for form submissions
            if hasattr(request, 'form'):
                form = await request.form()
                csrf_token = form.get("csrf_token")

        if not csrf_token:
            return False

        # Get expected token from session/cookie
        expected_token = request.cookies.get("csrf_token")

        if not expected_token:
            return False

        # Compare tokens (constant time comparison)
        return secrets.compare_digest(csrf_token, expected_token)


class SecurityService:
    """Service for security-related operations."""

    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a new CSRF token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        """Hash password with salt (additional security layer)."""
        if not salt:
            salt = secrets.token_hex(32)

        # Use PBKDF2 with SHA-256
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )

        return hash_obj.hex(), salt

    @staticmethod
    def verify_password_hash(password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash."""
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )

        return secrets.compare_digest(hash_obj.hex(), hashed)

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure random token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def validate_input_length(value: str, max_length: int, field_name: str = "input") -> bool:
        """Validate input length to prevent DoS attacks."""
        if len(value) > max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} exceeds maximum length of {max_length} characters"
            )
        return True

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        import re
        import os.path

        # Remove path components
        filename = os.path.basename(filename)

        # Replace dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # Remove null bytes
        filename = filename.replace('\x00', '')

        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext

        return filename

    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Basic email format validation."""
        import re

        if email.count('@') != 1:
            return False

        local_part, domain_part = email.split('@', 1)

        if not local_part or not domain_part:
            return False

        if '..' in local_part or '..' in domain_part:
            return False

        pattern = r"^[a-zA-Z0-9](?:[a-zA-Z0-9._%+-]{0,62}[a-zA-Z0-9])?@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
        return re.match(pattern, email) is not None

    @staticmethod
    def check_password_strength(password: str) -> dict:
        """Check password strength and return recommendations."""
        issues = []
        score = 0

        if len(password) >= 8:
            score += 1
        else:
            issues.append("Password must be at least 8 characters long")

        if any(c.isupper() for c in password):
            score += 1
        else:
            issues.append("Password must contain at least one uppercase letter")

        if any(c.islower() for c in password):
            score += 1
        else:
            issues.append("Password must contain at least one lowercase letter")

        if any(c.isdigit() for c in password):
            score += 1
        else:
            issues.append("Password must contain at least one digit")

        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        else:
            issues.append("Password must contain at least one special character")

        strength_levels = {
            0: "Very Weak",
            1: "Weak",
            2: "Fair",
            3: "Good",
            4: "Strong",
            5: "Very Strong"
        }

        return {
            "score": score,
            "strength": strength_levels[score],
            "is_strong": score >= 4,
            "issues": issues
        }

    @staticmethod
    def generate_audit_log_entry(
        user_id: Optional[str],
        action: str,
        resource: str,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict:
        """Generate standardized audit log entry."""
        from datetime import datetime

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "session_id": SecurityService.generate_secure_token(16)
        }


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request size for DoS protection."""

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        """Check request size limits."""

        # Check Content-Length header
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                content_length_int = int(content_length)
                if content_length_int < 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid Content-Length header: value must be non-negative"
                    )
                if content_length_int > self.max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request size exceeds maximum allowed size of {self.max_size} bytes"
                    )
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Content-Length header: must be a valid integer"
                )

        return await call_next(request)
