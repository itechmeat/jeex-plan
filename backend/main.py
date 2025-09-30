"""
JEEX Plan - Main API Service
Full implementation with authentication and multi-tenancy
"""

import time
from typing import Any

import aiohttp
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routes
from app.api.routes.agents import router as agents_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.projects import router as projects_router
from app.core.config import EXEMPT_PATHS
from app.core.logger import get_logger

# Import middleware
from app.middleware.security import CSRFProtectionMiddleware
from app.middleware.tenant import TenantIsolationMiddleware

logger = get_logger()

app = FastAPI(
    title="JEEX Plan API",
    description="AI-powered documentation management system",
    version="1.0.0",
)


# CORS configuration for development
def add_cors_middleware() -> None:
    """Add CORS middleware to the app."""
    from app.core.config import settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,  # Enable credentials for auth
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


def add_tenant_middleware() -> None:
    """Add tenant isolation middleware."""
    app.add_middleware(TenantIsolationMiddleware, excluded_path_prefixes=EXEMPT_PATHS)


def add_csrf_middleware() -> None:
    """Add CSRF protection middleware.

    Note: Registered after tenant middleware to ensure tenant context is available.
    In FastAPI, middleware is executed in reverse order of registration:
    - CORS (executes first - handles preflight)
    - Tenant Isolation (executes second - extracts tenant_id)
    - CSRF Protection (executes last - validates CSRF with tenant context)
    """
    app.add_middleware(CSRFProtectionMiddleware, exempt_paths=EXEMPT_PATHS)


# Add middleware in correct order
# Execution order is REVERSED: last registered = first to execute
add_cors_middleware()  # Executes first (CORS preflight handling)
add_tenant_middleware()  # Executes second (extracts tenant context)
add_csrf_middleware()  # Executes last (CSRF validation with tenant context)

# Include all routes
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(projects_router, prefix="/api/v1", tags=["Projects"])
app.include_router(agents_router, prefix="/api/v1", tags=["Agents"])

# Include document generation routes (optional)
try:
    from app.api.routes.document_generation import router as document_generation_router

    app.include_router(document_generation_router, prefix="/api/v1", tags=["Documents"])
except ImportError as exc:
    logger.warning(
        "Could not import document generation routes", extra={"error": str(exc)}
    )

# Include vector routes (optional)
try:
    from app.api.routes.vectors import router as vectors_router

    app.include_router(vectors_router, prefix="/api/v1", tags=["Vectors"])
except ImportError as exc:
    logger.warning("Could not import vector routes", extra={"error": str(exc)})


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    from ..app.core.config import get_settings

    settings = get_settings()

    return {
        "service": "JEEX Plan API",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "hot_reload": settings.is_development,
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Service health check"""
    return {
        "status": "healthy",
        "service": "jeex-plan-api",
        "version": "1.0.0",
        "database": "simulated_connected",
        "redis": "simulated_connected",
        "qdrant": "simulated_connected",
    }


@app.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Service readiness check"""
    return {
        "status": "ready",
        "database": "simulated_ready",
        "cache": "simulated_ready",
        "vector_db": "simulated_ready",
    }


async def check_service_health(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """External service health check"""
    start_time = time.time()
    try:
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session,
            session.get(url) as response,
        ):
            response_time = round((time.time() - start_time) * 1000)
            if response.status == 200:
                return {
                    "status": "pass",
                    "response_time": response_time,
                    "details": "Service operational",
                }
            else:
                return {
                    "status": "fail",
                    "response_time": response_time,
                    "details": f"HTTP {response.status}",
                }
    except TimeoutError:
        return {
            "status": "fail",
            "response_time": round((time.time() - start_time) * 1000),
            "details": "Timeout",
        }
    except (aiohttp.ClientError, OSError) as e:
        return {
            "status": "fail",
            "response_time": round((time.time() - start_time) * 1000),
            "details": str(e),
        }


@app.get("/system/status")
async def system_status() -> dict[str, Any]:
    """System services status check"""
    services = [
        {
            "name": "API Backend",
            "endpoint": "http://localhost:8000/health",
            "url": "http://localhost:8000/health",
        },
        {
            "name": "PostgreSQL",
            "endpoint": "postgresql://postgres@postgres:5432/jeex_plan",
            "url": "postgres:5432",
        },
        {"name": "Redis", "endpoint": "redis://redis:6379", "url": "redis:6379"},
        {
            "name": "Qdrant",
            "endpoint": "http://qdrant:6333/",
            "url": "http://qdrant:6333/",
        },
        {
            "name": "Vault",
            "endpoint": "http://vault:8200/v1/sys/health",
            "url": "http://vault:8200/v1/sys/health",
        },
    ]

    results = []
    for service in services:
        service_name = service["name"]
        check_result = await check_service_health(service["url"])

        results.append(
            {
                "service": service_name,
                "endpoint": service["endpoint"],
                "status": check_result["status"],
                "responseTime": check_result["response_time"],
                "details": check_result["details"],
                "timestamp": time.time(),
            }
        )

    return {"services": results, "timestamp": time.time()}


@app.get("/api/v1/info")
async def api_info() -> dict[str, Any]:
    """API information"""
    return {
        "name": "JEEX Plan API",
        "description": "AI-powered documentation management system",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Root endpoint"},
            {"path": "/health", "method": "GET", "description": "Health check"},
            {"path": "/ready", "method": "GET", "description": "Readiness check"},
            {
                "path": "/system/status",
                "method": "GET",
                "description": "System services status",
            },
            {"path": "/api/v1/info", "method": "GET", "description": "API information"},
            {
                "path": "/api/v1/agents/business-analysis",
                "method": "POST",
                "description": "Execute business analysis",
            },
            {
                "path": "/api/v1/agents/architecture-design",
                "method": "POST",
                "description": "Execute architecture design",
            },
            {
                "path": "/api/v1/agents/implementation-planning",
                "method": "POST",
                "description": "Execute implementation planning",
            },
            {
                "path": "/api/v1/agents/engineering-standards",
                "method": "POST",
                "description": "Execute engineering standards",
            },
            {
                "path": "/api/v1/agents/workflow/execute-stream",
                "method": "POST",
                "description": "Execute full workflow with SSE",
            },
            {
                "path": "/api/v1/agents/health",
                "method": "GET",
                "description": "Agent system health check",
            },
        ],
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
