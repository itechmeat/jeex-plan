"""Database configuration and connection management."""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import Executable

from app.core.config import settings
from app.core.logger import get_logger
from app.models.base import Base

logger = get_logger()


def _sanitize_database_url(database_url: str) -> str:
    """Remove credentials from DATABASE_URL for safe logging."""
    try:
        parsed = urlparse(database_url)
        if parsed.hostname:
            safe_netloc = parsed.hostname
            if parsed.port:
                safe_netloc = f"{safe_netloc}:{parsed.port}"
        else:
            safe_netloc = ""
        return urlunparse((parsed.scheme, safe_netloc, parsed.path, "", "", ""))
    except Exception:
        return "configured"


# Create async engine with optimized settings
# SECURITY: Validate and normalize DATABASE_URL properly
# Check if already using asyncpg driver to avoid double-replacement corruption
if "postgresql+asyncpg://" in settings.DATABASE_URL:
    ASYNC_DATABASE_URL = settings.DATABASE_URL
elif "postgresql://" in settings.DATABASE_URL:
    ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
else:
    logger.error(
        "Invalid DATABASE_URL format", url=_sanitize_database_url(settings.DATABASE_URL)
    )
    raise ValueError(
        "DATABASE_URL must start with postgresql:// or postgresql+asyncpg://"
    )

if settings.is_development:
    # Development: use NullPool (no pool parameters)
    engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
        connect_args={"server_settings": settings.get_pg_server_settings_dev()},
    )
else:
    # Production: use connection pooling
    engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"server_settings": settings.get_pg_server_settings_prod()},
    )

# Create session factory
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database dependency for FastAPI routes"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Context manager for database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables() -> None:
    """Create database tables on startup"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


async def close_database_connections() -> None:
    """Close all database connections"""
    await engine.dispose()
    logger.info("Database connections closed")


class DatabaseManager:
    """Database connection manager with health checks."""

    @staticmethod
    async def health_check() -> dict[str, Any]:
        """Check database connectivity"""
        try:
            async with AsyncSessionLocal() as session:
                # Simple query to test connection
                await session.execute(text("SELECT 1"))
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "details": {
                        "database_url": _sanitize_database_url(settings.DATABASE_URL),
                    },
                }
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {e!s}",
                "details": {"error": str(e)},
            }

    @staticmethod
    async def execute_raw_sql(
        session: AsyncSession,
        sql: str | Executable,
        params: dict[str, Any] | None = None,
    ) -> list[tuple[Any, ...]]:
        """Execute raw SQL query"""
        try:
            statement = text(sql) if isinstance(sql, str) else sql
            result: Result[Any] = await session.execute(statement, params or {})
            rows = result.fetchall()
            return [tuple(row) for row in rows]
        except Exception as e:
            # SECURITY: Avoid logging raw SQL and params to prevent sensitive data exposure
            sql_preview = (
                sql[:50] + "..." if isinstance(sql, str) and len(sql) > 50 else "query"
            )
            logger.error(
                "Raw SQL execution failed",
                error=str(e),
                sql_type=type(sql).__name__,
                sql_preview=sql_preview,
                has_params=bool(params),
            )
            raise
