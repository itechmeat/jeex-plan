"""
JEEX Plan - Simple Main API Service
Simplified implementation for Docker container
"""

import time
from typing import Any

import aiohttp
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import agent routes
from app.api.routes.agents import router as agents_router
from app.core.logger import get_logger

logger = get_logger()

app = FastAPI(
    title="JEEX Plan API",
    description="AI-powered documentation management system",
    version="1.0.0",
)


# CORS configuration for development
def add_cors_middleware() -> None:
    """Add CORS middleware to the app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


add_cors_middleware()

# Include agent routes
app.include_router(agents_router, prefix="/api/v1")

# Include document generation routes
try:
    from app.api.routes.document_generation import router as document_generation_router

    app.include_router(document_generation_router, prefix="/api/v1")
except ImportError as exc:
    logger.warning(
        "Could not import document generation routes", extra={"error": str(exc)}
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {
        "service": "JEEX Plan API",
        "version": "1.0.0",
        "status": "running",
        "hot_reload": "testing hot-reload functionality",
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
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.get(url) as response:
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
            "endpoint": "postgresql://postgres:secure_password@postgres:5432/jeex_plan",
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
