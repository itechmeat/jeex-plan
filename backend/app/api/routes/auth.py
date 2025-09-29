"""
Authentication endpoints with OAuth2 support and full JWT implementation.
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserResponse,
)
from ...core.auth import (
    AuthDependency,
    AuthService,
    auth_dependency,
    get_current_active_user_dependency,
)
from ...core.config import get_settings
from ...core.database import get_db
from ...core.logger import get_logger
from ...core.oauth import OAuthService
from ...models.user import User
from ...services.user import UserService

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


class OAuthInitRequest(BaseModel):
    """OAuth initialization request."""

    provider: str
    redirect_url: str | None = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str
    state: str
    provider: str


class ChangePasswordRequest(BaseModel):
    """Password change payload."""

    current_password: str
    new_password: str


@router.post("/register", response_model=LoginResponse)
async def register_user(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """
    User registration with email and password.

    Creates a new user account and returns authentication tokens.
    """
    logger.info("Registration attempt", email=user_data.email)

    # Validate password confirmation
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
        )

    user_service = UserService(db)

    try:
        # Register user and get tokens
        result = await user_service.register_user(
            email=user_data.email,
            username=user_data.name.lower().replace(" ", "_"),
            password=user_data.password,
            full_name=user_data.name,
        )

        user_response = UserResponse(
            id=result["user"]["id"],
            email=result["user"]["email"],
            name=result["user"]["full_name"] or result["user"]["username"],
            tenant_id=result["user"]["tenant_id"],
            is_active=result["user"]["is_active"],
            created_at=result["user"]["created_at"],
            last_login_at=result["user"]["last_login_at"],
        )

        token = Token(**result["tokens"])

        logger.info("Registration successful", user_id=result["user"]["id"])

        return LoginResponse(user=user_response, token=token)

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError) as e:
        logger.error("Registration validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid registration data",
        )
    except Exception as e:
        logger.error("Registration failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=LoginResponse)
async def login_user(
    login_data: LoginRequest, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """
    User login with email and password.

    Authenticates user and returns JWT tokens.
    """
    logger.info("Login attempt", email=login_data.email)

    user_service = UserService(db)

    try:
        # Authenticate user
        result = await user_service.authenticate_user(
            email=login_data.email, password=login_data.password
        )

        user_response = UserResponse(
            id=result["user"]["id"],
            email=result["user"]["email"],
            name=result["user"]["full_name"] or result["user"]["username"],
            tenant_id=result["user"]["tenant_id"],
            is_active=result["user"]["is_active"],
            created_at=result["user"]["created_at"],
            last_login_at=result["user"]["last_login_at"],
        )

        token = Token(**result["tokens"])

        logger.info("Login successful", user_id=result["user"]["id"])

        return LoginResponse(user=user_response, token=token)

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError) as e:
        logger.error("Login validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid login data",
        )
    except Exception as e:
        logger.error("Login failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    refresh_data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Refresh access token using refresh token.
    """
    logger.info("Token refresh attempt")

    user_service = UserService(db)

    try:
        tokens = await user_service.refresh_tokens(refresh_data.refresh_token)
        logger.info("Token refresh successful")
        return Token(**tokens)

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError) as e:
        logger.error("Token refresh validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token refresh data",
        )
    except Exception as e:
        logger.error("Token refresh failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout_user(
    auth: AuthDependency = Depends(auth_dependency),
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    """
    User logout endpoint.

    Invalidates the current session by blacklisting the JWT token.
    """
    if not auth.user or not auth.token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    logger.info("Logout attempt", user_id=str(auth.user.id))

    auth_service = AuthService(db)

    try:
        # Blacklist the current access token
        logout_success = await auth_service.logout_user(auth.token)

        if not logout_success:
            logger.error("Token blacklisting failed", user_id=str(auth.user.id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed",
            )

        logger.info("Logout successful", user_id=str(auth.user.id))
        return LogoutResponse(message="Successfully logged out")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Logout error", user_id=str(auth.user.id), error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user_dependency),
) -> UserResponse:
    """
    Get current authenticated user profile.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.full_name or current_user.username,
        tenant_id=str(current_user.tenant_id),
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )


# OAuth2 Endpoints
@router.post("/oauth/init")
async def oauth_init(
    request: Request,
    oauth_data: OAuthInitRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Initialize OAuth2 flow.

    Returns authorization URL for the specified provider.
    """
    logger.info("OAuth init", provider=oauth_data.provider)

    oauth_service = OAuthService(db)

    try:
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)

        # Get authorization URL
        auth_url = await oauth_service.get_authorization_url(oauth_data.provider, state)

        # Store state in Redis with short expiration for CSRF protection
        try:
            redis_client = getattr(request.app.state, "redis_client", None)
            if redis_client:
                await redis_client.setex(f"oauth_state:{state}", 300, "1")
        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "Redis connection failed during OAuth state persistence", error=str(e)
            )
        except (AttributeError, TypeError, ValueError) as e:
            logger.warning(
                "Redis configuration error during OAuth state persistence", error=str(e)
            )
        except Exception as e:
            logger.error(
                "Unexpected error during OAuth state persistence",
                error=str(e),
                exc_info=True,
            )

        return {
            "authorization_url": auth_url,
            "state": state,
            "provider": oauth_data.provider,
        }

    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError) as e:
        logger.error(
            "OAuth init validation error", provider=oauth_data.provider, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OAuth configuration for provider {oauth_data.provider}",
        )
    except Exception as e:
        logger.error(
            "OAuth init failed",
            provider=oauth_data.provider,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth initialization failed for provider {oauth_data.provider}",
        )


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    provider: str = Query(..., description="OAuth provider name"),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    OAuth2 callback endpoint.

    Handles the callback from OAuth providers and completes authentication.
    """
    logger.info("OAuth callback", provider=provider)

    oauth_service = OAuthService(db)
    auth_service = AuthService(db)

    try:
        # Validate state parameter
        redis_client = getattr(request.app.state, "redis_client", None)
        if redis_client:
            cache_key = f"oauth_state:{state}"
            exists = await redis_client.get(cache_key)
            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid OAuth state",
                )
            await redis_client.delete(cache_key)

        # Authenticate user with OAuth provider
        user = await oauth_service.authenticate_user(provider, code, state)

        # Generate JWT tokens
        tokens = await auth_service.create_tokens_for_user(user)

        frontend_url = (
            settings.ALLOWED_ORIGINS[0]
            if settings.ALLOWED_ORIGINS
            else "http://localhost:3000"
        )
        redirect_url = f"{frontend_url}/auth/callback"
        response = RedirectResponse(url=redirect_url)

        secure_cookie = settings.is_production
        access_max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        refresh_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            max_age=access_max_age,
            httponly=True,
            secure=secure_cookie,
            samesite="lax",
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            max_age=refresh_max_age,
            httponly=True,
            secure=secure_cookie,
            samesite="strict",
            path="/",
        )

        logger.info(
            "OAuth callback successful", provider=provider, user_id=str(user.id)
        )

        return response

    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError) as e:
        logger.error("OAuth callback validation error", provider=provider, error=str(e))
        frontend_url = (
            settings.ALLOWED_ORIGINS[0]
            if settings.ALLOWED_ORIGINS
            else "http://localhost:3000"
        )
        error_url = f"{frontend_url}/auth/error?error=oauth_validation_failed"
        return RedirectResponse(url=error_url)
    except Exception as e:
        logger.error(
            "OAuth callback failed", provider=provider, error=str(e), exc_info=True
        )
        # Redirect to frontend with error
        frontend_url = (
            settings.ALLOWED_ORIGINS[0]
            if settings.ALLOWED_ORIGINS
            else "http://localhost:3000"
        )
        error_url = f"{frontend_url}/auth/error?error=oauth_failed"
        return RedirectResponse(url=error_url)


@router.post("/oauth/callback", response_model=LoginResponse)
async def oauth_callback_post(
    request: Request,
    callback_data: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    OAuth2 callback endpoint (POST version for SPA applications).

    Handles the callback data and returns authentication tokens directly.
    """
    logger.info("OAuth callback POST", provider=callback_data.provider)

    oauth_service = OAuthService(db)
    auth_service = AuthService(db)

    try:
        # Validate state parameter
        redis_client = getattr(request.app.state, "redis_client", None)
        if redis_client:
            cache_key = f"oauth_state:{callback_data.state}"
            exists = await redis_client.get(cache_key)
            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid OAuth state",
                )
            await redis_client.delete(cache_key)

        # Authenticate user with OAuth provider
        user = await oauth_service.authenticate_user(
            callback_data.provider, callback_data.code, callback_data.state
        )

        # Generate JWT tokens
        tokens = await auth_service.create_tokens_for_user(user)

        user_response = UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.full_name or user.username,
            tenant_id=str(user.tenant_id),
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )

        token = Token(**tokens)

        logger.info(
            "OAuth callback POST successful",
            provider=callback_data.provider,
            user_id=str(user.id),
        )

        return LoginResponse(user=user_response, token=token)

    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError) as e:
        logger.error(
            "OAuth callback POST validation error",
            provider=callback_data.provider,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth callback data",
        )
    except Exception as e:
        logger.error(
            "OAuth callback POST failed",
            provider=callback_data.provider,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth authentication failed",
        )


