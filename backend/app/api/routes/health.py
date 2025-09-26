"""
Health check endpoints for monitoring system status.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.qdrant import QdrantAdapter
from app.adapters.redis import RedisAdapter
from app.core.config import settings
from app.core.database import DatabaseManager, get_db
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Comprehensive health check endpoint for all system components.

    Returns overall system status and detailed component health information.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
        "components": {},
        "checks": {},
    }

    # Database health check
    db_health = await DatabaseManager.health_check()
    health_status["components"]["database"] = db_health

    if db_health["status"] != "healthy":
        health_status["status"] = "degraded"

    # Redis health check
    try:
        redis_adapter = RedisAdapter()
        redis_health = await redis_adapter.health_check()
        health_status["components"]["redis"] = redis_health

        if redis_health["status"] != "healthy":
            health_status["status"] = "degraded"

    except (ConnectionError, TimeoutError) as e:
        logger.error("Redis connection failed", error=str(e))
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {e!s}",
            "details": {"error": str(e)},
        }
        health_status["status"] = "degraded"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e), exc_info=True)
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {e!s}",
            "details": {"error": str(e)},
        }
        health_status["status"] = "degraded"

    # Qdrant health check
    try:
        qdrant_adapter = QdrantAdapter()
        qdrant_health = await qdrant_adapter.health_check()
        health_status["components"]["qdrant"] = qdrant_health

        if qdrant_health["status"] != "healthy":
            health_status["status"] = "degraded"

    except (ConnectionError, TimeoutError) as e:
        logger.error("Qdrant connection failed", error=str(e))
        health_status["components"]["qdrant"] = {
            "status": "unhealthy",
            "message": f"Qdrant connection failed: {e!s}",
            "details": {"error": str(e)},
        }
        health_status["status"] = "degraded"
    except Exception as e:
        logger.error("Qdrant health check failed", error=str(e), exc_info=True)
        health_status["components"]["qdrant"] = {
            "status": "unhealthy",
            "message": f"Qdrant connection failed: {e!s}",
            "details": {"error": str(e)},
        }
        health_status["status"] = "degraded"

    # Vault health check (if configured)
    if settings.VAULT_ADDR:
        try:
            vault_health = await _check_vault_health()
            health_status["components"]["vault"] = vault_health

            if vault_health["status"] != "healthy":
                health_status["status"] = "degraded"

        except (ConnectionError, TimeoutError) as e:
            logger.error("Vault connection failed", error=str(e))
            health_status["components"]["vault"] = {
                "status": "unhealthy",
                "message": f"Vault connection failed: {e!s}",
                "details": {"error": str(e)},
            }
            health_status["status"] = "degraded"
        except Exception as e:
            logger.error("Vault health check failed", error=str(e), exc_info=True)
            health_status["components"]["vault"] = {
                "status": "unhealthy",
                "message": f"Vault connection failed: {e!s}",
                "details": {"error": str(e)},
            }
            health_status["status"] = "degraded"

    # Application-specific checks
    health_status["checks"] = {
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "tenant_isolation": settings.ENABLE_TENANT_ISOLATION,
        "database_url_configured": bool(settings.DATABASE_URL),
        "redis_url_configured": bool(settings.REDIS_URL),
        "qdrant_url_configured": bool(settings.QDRANT_URL),
        "vault_configured": bool(settings.VAULT_ADDR),
    }

    # Determine overall status
    unhealthy_components = [
        name
        for name, component in health_status["components"].items()
        if component["status"] == "unhealthy"
    ]

    if unhealthy_components:
        health_status["status"] = "unhealthy"
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service unavailable",
                "unhealthy_components": unhealthy_components,
                "health_status": health_status,
            },
        )

    return health_status


@router.get("/health/simple")
async def simple_health_check() -> dict[str, str]:
    """
    Simple health check for load balancers and container health probes.

    Returns minimal information suitable for automated monitoring.
    """
    return {
        "status": "healthy",
        "service": "JEEX Plan API",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Readiness check endpoint for Kubernetes and container orchestrators.

    Indicates if the application is ready to serve traffic.
    """
    # Check if we can connect to the database
    try:
        await db.execute(text("SELECT 1"))
    except (ConnectionError, TimeoutError) as e:
        logger.error("Database connection failed", error=str(e))
        raise HTTPException(status_code=503, detail="Database not ready")
    except Exception as e:
        logger.error("Readiness check failed - database not ready", error=str(e), exc_info=True)
        raise HTTPException(status_code=503, detail="Database not ready")

    return {
        "status": "ready",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {"database": "ready", "application": "ready"},
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """
    Liveness check endpoint for Kubernetes and container orchestrators.

    Indicates if the application is running.
    """
    return {"status": "alive", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/health/metrics")
async def health_metrics() -> dict[str, Any]:
    """
    Health metrics endpoint with detailed system information.

    Returns comprehensive metrics for monitoring dashboards.
    """
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime": "N/A",  # Would need to track application start time
        "components": {
            "database": {
                "url": settings.DATABASE_URL.split("@")[-1]
                if "@" in settings.DATABASE_URL
                else "configured",
                "configured": bool(settings.DATABASE_URL),
            },
            "redis": {
                "url": settings.REDIS_URL,
                "configured": bool(settings.REDIS_URL),
            },
            "qdrant": {
                "url": settings.QDRANT_URL,
                "collection": settings.QDRANT_COLLECTION,
                "configured": bool(settings.QDRANT_URL),
            },
            "vault": {
                "address": settings.VAULT_ADDR,
                "configured": bool(settings.VAULT_ADDR),
            },
        },
        "features": {
            "multi_tenancy": settings.ENABLE_TENANT_ISOLATION,
            "authentication": True,
            "rate_limiting": True,
            "observability": bool(settings.OTLP_ENDPOINT),
        },
    }


async def _check_vault_health() -> dict[str, Any]:
    """Check HashiCorp Vault health"""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.VAULT_ADDR}/v1/sys/health")

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "healthy",
                    "message": "Vault is healthy and initialized",
                    "details": {
                        "initialized": data.get("initialized", False),
                        "sealed": data.get("sealed", True),
                        "version": data.get("version", "unknown"),
                    },
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"Vault returned status {response.status_code}",
                    "details": {"status_code": response.status_code},
                }

    except (ConnectionError, TimeoutError) as e:
        return {
            "status": "unhealthy",
            "message": f"Vault connection failed: {e!s}",
            "details": {"error": str(e)},
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Vault health check failed: {e!s}",
            "details": {"error": str(e)},
        }
