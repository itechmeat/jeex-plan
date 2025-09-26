"""
Redis adapter for caching, rate limiting, and queue management.
"""

import json
from typing import Any, TypeAlias

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logger import LoggerMixin, get_logger

logger = get_logger(__name__)


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | dict[str, "JSONValue"] | list["JSONValue"]


class RedisAdapter(LoggerMixin):
    """Redis adapter with async support for caching and queuing"""

    def __init__(self) -> None:
        super().__init__()
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Redis client connection"""
        try:
            redis_settings = settings.get_redis_settings()
            self.client = redis.Redis(
                host=redis_settings["host"],
                port=redis_settings["port"],
                password=redis_settings.get("password"),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            logger.info("Redis client initialized", host=redis_settings["host"])
        except (RedisError, OSError) as exc:
            logger.error("Failed to initialize Redis client", error=str(exc))
            raise

    async def health_check(self) -> dict[str, Any]:
        """Check Redis service health"""
        try:
            # Test basic connectivity
            pong = await self.client.ping()
            if pong:
                # Get additional info
                info = await self.client.info("server")
                return {
                    "status": "healthy",
                    "message": "Redis connection successful",
                    "details": {
                        "redis_version": info.get("redis_version", "unknown"),
                        "connected_clients": info.get("connected_clients", 0),
                        "used_memory": info.get("used_memory_human", "N/A"),
                        "uptime": info.get("uptime_in_seconds", 0),
                    },
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Redis ping failed",
                    "details": {},
                }

        except (RedisError, OSError) as exc:
            logger.error("Redis health check failed", error=str(exc))
            return {
                "status": "unhealthy",
                "message": f"Redis connection failed: {exc!s}",
                "details": {"error": str(exc)},
            }

    async def get(self, key: str) -> str | None:
        """Get value from Redis"""
        try:
            return await self.client.get(key)
        except RedisError as e:
            logger.error("Redis GET failed", key=key, error=str(e))
            return None

    async def set(
        self, key: str, value: str, ex: int | None = None, px: int | None = None
    ) -> bool:
        """Set value in Redis with optional expiration"""
        try:
            return await self.client.set(key, value, ex=ex, px=px)
        except RedisError as e:
            logger.error("Redis SET failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            result = await self.client.delete(key)
            return result > 0
        except RedisError as e:
            logger.error("Redis DELETE failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            return await self.client.exists(key) > 0
        except RedisError as e:
            logger.error("Redis EXISTS failed", key=key, error=str(e))
            return False

    async def ttl(self, key: str) -> int:
        """Get time-to-live for key"""
        try:
            return await self.client.ttl(key)
        except RedisError as e:
            logger.error("Redis TTL failed", key=key, error=str(e))
            return -1

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key"""
        try:
            return await self.client.expire(key, seconds)
        except RedisError as e:
            logger.error("Redis EXPIRE failed", key=key, error=str(e))
            return False

    async def incr(self, key: str) -> int | None:
        """Increment value"""
        try:
            return await self.client.incr(key)
        except RedisError as e:
            logger.error("Redis INCR failed", key=key, error=str(e))
            return None

    async def decr(self, key: str) -> int | None:
        """Decrement value"""
        try:
            return await self.client.decr(key)
        except RedisError as e:
            logger.error("Redis DECR failed", key=key, error=str(e))
            return None

    # Set operations
    async def smembers(self, key: str) -> list[str]:
        """Get all members of a set"""
        try:
            result = await self.client.smembers(key)
            return result if result is not None else []
        except RedisError as e:
            logger.error("Redis SMEMBERS failed", key=key, error=str(e))
            return []

    async def sadd(self, key: str, *values: str) -> int:
        """Add one or more members to a set"""
        try:
            return await self.client.sadd(key, *values)
        except RedisError as e:
            logger.error("Redis SADD failed", key=key, values=values, error=str(e))
            return 0

    async def srem(self, key: str, *values: str) -> int:
        """Remove one or more members from a set"""
        try:
            return await self.client.srem(key, *values)
        except RedisError as e:
            logger.error("Redis SREM failed", key=key, values=values, error=str(e))
            return 0

    # JSON operations
    async def get_json(self, key: str) -> JSONValue | None:
        """Get JSON value from Redis"""
        try:
            value = await self.client.get(key)
            return json.loads(value) if value else None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error("Redis GET JSON failed", key=key, error=str(e))
            return None

    async def set_json(self, key: str, value: JSONValue, ex: int | None = None) -> bool:
        """Set JSON value in Redis"""
        try:
            json_value = json.dumps(value)
            return await self.client.set(key, json_value, ex=ex)
        except (RedisError, TypeError) as e:
            logger.error("Redis SET JSON failed", key=key, error=str(e))
            return False

    # Rate limiting operations
    async def check_rate_limit(
        self, key: str, limit: int, window: int
    ) -> dict[str, Any]:
        """
        Check and update rate limit using sliding window algorithm.

        Args:
            key: Rate limit key (e.g., user_id or IP)
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Dict with rate limit information
        """
        try:
            current_time = int(self._get_current_timestamp())
            window_start = current_time - window

            # Remove old entries
            await self.client.zremrangebyscore(key, 0, window_start)

            # Get current count
            current_count = await self.client.zcard(key)

            # Check if limit exceeded
            if current_count >= limit:
                # Get oldest request time
                oldest = await self.client.zrange(key, 0, 0, withscores=True)
                reset_time = int(oldest[0][1]) + window if oldest else current_time

                return {
                    "allowed": False,
                    "current": current_count,
                    "limit": limit,
                    "reset_time": reset_time,
                    "remaining": 0,
                }

            # Add current request
            await self.client.zadd(key, {str(current_time): current_time})
            await self.client.expire(key, window)

            return {
                "allowed": True,
                "current": current_count + 1,
                "limit": limit,
                "reset_time": current_time + window,
                "remaining": limit - (current_count + 1),
            }

        except RedisError as e:
            logger.error("Rate limit check failed", key=key, error=str(e))
            # Allow request if Redis fails (fail open)
            return {
                "allowed": True,
                "current": 0,
                "limit": limit,
                "reset_time": 0,
                "remaining": limit,
                "error": "Rate limiting service unavailable",
            }

    # Queue operations
    async def enqueue(self, queue_name: str, value: JSONValue) -> bool:
        """Add item to queue"""
        try:
            serialized_value = (
                json.dumps(value) if not isinstance(value, str) else value
            )
            return await self.client.lpush(queue_name, serialized_value)
        except RedisError as e:
            logger.error("Queue ENQUEUE failed", queue=queue_name, error=str(e))
            return False

    async def dequeue(self, queue_name: str, timeout: int = 30) -> JSONValue | None:
        """Get item from queue with timeout"""
        try:
            result = await self.client.brpop(queue_name, timeout=timeout)
            if result:
                _, value = result
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except RedisError as e:
            logger.error("Queue DEQUEUE failed", queue=queue_name, error=str(e))
            return None

    async def queue_length(self, queue_name: str) -> int:
        """Get queue length"""
        try:
            return await self.client.llen(queue_name)
        except RedisError as e:
            logger.error("Queue LENGTH failed", queue=queue_name, error=str(e))
            return 0

    # Cache operations with tenant isolation
    async def cache_get(
        self, tenant_id: str, cache_key: str, default: JSONValue | None = None
    ) -> JSONValue | None:
        """Get cached value with tenant isolation"""
        isolated_key = f"tenant:{tenant_id}:{cache_key}"
        value = await self.get_json(isolated_key)
        return value if value is not None else default

    async def cache_set(
        self, tenant_id: str, cache_key: str, value: JSONValue, ex: int | None = None
    ) -> bool:
        """Set cached value with tenant isolation"""
        isolated_key = f"tenant:{tenant_id}:{cache_key}"
        return await self.set_json(isolated_key, value, ex=ex)

    async def cache_delete(self, tenant_id: str, cache_key: str) -> bool:
        """Delete cached value with tenant isolation"""
        isolated_key = f"tenant:{tenant_id}:{cache_key}"
        return await self.delete(isolated_key)

    # Progress tracking
    async def set_progress(
        self, tenant_id: str, project_id: str, step: int, progress_data: dict[str, Any]
    ) -> bool:
        """Set progress data for project step"""
        key = f"progress:{tenant_id}:{project_id}:{step}"
        return await self.set_json(key, progress_data, ex=3600)  # 1 hour expiry

    async def get_progress(
        self, tenant_id: str, project_id: str, step: int
    ) -> dict[str, Any] | None:
        """Get progress data for project step"""
        key = f"progress:{tenant_id}:{project_id}:{step}"
        return await self.get_json(key)

    # Tenant management
    async def get_tenant_stats(self, tenant_id: str) -> dict[str, Any]:
        """Get tenant usage statistics"""
        try:
            pattern = f"tenant:{tenant_id}:*"
            keys = await self.client.keys(pattern)

            stats = {"cache_keys": len(keys), "memory_usage": 0, "active_projects": 0}

            # Count active projects
            progress_pattern = f"progress:{tenant_id}:*"
            progress_keys = await self.client.keys(progress_pattern)
            project_ids = set()
            for key in progress_keys:
                parts = key.split(":")
                if len(parts) >= 3:
                    project_ids.add(parts[2])
            stats["active_projects"] = len(project_ids)

            return stats

        except RedisError as e:
            logger.error(
                "Failed to get tenant stats", tenant_id=tenant_id, error=str(e)
            )
            return {"cache_keys": 0, "memory_usage": 0, "active_projects": 0}

    def _get_current_timestamp(self) -> float:
        """Get current timestamp"""
        import time

        return time.time()

    async def close(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")
