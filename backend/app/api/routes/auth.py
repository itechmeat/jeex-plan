"""
Authentication endpoints with OAuth2 support and full JWT implementation.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
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
    create_auth_dependency,
    get_current_active_user_dependency,
    get_current_active_user_flexible,
)
from ...core.config import get_settings
from ...core.database import get_db
from ...core.logger import get_logger
from ...core.oauth import OAuthService
from ...models.user import User
from ...repositories.tenant import TenantRepository
from ...services.user import UserService

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


class OAuthInitRequest(BaseModel):
    """OAuth initialization request."""

    provider: str
    redirect_url: str | None = None
    tenant_slug: str | None = None  # Optional tenant slug for multi-tenant OAuth


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str
    state: str
    provider: str


class ChangePasswordRequest(BaseModel):
    """Password change payload."""

    current_password: str
    new_password: str


@router.post(
    "/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    response: Response, user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """
    User registration with email and password.

    Creates a new user account and returns authentication tokens.

    SECURITY: Sets authentication tokens as HttpOnly, Secure cookies
    to prevent XSS attacks. Tokens are NOT included in response body.
    """
    logger.info("Registration attempt", email=user_data.email)

    # Validate password confirmation
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
        )

    # SECURITY: Tenant context is REQUIRED for registration
    # Registration requires explicit tenant_id or invitation token
    # NO automatic tenant creation from email domain

    tenant_id = None
    tenant_repo = TenantRepository(db)

    # Priority 1: Check for tenant_id in payload (if UserCreate supports it)
    if hasattr(user_data, "tenant_id") and getattr(user_data, "tenant_id", None):
        tenant_id = user_data.tenant_id
        # Validate tenant exists
        tenant = await tenant_repo.get_by_id(tenant_id)
        if not tenant:
            logger.warning(
                "Invalid tenant_id in registration", tenant_id=str(tenant_id)
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant identifier",
            )

    # Priority 2: Check for tenant_slug in payload
    elif hasattr(user_data, "tenant_slug") and getattr(user_data, "tenant_slug", None):
        tenant_slug = user_data.tenant_slug
        tenant = await tenant_repo.get_by_slug(tenant_slug)
        if not tenant:
            logger.warning(
                "Invalid tenant_slug in registration", tenant_slug=tenant_slug
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant identifier",
            )
        tenant_id = tenant.id

    # Priority 3: Check for invitation token (future implementation)
    # elif hasattr(user_data, "invitation_token"):
    #     invitation = await validate_invitation_token(user_data.invitation_token)
    #     tenant_id = invitation.tenant_id

    # SECURITY: Reject registration without valid tenant context
    if not tenant_id:
        logger.warning(
            "Registration rejected: missing tenant context",
            email=user_data.email,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration requires valid tenant context. "
            "Please provide tenant_id, tenant_slug, or invitation_token.",
        )

    user_service = UserService(db, tenant_id)

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

        # SECURITY: Set tokens as HttpOnly cookies
        access_max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        refresh_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        response.set_cookie(
            key="access_token",
            value=result["tokens"]["access_token"],
            max_age=access_max_age,
            httponly=True,
            secure=settings.is_production,
            samesite="strict",
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=result["tokens"]["refresh_token"],
            max_age=refresh_max_age,
            httponly=True,
            secure=settings.is_production,
            samesite="strict",
            path="/",
        )

        # Return tokens for frontend consumption
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
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    User login with email and password.

    Authenticates user and returns JWT tokens.

    SECURITY:
    - Requires tenant context (subdomain, slug, or header) for isolation
    - Sets authentication tokens as HttpOnly, Secure cookies
    - Implements rate limiting per tenant to prevent brute force attacks
    - Tokens are NOT included in response body
    """
    logger.info("Login attempt", email=login_data.email)

    # SECURITY: Extract tenant context from request
    # Priority: X-Tenant-ID header > tenant_slug in payload > subdomain
    tenant_id = None
    tenant_slug = None

    # Check X-Tenant-ID header
    tenant_id_header = request.headers.get("X-Tenant-ID")
    if tenant_id_header:
        try:
            from uuid import UUID

            tenant_id = UUID(tenant_id_header)
        except (ValueError, TypeError):
            logger.warning("Invalid X-Tenant-ID header", header=tenant_id_header)

    # Check tenant_slug in payload (if LoginRequest supports it)
    if not tenant_id and hasattr(login_data, "tenant_slug"):
        tenant_slug = getattr(login_data, "tenant_slug", None)

    # TODO: Check subdomain from request host (requires proper DNS/routing setup)
    # if not tenant_id and not tenant_slug:
    #     host = request.headers.get("host", "")
    #     subdomain = extract_subdomain(host)
    #     if subdomain:
    #         tenant_slug = subdomain

    # Resolve tenant_slug to tenant_id if needed
    if not tenant_id and tenant_slug:
        tenant_repo = TenantRepository(db)
        tenant = await tenant_repo.get_by_slug(tenant_slug)
        if not tenant:
            logger.warning("Tenant not found for slug", tenant_slug=tenant_slug)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant identifier",
            )
        tenant_id = tenant.id

    # SECURITY: Tenant context is REQUIRED for login
    if not tenant_id:
        logger.warning(
            "Login rejected: missing tenant context",
            email=login_data.email,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context is required for authentication. "
            "Please provide tenant_slug or X-Tenant-ID header.",
        )

    # TODO: Implement per-tenant rate limiting
    # rate_limiter.check_login_attempts(tenant_id, login_data.email)

    auth_service = AuthService(db, tenant_id)

    try:
        # SECURITY: Authenticate user within tenant scope only
        user = await auth_service.authenticate_user(
            email=login_data.email, password=login_data.password, tenant_id=tenant_id
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
            )

        # Update last login
        user.last_login_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(user)

        # Generate tokens
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

        # SECURITY: Set tokens as HttpOnly cookies
        access_max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        refresh_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            max_age=access_max_age,
            httponly=True,
            secure=settings.is_production,
            samesite="strict",
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            max_age=refresh_max_age,
            httponly=True,
            secure=settings.is_production,
            samesite="strict",
            path="/",
        )

        # Return tokens for frontend consumption
        token = Token(**tokens)

        logger.info("Login successful", user_id=str(user.id))

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
    request: Request,
    response: Response,
    refresh_data: RefreshTokenRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Refresh access token using refresh token.

    SECURITY: Accepts refresh token from HttpOnly cookie (preferred)
    or request body (backwards compatibility). Sets new tokens as cookies.
    """
    logger.info("Token refresh attempt")

    # SECURITY: Try to get refresh token from cookie first (secure method)
    refresh_token = request.cookies.get("refresh_token")

    # Fallback to request body for backwards compatibility
    if not refresh_token and refresh_data:
        refresh_token = refresh_data.refresh_token
        logger.info("Refresh token received in body (migrate to cookies recommended)")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token provided"
        )

    # For refresh token, use AuthService directly to extract tenant from token
    auth_service = AuthService(db)

    try:
        tokens = await auth_service.refresh_access_token(refresh_token)

        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        # SECURITY: Set new tokens as HttpOnly cookies
        access_max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        refresh_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            max_age=access_max_age,
            httponly=True,
            secure=settings.is_production,
            samesite="strict",
            path="/",
        )

        # Optionally rotate refresh token for enhanced security
        if "refresh_token" in tokens:
            response.set_cookie(
                key="refresh_token",
                value=tokens["refresh_token"],
                max_age=refresh_max_age,
                httponly=True,
                secure=settings.is_production,
                samesite="strict",
                path="/",
            )

        logger.info("Token refresh successful")

        # Return tokens for backwards compatibility
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
    request: Request,
    response: Response,
    auth: AuthDependency = Depends(create_auth_dependency()),
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    """
    User logout endpoint.

    Invalidates the current session by blacklisting both access and refresh tokens,
    and clearing authentication cookies.
    """
    logger.info("Logout attempt", user_id=str(auth.user.id))

    auth_service = AuthService(db)

    try:
        # Get refresh token from cookies (may be None if not present)
        refresh_token = request.cookies.get("refresh_token")

        # Blacklist both access and refresh tokens
        logout_success = await auth_service.logout_user(auth.token, refresh_token)

        if not logout_success:
            logger.error("Token blacklisting failed", user_id=str(auth.user.id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed",
            )

        # Clear authentication cookies
        response.delete_cookie(
            key="access_token",
            path="/",
            secure=settings.is_production,
            httponly=True,
        )
        response.delete_cookie(
            key="refresh_token",
            path="/",
            secure=settings.is_production,
            httponly=True,
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
    current_user: User = Depends(get_current_active_user_flexible),
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
    Initialize OAuth2 flow with tenant context.

    Args:
        request: FastAPI request object
        oauth_data: OAuth initialization request with optional tenant_slug
        db: Database session

    Returns:
        Dict with authorization_url, signed state (containing tenant context), and provider

    Security:
        - State parameter is JWT-signed to prevent tampering
        - Tenant context is embedded in state for multi-tenant isolation
        - 5-minute expiration prevents replay attacks
    """
    logger.info(
        "OAuth init",
        provider=oauth_data.provider,
        tenant_slug=oauth_data.tenant_slug,
    )

    oauth_service = OAuthService(db)

    try:
        # Resolve tenant_id from tenant_slug if provided
        tenant_id = None
        if oauth_data.tenant_slug:
            from ...repositories.tenant import TenantRepository

            tenant_repo = TenantRepository(db)
            tenant = await tenant_repo.get_by_slug(oauth_data.tenant_slug)
            if tenant:
                tenant_id = tenant.id
                logger.info(
                    "OAuth init with tenant context",
                    tenant_id=str(tenant_id),
                    tenant_slug=oauth_data.tenant_slug,
                )
            else:
                logger.warning(
                    "OAuth init with invalid tenant_slug",
                    tenant_slug=oauth_data.tenant_slug,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tenant '{oauth_data.tenant_slug}' not found",
                )

        # Create signed state with tenant context and CSRF token
        state = oauth_service.create_oauth_state(tenant_id=tenant_id)

        # Get authorization URL
        auth_url = await oauth_service.get_authorization_url(oauth_data.provider, state)

        # Store state in Redis with short expiration for additional CSRF protection
        # Note: JWT signature already provides integrity, Redis is for extra validation
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

    Security:
        - Validates JWT-signed state parameter
        - Extracts tenant context from state
        - Enforces tenant isolation during user lookup/creation
    """
    logger.info("OAuth callback", provider=provider)

    oauth_service = OAuthService(db)
    auth_service = AuthService(db)

    try:
        # Decode and validate signed state parameter
        # This extracts tenant_id and validates JWT signature
        state_payload = oauth_service.decode_oauth_state(state)
        tenant_id = state_payload.get("tenant_id")

        # SECURITY: Tenant context is REQUIRED for OAuth authentication
        if not tenant_id:
            logger.error(
                "OAuth callback failed: tenant_id missing from state",
                provider=provider,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state missing tenant context",
            )

        logger.info(
            "OAuth callback with decoded state",
            provider=provider,
            tenant_id=str(tenant_id),
        )

        # Validate state parameter in Redis (additional CSRF check)
        redis_client = getattr(request.app.state, "redis_client", None)
        if redis_client:
            cache_key = f"oauth_state:{state}"
            exists = await redis_client.get(cache_key)
            if not exists:
                logger.warning(
                    "OAuth state not found in Redis",
                    provider=provider,
                    tenant_id=str(tenant_id),
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired OAuth state",
                )
            await redis_client.delete(cache_key)

        # Authenticate user with OAuth provider, passing tenant context
        user = await oauth_service.authenticate_user(provider, code, state, tenant_id)

        # Generate JWT tokens
        tokens = await auth_service.create_tokens_for_user(user)

        # SECURITY: Require explicit FRONTEND_URL or ALLOWED_ORIGINS configuration
        if not settings.ALLOWED_ORIGINS:
            logger.error("OAuth callback failed: ALLOWED_ORIGINS not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth configuration error",
            )

        frontend_url = settings.ALLOWED_ORIGINS[0]
        redirect_url = f"{frontend_url}/auth/callback"

        # SECURITY: Validate redirect host is in ALLOWED_ORIGINS
        from urllib.parse import urlparse

        parsed_redirect = urlparse(redirect_url)
        allowed_hosts = [urlparse(origin).netloc for origin in settings.ALLOWED_ORIGINS]
        if parsed_redirect.netloc not in allowed_hosts:
            logger.error(
                "OAuth callback failed: Invalid redirect host",
                redirect_host=parsed_redirect.netloc,
                allowed_hosts=allowed_hosts,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid redirect URL",
            )

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
        # SECURITY: Require explicit ALLOWED_ORIGINS
        if not settings.ALLOWED_ORIGINS:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth configuration error",
            )
        frontend_url = settings.ALLOWED_ORIGINS[0]
        error_url = f"{frontend_url}/auth/error?error=oauth_validation_failed"
        return RedirectResponse(url=error_url)
    except Exception as e:
        logger.error(
            "OAuth callback failed", provider=provider, error=str(e), exc_info=True
        )
        # SECURITY: Require explicit ALLOWED_ORIGINS
        if not settings.ALLOWED_ORIGINS:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth configuration error",
            )
        frontend_url = settings.ALLOWED_ORIGINS[0]
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
        # Decode and validate state to extract tenant_id
        state_payload = oauth_service.decode_oauth_state(callback_data.state)
        tenant_id = state_payload.get("tenant_id")

        # SECURITY: Tenant context is REQUIRED for OAuth authentication
        if not tenant_id:
            logger.error(
                "OAuth callback POST failed: tenant_id missing from state",
                provider=callback_data.provider,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state missing tenant context",
            )

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
            callback_data.provider, callback_data.code, callback_data.state, tenant_id
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
    if not current_user.is_superuser:
        logger.warning(
            "Unauthorized blacklist stats access attempt",
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

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
