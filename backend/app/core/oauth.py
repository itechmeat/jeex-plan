"""
OAuth2 providers for Google and GitHub authentication.
"""

import uuid
from typing import Optional, Dict, Any
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import HTTPException, status
from sqlalchemy import func
import httpx

from ..core.config import get_settings
from ..core.logger import get_logger
from ..models.user import User
from ..models.tenant import Tenant
from ..repositories.user import UserRepository
from ..repositories.tenant import TenantRepository

settings = get_settings()
logger = get_logger(__name__)


class OAuthProvider:
    """Base OAuth provider class."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    async def get_authorization_url(self, state: str) -> str:
        """Get authorization URL for OAuth flow."""
        raise NotImplementedError

    async def get_user_info(self, code: str, state: str) -> Dict[str, Any]:
        """Get user information from OAuth provider."""
        raise NotImplementedError


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth2 provider."""

    def __init__(self):
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google OAuth credentials not configured")

        super().__init__(settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET)
        self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"

    async def get_authorization_url(self, state: str) -> str:
        """Get Google authorization URL."""
        async with AsyncOAuth2Client(
            client_id=self.client_id,
            redirect_uri=settings.OAUTH_REDIRECT_URL,
            scope="openid email profile"
        ) as client:
            authorization_url, _ = client.create_authorization_url(
                self.authorization_endpoint,
                state=state
            )

        return authorization_url

    async def get_user_info(self, code: str, state: str) -> Dict[str, Any]:
        """Get user information from Google."""
        try:
            async with AsyncOAuth2Client(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=settings.OAUTH_REDIRECT_URL
            ) as client:
                # Exchange code for token
                token = await client.fetch_token(
                    self.token_endpoint,
                    code=code
                )

            # Get user info
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    self.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {token['access_token']}"}
                )
                response.raise_for_status()
                user_info = response.json()

            return {
                "provider": "google",
                "provider_id": user_info["id"],
                "email": user_info["email"],
                "full_name": user_info.get("name", ""),
                "avatar_url": user_info.get("picture", ""),
                "verified_email": user_info.get("verified_email", False)
            }

        except Exception as e:
            logger.error(
                "Google OAuth user info retrieval failed",
                error=str(e),
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authentication with provider failed"
            ) from e