@router.get("/providers")
async def get_available_providers() -> dict:
    """
    Get list of available OAuth providers.
    """
    providers = []

    if settings.GOOGLE_CLIENT_ID:
        providers.append({"name": "google", "display_name": "Google", "enabled": True})

    if settings.GITHUB_CLIENT_ID:
        providers.append({"name": "github", "display_name": "GitHub", "enabled": True})

    return {"providers": providers}


# Password management endpoints
@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
) -> dict:
    """
    Change user password.
    """
    logger.info("Password change attempt", user_id=str(current_user.id))

    user_service = UserService(db, current_user.tenant_id)

    try:
        await user_service.change_password(
            current_user.id, payload.current_password, payload.new_password
        )

        logger.info("Password change successful", user_id=str(current_user.id))
        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError) as e:
        logger.error(
            "Password change validation error",
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password change data",
        )
    except Exception as e:
        logger.error(
            "Password change failed",
            user_id=str(current_user.id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed",
        )


@router.post("/validate-token")
async def validate_token(
    current_user: User = Depends(get_current_active_user_dependency),
) -> dict:
    """
    Validate JWT token and return token information.
    """
    return {
        "valid": True,
        "user_id": str(current_user.id),
        "tenant_id": str(current_user.tenant_id),
        "email": current_user.email,
        "is_active": current_user.is_active,
    }


@router.get("/blacklist/stats")
async def get_blacklist_stats(
    current_user: User = Depends(get_current_active_user_dependency),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get token blacklist statistics (for administrators).
    """
    logger.info("Blacklist stats request", user_id=str(current_user.id))

    auth_service = AuthService(db)

    try:
        stats = await auth_service.token_blacklist.get_blacklist_stats()
        return stats

    except Exception as e:
        logger.error(
            "Failed to get blacklist stats",
            user_id=str(current_user.id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve blacklist statistics",
        )
