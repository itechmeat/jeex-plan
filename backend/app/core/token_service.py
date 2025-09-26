"""
Token service for JWT token management.
Separated from AuthService to follow Single Responsibility Principle.
"""

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from .config import get_settings

settings = get_settings()


class TokenService:
    """Service responsible only for token operations."""

    def __init__(self, secret_key: str | None = None, algorithm: str | None = None):
        self.secret_key = secret_key or settings.SECRET_KEY
        self.algorithm = algorithm or settings.ALGORITHM

    def create_access_token(
        self,
        data: dict[str, Any],
        expires_delta: timedelta | None = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire, "type": "access"})

        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            raise ValueError(f"Failed to create access token: {e}") from e

    def create_refresh_token(
        self,
        data: dict[str, Any],
        expires_delta: timedelta | None = None
    ) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )

        to_encode.update({"exp": expire, "type": "refresh"})

        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            raise ValueError(f"Failed to create refresh token: {e}") from e

    def verify_token(self, token: str, token_type: str = "access") -> dict[str, Any] | None:
        """Verify and decode JWT token."""
        if not token or not isinstance(token, str):
            return None

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            if payload.get("type") != token_type:
                return None

            # Check if token is expired
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                return None

            return payload
        except JWTError:
            return None
        except Exception:
            return None

    def create_tokens_for_user_data(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create both access and refresh tokens for user data."""
        if not user_data or "id" not in user_data:
            raise ValueError("Invalid user data provided")

        token_data = {
            "sub": str(user_data["id"]),
            "email": user_data.get("email", ""),
            "tenant_id": str(user_data.get("tenant_id", "")),
            "username": user_data.get("username", ""),
            "full_name": user_data.get("full_name", ""),
        }

        try:
            access_token = self.create_access_token(token_data)
            refresh_token = self.create_refresh_token(token_data)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            }
        except Exception as e:
            raise ValueError(f"Failed to create tokens: {e}") from e

    def extract_user_id_from_token(self, token: str) -> str | None:
        """Extract user ID from token."""
        payload = self.verify_token(token)
        if not payload:
            return None
        return payload.get("sub")

    def extract_tenant_id_from_token(self, token: str) -> str | None:
        """Extract tenant ID from token."""
        payload = self.verify_token(token)
        if not payload:
            return None
        return payload.get("tenant_id")