class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth2 provider."""

    def __init__(self):
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            raise ValueError("GitHub OAuth credentials not configured")

        super().__init__(settings.GITHUB_CLIENT_ID, settings.GITHUB_CLIENT_SECRET)
        self.authorization_endpoint = "https://github.com/login/oauth/authorize"
        self.token_endpoint = "https://github.com/login/oauth/access_token"
        self.userinfo_endpoint = "https://api.github.com/user"
        self.emails_endpoint = "https://api.github.com/user/emails"

    async def get_authorization_url(self, state: str) -> str:
        """Get GitHub authorization URL."""
        async with AsyncOAuth2Client(
            client_id=self.client_id,
            redirect_uri=settings.OAUTH_REDIRECT_URL,
            scope="user:email"
        ) as client:
            authorization_url, _ = client.create_authorization_url(
                self.authorization_endpoint,
                state=state
            )

        return authorization_url

    async def get_user_info(self, code: str, state: str) -> Dict[str, Any]:
        """Get user information from GitHub."""
        try:
            async with AsyncOAuth2Client(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=settings.OAUTH_REDIRECT_URL
            ) as client:
                # Exchange code for token
                token = await client.fetch_token(
                    self.token_endpoint,
                    code=code
                )

            headers = {
                "Authorization": f"Bearer {token['access_token']}",
                "Accept": "application/vnd.github.v3+json"
            }

            async with httpx.AsyncClient() as http_client:
                # Get user info
                user_response = await http_client.get(
                    self.userinfo_endpoint,
                    headers=headers
                )
                user_response.raise_for_status()
                user_info = user_response.json()

                # Get primary email
                emails_response = await http_client.get(
                    self.emails_endpoint,
                    headers=headers
                )
                emails_response.raise_for_status()
                emails = emails_response.json()

                primary_email_entry = next(
                    (email for email in emails if email.get("primary")),
                    None
                )
                primary_email = (
                    primary_email_entry["email"]
                    if primary_email_entry
                    else user_info.get("email")
                )

                if primary_email_entry is not None:
                    verified_email = bool(primary_email_entry.get("verified", False))
                elif primary_email:
                    matching_entry = next(
                        (email for email in emails if email.get("email") == primary_email),
                        None
                    )
                    if matching_entry is not None:
                        verified_email = bool(matching_entry.get("verified", False))
                    else:
                        verified_email = bool(user_info.get("verified", False))
                else:
                    verified_email = False

            return {
                "provider": "github",
                "provider_id": str(user_info["id"]),
                "email": primary_email,
                "full_name": user_info.get("name", user_info.get("login", "")),
                "avatar_url": user_info.get("avatar_url", ""),
                "verified_email": bool(verified_email)
            }

        except Exception as e:
            logger.error(
                "GitHub OAuth user info retrieval failed",
                error=str(e),
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authentication with provider failed"
            ) from e


class OAuthService:
    """Service for handling OAuth authentication."""

    def __init__(self, db):
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.providers = {
            "google": GoogleOAuthProvider() if settings.GOOGLE_CLIENT_ID else None,
            "github": GitHubOAuthProvider() if settings.GITHUB_CLIENT_ID else None,
        }

    def get_provider(self, provider_name: str) -> OAuthProvider:
        """Get OAuth provider by name."""
        provider = self.providers.get(provider_name)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth provider '{provider_name}' not configured"
            )
        return provider

    async def get_authorization_url(self, provider_name: str, state: str) -> str:
        """Get authorization URL for OAuth provider."""
        provider = self.get_provider(provider_name)
        return await provider.get_authorization_url(state)

    async def authenticate_user(
        self,
        provider_name: str,
        code: str,
        state: str,
        tenant_id: Optional[uuid.UUID] = None
    ) -> User:
        """Authenticate user with OAuth provider."""
        provider = self.get_provider(provider_name)
        user_info = await provider.get_user_info(code, state)

        # Find or create tenant if not specified
        if not tenant_id:
            tenant_id = await self._get_or_create_default_tenant()

        # Find existing user or create new one
        tenant_user_repo = UserRepository(self.db, tenant_id)

        user = await tenant_user_repo.get_by_oauth(
            user_info["provider"],
            user_info["provider_id"]
        )

        if user:
            # Update last login
            user.last_login_at = func.now()
            await self.db.commit()
            return user

        # Check if user exists with same email
        existing_user = await tenant_user_repo.get_by_email(
            user_info["email"]
        )

        if existing_user:
            # Link OAuth account to existing user
            existing_user.oauth_provider = user_info["provider"]
            existing_user.oauth_id = user_info["provider_id"]
            existing_user.last_login_at = func.now()
            await self.db.commit()
            return existing_user

        # Create new user
        username = await self._generate_unique_username(
            tenant_user_repo,
            user_info["email"]
        )

        new_user = User(
            tenant_id=tenant_id,
            email=user_info["email"],
            username=username,
            full_name=user_info["full_name"],
            oauth_provider=user_info["provider"],
            oauth_id=user_info["provider_id"],
            is_active=True,
            last_login_at=func.now()
        )

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        return new_user

    async def _get_or_create_default_tenant(self) -> uuid.UUID:
        """Get or create default tenant."""
        default_tenant = await self.tenant_repo.get_by_slug("default")

        if not default_tenant:
            default_tenant = Tenant(
                name="Default Tenant",
                slug="default",
                description="Default tenant for new users",
                is_active=True
            )
            self.db.add(default_tenant)
            await self.db.commit()
            await self.db.refresh(default_tenant)

        return default_tenant.id

    async def _generate_unique_username(
        self,
        user_repo: UserRepository,
        email: str
    ) -> str:
        """Generate unique username for tenant."""
        base_username = email.split("@")[0].lower()
        username = base_username
        counter = 1

        while await user_repo.get_by_username(username):
            username = f"{base_username}{counter}"
            counter += 1

        return username
