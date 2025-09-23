"""
User management service with authentication and profile operations.
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from ..core.auth import AuthService
from ..models.user import User
from ..repositories.user import UserRepository
from ..repositories.tenant import TenantRepository


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession, tenant_id: Optional[uuid.UUID] = None):
        self.db = db
        self.tenant_id = tenant_id
        # Repositories that require tenant_id
        if tenant_id:
            self.user_repo = UserRepository(db, tenant_id)
        else:
            self.user_repo = None
        # Global repositories (no tenant scope)
        self.tenant_repo = TenantRepository(db)
        self.auth_service = AuthService(db, tenant_id)

    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        tenant_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Register a new user with password authentication."""

        # Compute effective tenant_id first
        if tenant_id:
            effective_tenant_id = tenant_id
        else:
            effective_tenant_id = await self._get_or_create_default_tenant()

        # Initialize repositories and auth service with effective tenant
        self.tenant_id = effective_tenant_id
        self.user_repo = UserRepository(self.db, self.tenant_id)
        self.auth_service = AuthService(self.db, self.tenant_id)

        # Validate email availability (against correct tenant)
        if not await self.user_repo.check_email_availability(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Validate username availability (against correct tenant)
        if not await self.user_repo.check_username_availability(username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        # Hash password
        hashed_password = self.auth_service.get_password_hash(password)

        # Create user
        user = await self.user_repo.create(
            email=email,
            username=username,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            last_login_at=datetime.utcnow()
        )

        # Generate tokens
        tokens = await self.auth_service.create_tokens_for_user(user)

        return {
            "user": self._serialize_user(user),
            "tokens": tokens
        }

    async def authenticate_user(
        self,
        email: str,
        password: str,
        tenant_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Authenticate user with email and password."""

        user = await self.auth_service.authenticate_user(email, password, tenant_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )

        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.commit()

        # Generate tokens
        tokens = await self.auth_service.create_tokens_for_user(user)

        return {
            "user": self._serialize_user(user),
            "tokens": tokens
        }

    async def refresh_tokens(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token."""
        tokens = await self.auth_service.refresh_access_token(refresh_token)

        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        return tokens

    async def get_user_profile(self, user_id: uuid.UUID) -> User:
        """Get user profile by ID."""
        if self.user_repo is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User repository not initialized"
            )

        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user

    async def update_user_profile(
        self,
        user_id: uuid.UUID,
        **updates
    ) -> User:
        """Update user profile."""
        if self.user_repo is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User repository not initialized"
            )

        # Remove sensitive fields that shouldn't be updated directly
        sensitive_fields = {
            'hashed_password', 'tenant_id', 'oauth_provider',
            'oauth_id', 'is_superuser', 'created_at', 'updated_at'
        }

        filtered_updates = {
            k: v for k, v in updates.items()
            if k not in sensitive_fields and v is not None
        }

        # Validate email uniqueness if being updated
        if 'email' in filtered_updates:
            email_available = await self.user_repo.check_email_availability(
                filtered_updates['email'],
                exclude_user_id=user_id
            )
            if not email_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )

        # Validate username uniqueness if being updated
        if 'username' in filtered_updates:
            username_available = await self.user_repo.check_username_availability(
                filtered_updates['username'],
                exclude_user_id=user_id
            )
            if not username_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )

        user = await self.user_repo.update(user_id, **filtered_updates)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user password."""
        if self.user_repo is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User repository not initialized"
            )

        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify current password
        if not user.hashed_password or not self.auth_service.verify_password(
            current_password,
            user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Hash new password
        new_hashed_password = self.auth_service.get_password_hash(new_password)

        # Update password
        await self.user_repo.update(user_id, hashed_password=new_hashed_password)

        return True

    async def deactivate_user(self, user_id: uuid.UUID) -> User:
        """Deactivate user account."""
        user = await self.user_repo.deactivate_user(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user

    async def activate_user(self, user_id: uuid.UUID) -> User:
        """Activate user account."""
        user = await self.user_repo.activate_user(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user

    async def get_users_list(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        active_only: bool = True
    ) -> List[User]:
        """Get list of users with optional search."""
        if self.user_repo is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User repository not initialized"
            )

        if search:
            return await self.user_repo.search_users(search, skip, limit)

        if active_only:
            return await self.user_repo.get_active_users(skip, limit)

        return await self.user_repo.get_all(skip, limit)

    async def get_user_statistics(self) -> Dict[str, int]:
        """Get user statistics."""
        return await self.user_repo.get_user_count_by_status()

    async def link_oauth_account(
        self,
        user_id: uuid.UUID,
        oauth_provider: str,
        oauth_id: str
    ) -> User:
        """Link OAuth account to existing user."""

        repo = self.user_repo

        if repo is None:
            raise RuntimeError(
                "UserService.link_oauth_account requires an initialized user_repo"
            )

        # Check if OAuth account is already linked
        oauth_available = await repo.check_oauth_availability(
            oauth_provider,
            oauth_id,
            exclude_user_id=user_id
        )

        if not oauth_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth account already linked to another user"
            )

        user = await repo.link_oauth_account(
            user_id,
            oauth_provider,
            oauth_id
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user

    async def unlink_oauth_account(self, user_id: uuid.UUID) -> User:
        """Unlink OAuth account from user."""
        user = await self.user_repo.unlink_oauth_account(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user

    def _serialize_user(self, user: User) -> Dict[str, Any]:
        """Serialize user data safely, excluding sensitive fields."""
        return {
            "id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }

    async def _get_or_create_default_tenant(self) -> uuid.UUID:
        """Get or create default tenant."""
        default_tenant = await self.tenant_repo.get_by_slug("default")

        if not default_tenant:
            default_tenant = await self.tenant_repo.create_default()

        return default_tenant.id
