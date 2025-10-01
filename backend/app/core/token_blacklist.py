"""
Token blacklist service for handling JWT token invalidation on logout.

This service manages blacklisted tokens in Redis using their JWT IDs (JTI)
to provide secure logout functionality by preventing invalidated tokens
from being used after logout. Using JTI is more efficient than storing
full token hashes and provides direct token tracking.
"""

from datetime import UTC, datetime
from typing import Any

from jose import jwt  # type: ignore[import-untyped]

from ..adapters.redis import RedisAdapter
from .config import get_settings
from .logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class TokenBlacklistService:
    """Service for managing blacklisted JWT tokens in Redis."""

    def __init__(self, redis_adapter: RedisAdapter | None = None) -> None:
        self.redis = redis_adapter or RedisAdapter()
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM

    def _get_blacklist_key(self, jti: str, tenant_id: str) -> str:
        """
        Generate Redis key for blacklisted token with tenant isolation.

        SECURITY: Tenant ID is REQUIRED to prevent cross-tenant token collisions.
        Format: blacklist:tenant:{tenant_id}:token:{jti}

        Args:
            jti: JWT ID (unique token identifier)
            tenant_id: Tenant UUID for isolation

        Returns:
            Tenant-scoped Redis key
        """
        if not tenant_id:
            raise ValueError("tenant_id is required for token blacklist key generation")
        return f"blacklist:tenant:{tenant_id}:token:{jti}"

    def _extract_jti(self, token: str) -> str | None:
        """Extract JTI from JWT token."""
        try:
            # Decode without verification to get JTI
            unverified_payload = jwt.get_unverified_claims(token)
            jti = unverified_payload.get("jti")

            if jti and isinstance(jti, str):
                return jti  # type: ignore[no-any-return]
            return None
        except Exception as e:
            logger.warning("Failed to extract JTI from token", error=str(e))
            return None

    def _extract_tenant_id(self, token: str) -> str | None:
        """
        Extract tenant_id from JWT token.

        SECURITY: Tenant ID is required for multi-tenant token isolation.

        Args:
            token: JWT token string

        Returns:
            Tenant ID string or None if not found
        """
        try:
            unverified_payload = jwt.get_unverified_claims(token)
            tenant_id = unverified_payload.get("tenant_id")

            if tenant_id and isinstance(tenant_id, str):
                return tenant_id  # type: ignore[no-any-return]
            return None
        except Exception as e:
            logger.warning("Failed to extract tenant_id from token", error=str(e))
            return None

    def _get_token_expiry(self, token: str) -> int | None:
        """Extract expiry timestamp from JWT token."""
        try:
            # Decode without verification to get expiry
            unverified_payload = jwt.get_unverified_claims(token)
            exp = unverified_payload.get("exp")

            if exp and isinstance(exp, (int, float)):
                return int(exp)
            return None
        except Exception as e:
            logger.warning("Failed to extract token expiry", error=str(e))
            return None

    def _calculate_ttl(self, token: str) -> int:
        """Calculate TTL for blacklist entry based on token expiry."""
        exp_timestamp = self._get_token_expiry(token)
        if not exp_timestamp:
            # Default TTL if we can't get expiry (use max token lifetime)
            return settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        current_timestamp = int(datetime.now(UTC).timestamp())
        ttl = exp_timestamp - current_timestamp

        # Ensure TTL is positive
        return max(ttl, 0)

    async def blacklist_token(self, token: str) -> bool:
        """
        Add token to blacklist with tenant isolation and appropriate TTL.

        SECURITY: Tenant ID is REQUIRED and extracted from token for isolation.

        Args:
            token: JWT token to blacklist

        Returns:
            True if successfully blacklisted, False otherwise
        """
        try:
            jti = self._extract_jti(token)
            if not jti:
                logger.error("Failed to extract JTI from token for blacklisting")
                return False

            # SECURITY: Extract tenant_id for isolation
            tenant_id = self._extract_tenant_id(token)
            if not tenant_id:
                logger.error(
                    "Failed to extract tenant_id from token for blacklisting",
                    jti=jti[:16],
                )
                raise ValueError(
                    "tenant_id is required in token for blacklist operation"
                )

            blacklist_key = self._get_blacklist_key(jti, tenant_id)
            ttl = self._calculate_ttl(token)

            if ttl <= 0:
                logger.info(
                    "Token already expired, not blacklisting",
                    jti=jti[:16],
                    tenant_id=tenant_id,
                )
                return True

            # Store in Redis with TTL and tenant isolation
            success = await self.redis.set(blacklist_key, "1", ex=ttl)

            if success:
                logger.info(
                    "Token blacklisted successfully",
                    jti=jti[:16],
                    tenant_id=tenant_id,
                    ttl=ttl,
                )
            else:
                logger.error(
                    "Failed to blacklist token", jti=jti[:16], tenant_id=tenant_id
                )

            return success

        except ValueError:
            raise  # Re-raise tenant_id validation errors
        except Exception as e:
            logger.error("Error blacklisting token", error=str(e), exc_info=True)
            raise  # Preserve original exception

    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted with tenant isolation.

        SECURITY: Tenant ID is REQUIRED and extracted from token for isolation.

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted, False otherwise

        Security:
            FAIL-CLOSED behavior: On Redis errors, return True to treat
            unknown tokens as blacklisted. Additionally checks JWT expiry
            before returning True.
        """
        try:
            jti = self._extract_jti(token)
            if not jti:
                # If we can't extract JTI, we can't check blacklist properly
                # Treat as blacklisted for safety
                logger.warning("Cannot extract JTI from token, treating as blacklisted")
                return True

            # SECURITY: Extract tenant_id for isolation
            tenant_id = self._extract_tenant_id(token)
            if not tenant_id:
                logger.warning(
                    "Cannot extract tenant_id from token, treating as blacklisted",
                    jti=jti[:16],
                )
                return True

            blacklist_key = self._get_blacklist_key(jti, tenant_id)
            exists = await self.redis.exists(blacklist_key)

            if exists:
                logger.debug(
                    "Token found in blacklist", jti=jti[:16], tenant_id=tenant_id
                )

            return exists

        except ValueError as e:
            logger.error(
                "Tenant validation error - FAIL-CLOSED",
                error=str(e),
            )
            return True
        except Exception as e:
            logger.error(
                "Error checking token blacklist - FAIL-CLOSED",
                error=str(e),
                exc_info=True,
            )
            # SECURITY: FAIL-CLOSED behavior - treat as blacklisted on error
            # Check if token is expired before rejecting
            exp_timestamp = self._get_token_expiry(token)
            if exp_timestamp:
                current_timestamp = int(datetime.now(UTC).timestamp())
                if current_timestamp < exp_timestamp:
                    # Token not expired, but Redis error - treat as blacklisted (fail-closed)
                    return True
            # Token expired or no expiry - treat as blacklisted
            return True

    async def blacklist_user_tokens(self, user_id: str, tenant_id: str) -> bool:
        """
        Blacklist all tokens for a specific user with tenant isolation.

        SECURITY: Tenant ID is REQUIRED to prevent cross-tenant user blacklisting.

        Args:
            user_id: User ID to blacklist all tokens for
            tenant_id: Tenant UUID for isolation

        Returns:
            True if successfully added to user blacklist, False otherwise
        """
        if not tenant_id:
            logger.error(
                "tenant_id is required for user token blacklisting", user_id=user_id
            )
            raise ValueError("tenant_id is required for user blacklist operation")

        try:
            user_blacklist_key = f"blacklist:tenant:{tenant_id}:user:{user_id}"
            # Set with a long TTL (refresh token lifetime)
            ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

            success = await self.redis.set(user_blacklist_key, "1", ex=ttl)

            if success:
                logger.info(
                    "All user tokens blacklisted",
                    user_id=user_id,
                    tenant_id=tenant_id,
                )
            else:
                logger.error(
                    "Failed to blacklist user tokens",
                    user_id=user_id,
                    tenant_id=tenant_id,
                )

            return success

        except ValueError:
            raise  # Re-raise tenant_id validation errors
        except Exception as e:
            logger.error(
                "Error blacklisting user tokens",
                user_id=user_id,
                tenant_id=tenant_id,
                error=str(e),
                exc_info=True,
            )
            raise  # Preserve original exception

    async def is_user_blacklisted(self, user_id: str, tenant_id: str) -> bool:
        """
        Check if all tokens for user are blacklisted with tenant isolation.

        SECURITY: Tenant ID is REQUIRED to prevent cross-tenant user checks.

        Args:
            user_id: User ID to check
            tenant_id: Tenant UUID for isolation

        Returns:
            True if user is blacklisted, False otherwise

        Security:
            FAIL-CLOSED behavior: On Redis errors, return True to treat
            unknown user status as blacklisted.
        """
        if not tenant_id:
            logger.error(
                "tenant_id is required for user blacklist check", user_id=user_id
            )
            return True  # FAIL-CLOSED on missing tenant_id

        try:
            user_blacklist_key = f"blacklist:tenant:{tenant_id}:user:{user_id}"
            exists = await self.redis.exists(user_blacklist_key)

            if exists:
                logger.debug(
                    "User found in blacklist", user_id=user_id, tenant_id=tenant_id
                )

            return exists

        except Exception as e:
            logger.error(
                "Error checking user blacklist - FAIL-CLOSED",
                user_id=user_id,
                tenant_id=tenant_id,
                error=str(e),
                exc_info=True,
            )
            # SECURITY: FAIL-CLOSED behavior - treat as blacklisted on error
            return True

    async def get_blacklist_stats(self) -> dict[str, Any]:
        """
        Get statistics about blacklisted tokens.

        Warning: This operation scans Redis keys and may be expensive on large datasets.
        Results are limited to prevent blocking Redis. Consider caching results if called
        frequently.

        Returns:
            Dictionary with blacklist statistics including:
            - blacklisted_tokens: Count of blacklisted tokens (max 10,000)
            - blacklisted_users: Count of users with blacklisted tokens (max 10,000)
            - tokens_limited: True if token count reached limit
            - users_limited: True if user count reached limit
            - redis_status: Connection status
        """
        try:
            # Count blacklisted tokens
            token_pattern = "blacklist:token:*"
            user_pattern = "blacklist:user:*"

            token_keys = []
            user_keys = []

            # Limit scan to prevent blocking Redis
            max_keys = 10000

            async for key in self.redis.client.scan_iter(match=token_pattern):
                token_keys.append(str(key))
                if len(token_keys) >= max_keys:
                    break

            async for key in self.redis.client.scan_iter(match=user_pattern):
                user_keys.append(str(key))
                if len(user_keys) >= max_keys:
                    break

            return {
                "blacklisted_tokens": len(token_keys),
                "blacklisted_users": len(user_keys),
                "tokens_limited": len(token_keys) >= max_keys,
                "users_limited": len(user_keys) >= max_keys,
                "redis_status": "connected",
            }

        except Exception as e:
            logger.error("Error getting blacklist stats", error=str(e))
            return {
                "blacklisted_tokens": 0,
                "blacklisted_users": 0,
                "tokens_limited": False,
                "users_limited": False,
                "redis_status": "error",
                "error": str(e),
            }
