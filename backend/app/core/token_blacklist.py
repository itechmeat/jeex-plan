"""
Token blacklist service for handling JWT token invalidation on logout.

This service manages blacklisted tokens in Redis to provide secure logout
functionality by preventing invalidated tokens from being used after logout.
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

    def _get_blacklist_key(self, token_hash: str) -> str:
        """Generate Redis key for blacklisted token."""
        return f"blacklist:token:{token_hash}"

    def _hash_token(self, token: str) -> str:
        """Create a hash of the token for storage (for privacy)."""
        import hashlib

        return hashlib.sha256(token.encode()).hexdigest()

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
        Add token to blacklist with appropriate TTL.

        Args:
            token: JWT token to blacklist

        Returns:
            True if successfully blacklisted, False otherwise
        """
        try:
            token_hash = self._hash_token(token)
            blacklist_key = self._get_blacklist_key(token_hash)
            ttl = self._calculate_ttl(token)

            if ttl <= 0:
                logger.info(
                    "Token already expired, not blacklisting",
                    token_hash=token_hash[:16],
                )
                return True

            # Store in Redis with TTL
            success = await self.redis.set(blacklist_key, "1", ex=ttl)

            if success:
                logger.info(
                    "Token blacklisted successfully",
                    token_hash=token_hash[:16],
                    ttl=ttl,
                )
            else:
                logger.error("Failed to blacklist token", token_hash=token_hash[:16])

            return success

        except Exception as e:
            logger.error("Error blacklisting token", error=str(e))
            return False

    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted.

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
            token_hash = self._hash_token(token)
            blacklist_key = self._get_blacklist_key(token_hash)

            exists = await self.redis.exists(blacklist_key)

            if exists:
                logger.debug("Token found in blacklist", token_hash=token_hash[:16])

            return exists

        except Exception as e:
            logger.error(
                "Error checking token blacklist - FAIL-CLOSED",
                error=str(e),
                token_hash=self._hash_token(token)[:16],
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

    async def blacklist_user_tokens(self, user_id: str) -> bool:
        """
        Blacklist all tokens for a specific user (for account compromise scenarios).

        Args:
            user_id: User ID to blacklist all tokens for

        Returns:
            True if successfully added to user blacklist, False otherwise
        """
        try:
            user_blacklist_key = f"blacklist:user:{user_id}"
            # Set with a long TTL (refresh token lifetime)
            ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

            success = await self.redis.set(user_blacklist_key, "1", ex=ttl)

            if success:
                logger.info("All user tokens blacklisted", user_id=user_id)
            else:
                logger.error("Failed to blacklist user tokens", user_id=user_id)

            return success

        except Exception as e:
            logger.error(
                "Error blacklisting user tokens", user_id=user_id, error=str(e)
            )
            return False

    async def is_user_blacklisted(self, user_id: str) -> bool:
        """
        Check if all tokens for user are blacklisted.

        Args:
            user_id: User ID to check

        Returns:
            True if user is blacklisted, False otherwise

        Security:
            FAIL-CLOSED behavior: On Redis errors, return True to treat
            unknown user status as blacklisted.
        """
        try:
            user_blacklist_key = f"blacklist:user:{user_id}"
            exists = await self.redis.exists(user_blacklist_key)

            if exists:
                logger.debug("User found in blacklist", user_id=user_id)

            return exists

        except Exception as e:
            logger.error(
                "Error checking user blacklist - FAIL-CLOSED",
                user_id=user_id,
                error=str(e),
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
