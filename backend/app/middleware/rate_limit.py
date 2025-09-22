"""
Rate limiting middleware with Redis backend for API endpoint protection.
"""

import time
import hashlib
from typing import Optional, Tuple, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

from ..core.config import get_settings
from ..middleware.tenant import TenantContextManager

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API requests."""

    def __init__(
        self,
        app,
        redis_client: Optional[redis.Redis] = None,
        default_requests: int = 100,
        default_window: int = 60
    ):
        super().__init__(app)
        self.redis_client = redis_client
        self.default_requests = default_requests
        self.default_window = default_window
        self.excluded_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ]

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting checks."""

        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)

        # Get Redis client from app state if not provided during init
        redis_client = self.redis_client or getattr(request.app.state, 'redis_client', None)

        # Skip if Redis is not available
        if not redis_client:
            return await call_next(request)

        # Apply rate limiting
        is_allowed, headers = await self._check_rate_limit(request, redis_client)

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers=headers
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for header, value in headers.items():
            response.headers[header] = str(value)

        return response

    async def _check_rate_limit(self, request: Request, redis_client=None) -> Tuple[bool, dict]:
        """Check if request is within rate limits."""

        # Get rate limit configuration based on endpoint and user
        limit_config = await self._get_rate_limit_config(request)
        requests_limit = limit_config["requests"]
        time_window = limit_config["window"]

        # Generate unique key for this user/endpoint combination
        key = await self._generate_rate_limit_key(request)

        # Use sliding window algorithm
        current_time = int(time.time())
        window_start = current_time - time_window

        # Clean old entries and count current requests
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(current_time): current_time})
        pipe.expire(key, time_window)

        results = await pipe.execute()
        current_requests = results[1]

        # Calculate headers
        remaining = max(0, requests_limit - current_requests)
        reset_time = current_time + time_window

        headers = {
            "X-RateLimit-Limit": requests_limit,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Reset": reset_time,
            "X-RateLimit-Window": time_window
        }

        # Check if limit exceeded
        is_allowed = current_requests < requests_limit

        return is_allowed, headers

    async def _get_rate_limit_config(self, request: Request) -> dict:
        """Get rate limit configuration for the request."""

        # Default limits
        config = {
            "requests": self.default_requests,
            "window": self.default_window
        }

        # Apply endpoint-specific limits
        endpoint_limits = {
            "/auth/login": {"requests": 5, "window": 300},  # 5 requests per 5 minutes
            "/auth/register": {"requests": 3, "window": 3600},  # 3 requests per hour
            "/auth/oauth": {"requests": 10, "window": 300},  # 10 requests per 5 minutes
            "/api/v1/projects": {"requests": 200, "window": 60},  # 200 requests per minute
            "/api/v1/documents": {"requests": 300, "window": 60},  # 300 requests per minute
            "/api/v1/agents": {"requests": 50, "window": 60},  # 50 requests per minute
        }

        for path, limits in endpoint_limits.items():
            if request.url.path.startswith(path):
                config.update(limits)
                break

        # Apply user-specific multipliers (premium users could have higher limits)
        tenant_id = TenantContextManager.get_tenant_id(request)
        if tenant_id:
            # Could implement tenant-based rate limits here
            pass

        return config

    async def _generate_rate_limit_key(self, request: Request) -> str:
        """Generate unique key for rate limiting."""

        # Get client identifier
        client_id = await self._get_client_identifier(request)

        # Include endpoint in key for endpoint-specific limits
        endpoint = request.url.path

        # Create hash for the key
        key_data = f"rate_limit:{client_id}:{endpoint}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()

        return f"rl:{key_hash}"

    async def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client."""

        # Try to get user ID from tenant context
        tenant_id = TenantContextManager.get_tenant_id(request)
        if tenant_id:
            return f"tenant:{tenant_id}"

        # Fallback to IP address for unauthenticated requests
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""

        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client
        return request.client.host if request.client else "unknown"


class RateLimitService:
    """Service for managing rate limits."""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def get_rate_limit_status(self, key: str) -> dict:
        """Get current rate limit status for a key."""

        current_time = int(time.time())
        window_start = current_time - settings.RATE_LIMIT_WINDOW

        # Get request count in current window
        request_count = await self.redis_client.zcount(
            key,
            window_start,
            current_time
        )

        # Get TTL
        ttl = await self.redis_client.ttl(key)

        return {
            "requests_made": request_count,
            "requests_limit": settings.RATE_LIMIT_REQUESTS,
            "requests_remaining": max(0, settings.RATE_LIMIT_REQUESTS - request_count),
            "window_size": settings.RATE_LIMIT_WINDOW,
            "reset_time": current_time + ttl if ttl > 0 else None
        }

    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit for a specific key."""

        result = await self.redis_client.delete(key)
        return result > 0

    async def set_custom_limit(
        self,
        identifier: str,
        requests: int,
        window: int,
        duration: Optional[int] = None
    ) -> bool:
        """Set custom rate limit for a specific identifier."""

        import json
        key = f"custom_limit:{identifier}"
        value = {"requests": requests, "window": window}

        if duration:
            await self.redis_client.setex(key, duration, json.dumps(value))
        else:
            await self.redis_client.set(key, json.dumps(value))

        return True

    async def get_custom_limit(self, identifier: str) -> Optional[dict]:
        """Get custom rate limit for a specific identifier."""

        key = f"custom_limit:{identifier}"
        value = await self.redis_client.get(key)

        if value:
            try:
                import json
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None

        return None

    async def list_active_limits(self, pattern: str = "*") -> List[dict]:
        """List all active rate limit keys."""

        keys = await self.redis_client.keys(f"rl:{pattern}")
        result = []

        for key in keys:
            status = await self.get_rate_limit_status(key)
            result.append({
                "key": key,
                "status": status
            })

        return result

    async def cleanup_expired_limits(self) -> int:
        """Clean up expired rate limit entries."""

        current_time = int(time.time())
        expired_count = 0

        # Get all rate limit keys
        keys = await self.redis_client.keys("rl:*")

        for key in keys:
            # Remove entries older than maximum window
            removed = await self.redis_client.zremrangebyscore(
                key,
                0,
                current_time - (settings.RATE_LIMIT_WINDOW * 2)
            )
            expired_count += removed

            # Delete empty keys
            if await self.redis_client.zcard(key) == 0:
                await self.redis_client.delete(key)

        return expired_count


# Dependency function to get rate limit service
def get_rate_limit_service(redis_client: redis.Redis) -> RateLimitService:
    """Get rate limit service instance."""
    return RateLimitService(redis_client)