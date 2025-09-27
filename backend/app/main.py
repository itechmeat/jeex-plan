"""Main FastAPI application entry point for JEEX Plan backend."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from structlog import get_logger

from app.api.routes import agents, auth, health, projects
from app.core.config import settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import (
    CSRFProtectionMiddleware,
    RequestSizeMiddleware,
    SecurityHeadersMiddleware,
)

# from app.core.observability import setup_observability  # NOTE: Disabled due to OpenTelemetry version conflicts
from app.middleware.tenant import TenantIsolationMiddleware

# Configure structured logging
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager"""
    # Startup
    logger.info("Starting JEEX Plan Backend")

    # Setup observability
    # setup_observability(app)  # NOTE: Disabled due to OpenTelemetry version conflicts

    # Initialize Redis connection for rate limiting
    try:
        redis_settings = settings.get_redis_settings()
        redis_url = settings.REDIS_URL
        connection_kwargs = {
            key: value
            for key, value in redis_settings.items()
            if key not in {"host", "port"}
        }
        redis_client = redis.from_url(redis_url, **connection_kwargs)
        await redis_client.ping()
        app.state.redis_client = redis_client
        logger.info("Redis connection established")

    except redis.RedisError as exc:
        logger.warning(
            "Failed to connect to Redis, rate limiting will be disabled: %s", exc
        )
        app.state.redis_client = None

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down JEEX Plan Backend")

    # Close Redis connection
    if hasattr(app.state, "redis_client") and app.state.redis_client:
        await app.state.redis_client.aclose()
        logger.info("Redis connection closed")


# Create FastAPI application
app = FastAPI(
    title="JEEX Plan API",
    description="Multi-agent documentation generation system API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add security middleware stack (order matters - last added is first executed)

# 1. Request size limiting (first check)
app.add_middleware(RequestSizeMiddleware, max_size=10 * 1024 * 1024)  # 10MB

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. CSRF protection
app.add_middleware(CSRFProtectionMiddleware)

# 4. Rate limiting with Redis
app.add_middleware(
    RateLimitMiddleware,
    redis_client=None,  # Will be populated from app.state during requests
    default_requests=settings.RATE_LIMIT_REQUESTS,
    default_window=settings.RATE_LIMIT_WINDOW,
)

# 5. Tenant isolation
app.add_middleware(TenantIsolationMiddleware)

# 6. CORS (should be close to the end) - More restrictive settings for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],  # Explicit methods instead of *
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "X-Tenant-ID",
        "Cache-Control",
    ],  # Explicit headers instead of *
    expose_headers=["X-Request-ID", "X-Process-Time"],
    max_age=3600,  # Cache preflight requests for 1 hour
)


# Add request logging middleware
@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Log all HTTP requests with structured logging"""
    logger.info(
        "HTTP request received",
        method=request.method,
        url=str(request.url),
        client_host=request.client.host if request.client else None,
    )

    response = await call_next(request)

    logger.info(
        "HTTP request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
    )

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler with structured logging"""
    logger.exception("Unhandled exception for %s %s", request.method, request.url)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-ID"),
        },
    )


# Include API routers with proper prefixes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "JEEX Plan API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
