"""
User repository for user management operations with tenant isolation.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

from app.models.user import User
from .base import TenantRepository


class UserRepository(TenantRepository[User]):
    """Repository for user operations with tenant isolation."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, User, tenant_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email within tenant."""
        return await self.get_by_field('email', email)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username within tenant."""
        return await self.get_by_field('username', username)

    async def get_by_oauth(self, oauth_provider: str, oauth_id: str) -> Optional[User]:
        """Get user by OAuth credentials within tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.oauth_provider == oauth_provider,
                self.model.oauth_id == oauth_id,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get all active users within tenant."""
        return await self.get_all(
            skip=skip,
            limit=limit,
            filters={'is_active': True}
        )

    async def get_superusers(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get all superusers within tenant."""
        return await self.get_all(
            skip=skip,
            limit=limit,
            filters={'is_superuser': True}
        )

    async def create_user(
        self,
        email: str,
        username: str,
        full_name: Optional[str] = None,
        is_active: bool = True,
        is_superuser: bool = False,
        oauth_provider: Optional[str] = None,
        oauth_id: Optional[str] = None
    ) -> User:
        """Create a new user within tenant."""
        return await self.create(
            email=email,
            username=username,
            full_name=full_name,
            is_active=is_active,
            is_superuser=is_superuser,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id
        )

    async def activate_user(self, user_id: UUID) -> Optional[User]:
        """Activate a user."""
        return await self.update(user_id, is_active=True)

    async def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """Deactivate a user."""
        return await self.update(user_id, is_active=False)

    async def search_users(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Search users by email, username, or full name within tenant."""
        return await self.search(
            search_fields=['email', 'username', 'full_name'],
            search_term=search_term,
            skip=skip,
            limit=limit
        )

    async def check_email_availability(
        self,
        email: str,
        exclude_user_id: Optional[UUID] = None
    ) -> bool:
        """Check if email is available within tenant."""
        stmt = select(self.model.id).where(
            and_(
                self.model.email == email,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )

        if exclude_user_id:
            stmt = stmt.where(self.model.id != exclude_user_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is None

    async def check_username_availability(
        self,
        username: str,
        exclude_user_id: Optional[UUID] = None
    ) -> bool:
        """Check if username is available within tenant."""
        stmt = select(self.model.id).where(
            and_(
                self.model.username == username,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )

        if exclude_user_id:
            stmt = stmt.where(self.model.id != exclude_user_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is None

    async def get_user_count_by_status(self) -> dict:
        """Get user count statistics by status within tenant."""
        active_count = await self.count({'is_active': True})
        inactive_count = await self.count({'is_active': False})
        superuser_count = await self.count({'is_superuser': True})
        total_count = await self.count()

        return {
            'active': active_count,
            'inactive': inactive_count,
            'superusers': superuser_count,
            'total': total_count
        }

    async def create_oauth_user(
        self,
        email: str,
        username: str,
        full_name: Optional[str],
        oauth_provider: str,
        oauth_id: str,
        is_active: bool = True
    ) -> User:
        """Create a new OAuth user within tenant."""
        return await self.create(
            email=email,
            username=username,
            full_name=full_name,
            is_active=is_active,
            is_superuser=False,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id
        )

    async def link_oauth_account(
        self,
        user_id: UUID,
        oauth_provider: str,
        oauth_id: str
    ) -> Optional[User]:
        """Link OAuth account to existing user."""
        return await self.update(
            user_id,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id
        )

    async def unlink_oauth_account(self, user_id: UUID) -> Optional[User]:
        """Unlink OAuth account from user."""
        return await self.update(
            user_id,
            oauth_provider=None,
            oauth_id=None
        )

    async def check_oauth_availability(
        self,
        oauth_provider: str,
        oauth_id: str,
        exclude_user_id: Optional[UUID] = None
    ) -> bool:
        """Check if OAuth account is available within tenant."""
        stmt = select(self.model.id).where(
            and_(
                self.model.oauth_provider == oauth_provider,
                self.model.oauth_id == oauth_id,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )

        if exclude_user_id:
            stmt = stmt.where(self.model.id != exclude_user_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is None

    async def get_users_by_oauth_provider(
        self,
        oauth_provider: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get all users with specific OAuth provider within tenant."""
        return await self.get_all(
            skip=skip,
            limit=limit,
            filters={'oauth_provider': oauth_provider}
        )

    async def find_user_for_login(self, identifier: str) -> Optional[User]:
        """Find user by email or username for login within tenant."""
        # Try email first
        user = await self.get_by_email(identifier)
        if user:
            return user

        # Try username
        return await self.get_by_username(identifier)

    async def update_last_login(self, user_id: UUID) -> Optional[User]:
        """Update user's last login timestamp."""
        from datetime import datetime
        return await self.update(user_id, updated_at=datetime.utcnow())