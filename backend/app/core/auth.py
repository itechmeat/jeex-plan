"""
Core authentication module with JWT and OAuth2 support.
Refactored to follow Single Responsibility Principle.
"""

import uuid
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.database import get_db
from ..core.password_service import PasswordService
from ..core.token_service import TokenService
from ..models.user import User
from ..repositories.tenant import TenantRepository
from ..repositories.user import UserRepository

settings = get_settings()
security = HTTPBearer()


class AuthService:
    """Service for handling authentication and authorization - now focused only on auth logic."""

    def __init__(self, db: AsyncSession, tenant_id: UUID | None = None) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_repo = UserRepository(db, tenant_id) if tenant_id else None
        self.tenant_repo = TenantRepository(db)

        # Use separate services for specific responsibilities
        self.password_service = PasswordService()
        self.token_service = TokenService()

    async def get_user_by_token(self, token: str) -> User | None:
        """Get user from JWT token."""
        payload = self.token_service.verify_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        try:
            user_uuid = uuid.UUID(user_id)
        except (ValueError, TypeError):
            return None

        # For token validation, we need to search across all tenants
        from sqlalchemy import select

        from ..models.user import User

        stmt = select(User).where(
            User.id == user_uuid,
            User.is_active.is_(True),
            User.is_deleted.is_(False)
        )

        try:
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            return user
        except Exception:
            return None

    async def authenticate_user(
        self,
        email: str,
        password: str,
        tenant_id: uuid.UUID | None = None
    ) -> User | None:
        """Authenticate user with email and password."""
        if not email or not password:
            return None

        # For authentication, we need to search across all tenants
        from sqlalchemy import select

        from ..models.user import User

        stmt = select(User).where(
            User.email == email,
            User.is_active.is_(True),
            User.is_deleted.is_(False)
        )

        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)

        try:
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user or not user.hashed_password:
                return None

            if not self.password_service.verify_password(password, user.hashed_password):
                return None

            # Check if password hash needs updating
            new_hash = self.password_service.update_hash_if_needed(password, user.hashed_password)
            if new_hash:
                user.hashed_password = new_hash
                await self.db.commit()

            return user
        except Exception:
            return None

    async def create_tokens_for_user(self, user: User) -> dict[str, Any]:
        """Create access and refresh tokens for user."""
        user_data = {
            "id": user.id,
            "email": user.email,
            "tenant_id": user.tenant_id,
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

        if self.user_repo is None or getattr(self.user_repo, "tenant_id", None) != tenant_uuid:
            self.user_repo = UserRepository(self.db, tenant_uuid)

        user = await self.user_repo.get_by_id(user_uuid)
        if not user or not user.is_active:
            return None

        return await self.create_tokens_for_user(user)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession
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
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )

        return user
    except Exception:
        raise credentials_exception


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession
) -> User:
    """Dependency to get current active user."""
    user = await get_current_user(credentials, db)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user


# FastAPI dependency wrappers
async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """FastAPI dependency to get current user."""
    return await get_current_user(credentials, db)


async def get_current_active_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """FastAPI dependency to get current active user."""
    return await get_current_active_user(credentials, db)
