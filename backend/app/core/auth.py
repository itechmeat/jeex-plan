"""
Core authentication module with JWT and OAuth2 support.
Refactored to follow Single Responsibility Principle.
"""

import uuid
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.stdlib import BoundLogger

from ..core.config import get_settings
from ..core.database import get_db
from ..core.logger import get_logger
from ..core.password_service import PasswordService
from ..core.token_service import TokenService
from ..models.user import User
from ..repositories.tenant import TenantRepository
from ..repositories.user import UserRepository

settings = get_settings()
security = HTTPBearer()


class AuthService:
    """Service for handling authentication and authorization."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: UUID | None = None,
        *,
        logger: BoundLogger | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_repo = UserRepository(db, tenant_id) if tenant_id else None
        self.tenant_repo = TenantRepository(db)

        # Use separate services for specific responsibilities
        self.password_service = PasswordService()
        self.token_service = TokenService()
        self.logger = logger or get_logger("auth_service")

    async def get_user_by_token(self, token: str) -> User | None:
        """Get user from JWT token."""
        payload = self.token_service.verify_token(token)
        if not payload:
            self.logger.warning(
                "auth.invalid_token", extra={"reason": "payload_missing"}
            )
            return None

        user_id = payload.get("sub")
        token_tenant_id = payload.get("tenant_id")
        if not user_id:
            self.logger.warning(
                "auth.invalid_token",
                extra={"reason": "missing_subject"},
            )
            return None

        try:
            user_uuid = uuid.UUID(user_id)
        except (ValueError, TypeError):
            self.logger.warning(
                "auth.invalid_token",
                extra={"reason": "malformed_subject"},
            )
            return None

        # For token validation, we need to search across all tenants
        from sqlalchemy import select

        from ..models.user import User

        stmt = select(User).where(
            User.id == user_uuid,
            User.is_active.is_(True),
            User.is_deleted.is_(False),
        )

        if token_tenant_id:
            try:
                tenant_uuid = uuid.UUID(token_tenant_id)
            except (ValueError, TypeError):
                self.logger.warning(
                    "auth.invalid_tenant_claim",
                    extra={"token_tenant_id": token_tenant_id},
                )
                return None

            stmt = stmt.where(User.tenant_id == tenant_uuid)

        try:
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                self.logger.warning(
                    "auth.user_not_found_for_token",
                    extra={"user_id": str(user_uuid), "tenant_id": token_tenant_id},
                )
            return user
        except (SQLAlchemyError, AttributeError) as exc:
            self.logger.exception(
                "auth.user_lookup_failed",
                extra={"user_id": str(user_uuid), "error": str(exc)},
            )
            return None

    async def authenticate_user(
        self, email: str, password: str, tenant_id: uuid.UUID | None = None
    ) -> User | None:
        """Authenticate user with email and password."""
        if not email or not password:
            return None

        # For authentication, we need to search across all tenants
        from sqlalchemy import select

        from ..models.user import User

        stmt = select(User).where(
            User.email == email, User.is_active.is_(True), User.is_deleted.is_(False)
        )

        scoped_tenant = tenant_id or self.tenant_id
        if scoped_tenant:
            stmt = stmt.where(User.tenant_id == scoped_tenant)
        else:
            self.logger.warning(
                "auth.tenant_scope_missing_for_login",
                extra={"email": email},
            )

        try:
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user or not user.hashed_password:
                self.logger.warning(
                    "auth.login_failed_user_not_found_or_no_password",
                    extra={"email": email},
                )
                return None

            if not self.password_service.verify_password(
                password, user.hashed_password
            ):
                self.logger.warning(
                    "auth.login_failed_bad_password",
                    extra={
                        "user_id": str(user.id) if user else None,
                        "tenant_id": str(user.tenant_id) if user else None,
                    },
                )
                return None

            # Check if password hash needs updating
            new_hash = self.password_service.update_hash_if_needed(
                password, user.hashed_password
            )
            if new_hash:
                user.hashed_password = new_hash
                await self.db.commit()

            return user
        except (SQLAlchemyError, AttributeError) as exc:
            self.logger.exception(
                "auth.login_error",
                extra={"email": email, "error": str(exc)},
            )
            return None

    async def create_tokens_for_user(self, user: User) -> dict[str, Any]:
        """Create access and refresh tokens for user."""
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "tenant_id": str(user.tenant_id) if user.tenant_id is not None else None,
            "username": user.username,
            "full_name": user.full_name or "",
        }

        return self.token_service.create_tokens_for_user_data(user_data)

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any] | None:
        """Create new access token from refresh token."""
        payload = self.token_service.verify_token(refresh_token, "refresh")
        if not payload:
            return None

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")

        if not user_id or not tenant_id:
            return None

        try:
            user_uuid = uuid.UUID(user_id)
            tenant_uuid = uuid.UUID(tenant_id)
        except (ValueError, TypeError):
            return None

        if (
            self.user_repo is None
            or getattr(self.user_repo, "tenant_id", None) != tenant_uuid
        ):
            self.user_repo = UserRepository(self.db, tenant_uuid)

        user = await self.user_repo.get_by_id(user_uuid)
        if not user or not user.is_active:
            return None

        return await self.create_tokens_for_user(user)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials, db: AsyncSession
) -> User:
    """Dependency to get current authenticated user."""
    auth_service = AuthService(db)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        user = await auth_service.get_user_by_token(token)

        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user"
            )

        return user
    except Exception as exc:
        raise credentials_exception from exc


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials, db: AsyncSession
) -> User:
    """Dependency to get current active user."""
    user = await get_current_user(credentials, db)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    return user


# FastAPI dependency wrappers
async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency to get current user."""
    return await get_current_user(credentials, db)


async def get_current_active_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency to get current active user."""
    return await get_current_active_user(credentials, db)
