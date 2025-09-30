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
from app.core.database import DatabaseManager, _sanitize_database_url, get_db
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Comprehensive health check endpoint for all system components.

    Returns overall system status and detailed component health information.
    """
    components: dict[str, Any] = {}
    health_status: dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
        "components": components,
        "checks": {},
    }

    # Database health check
    db_health = await DatabaseManager.health_check()
    components["database"] = db_health

    if db_health["status"] != "healthy":
        health_status["status"] = "degraded"

    # Redis health check
    try:
        redis_adapter = RedisAdapter()
        redis_health = await redis_adapter.health_check()
        components["redis"] = redis_health

        if redis_health["status"] != "healthy":
            health_status["status"] = "degraded"

    except (ConnectionError, TimeoutError) as e:
        logger.error("Redis connection failed", error=str(e))
        components["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {e!s}",
            "details": {"error": str(e)},
        }
        health_status["status"] = "degraded"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e), exc_info=True)
        components["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {e!s}",
            "details": {"error": str(e)},
        }
        health_status["status"] = "degraded"

    # Qdrant health check
    try:
        qdrant_adapter = QdrantAdapter()
        qdrant_health = await qdrant_adapter.health_check()
        components["qdrant"] = qdrant_health

        if qdrant_health["status"] != "healthy":
            health_status["status"] = "degraded"

    except (ConnectionError, TimeoutError) as e:
        logger.error("Qdrant connection failed", error=str(e))
        components["qdrant"] = {
            "status": "unhealthy",
            "message": f"Qdrant connection failed: {e!s}",
            "details": {"error": str(e)},
        }
        health_status["status"] = "degraded"
    except Exception as e:
        logger.error("Qdrant health check failed", error=str(e), exc_info=True)
        components["qdrant"] = {
            "status": "unhealthy",
            "message": f"Qdrant connection failed: {e!s}",
            "details": {"error": str(e)},
        }
        health_status["status"] = "degraded"

    # Vault health check (if configured and in production)
    if settings.VAULT_ADDR and settings.is_production:
        try:
            vault_health = await _check_vault_health()
            components["vault"] = vault_health

            if vault_health["status"] != "healthy":
                health_status["status"] = "degraded"

        except (ConnectionError, TimeoutError) as e:
            logger.error("Vault connection failed", error=str(e))
            components["vault"] = {
                "status": "unhealthy",
                "message": f"Vault connection failed: {e!s}",
                "details": {"error": str(e)},
            }
            health_status["status"] = "degraded"
        except Exception as e:
            logger.error("Vault health check failed", error=str(e), exc_info=True)
            components["vault"] = {
                "status": "unhealthy",
                "message": f"Vault connection failed: {e!s}",
                "details": {"error": str(e)},
            }
            health_status["status"] = "degraded"
    elif settings.VAULT_ADDR and settings.is_development:
        # In development, mark Vault as optional
        try:
            vault_health = await _check_vault_health()
            if vault_health["status"] == "healthy":
                components["vault"] = vault_health
            else:
                # Don't affect overall health status in development if Vault is unhealthy
                logger.info(
                    "Vault unhealthy in development (optional)",
                    status=vault_health["status"],
                )
                components["vault"] = {
                    "status": "healthy",
                    "message": "Vault optional in development - currently unhealthy",
                    "details": {
                        "note": "Vault health checks are optional in development mode",
                        "actual_status": vault_health["status"],
                    },
                }
        except Exception as e:
            logger.info("Vault unavailable in development (optional)", error=str(e))
            components["vault"] = {
                "status": "healthy",
                "message": "Vault optional in development - not available",
                "details": {
                    "note": "Vault health checks are optional in development mode"
                },
            }

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
        for name, component in components.items()
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
        logger.error(
            "Readiness check failed - database not ready", error=str(e), exc_info=True
        )
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
                "url": _sanitize_database_url(settings.DATABASE_URL),
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
