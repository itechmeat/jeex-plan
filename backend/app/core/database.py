"""
Database configuration and connection management.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger()

# Create async engine with optimized settings
if settings.is_development:
    # Development: use NullPool (no pool parameters)
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=settings.DEBUG,
        poolclass=NullPool,
        pool_pre_ping=True,
        pool_recycle=300,
    )
else:
    # Production: use connection pooling
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=settings.DEBUG,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=300,
    )

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Import canonical Base from models
from app.models.base import Base


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database dependency for FastAPI routes"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session():
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
    """Database connection manager with health checks"""

    @staticmethod
    async def health_check() -> dict:
        """Check database connectivity"""
        try:
            async with AsyncSessionLocal() as session:
                # Simple query to test connection
                await session.execute(text("SELECT 1"))
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "details": {
                        "database_url": settings.DATABASE_URL.split("@")[-1],
                    }
                }
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {e!s}",
                "details": {"error": str(e)}
            }

    @staticmethod
    async def execute_raw_sql(session: AsyncSession, sql: str, params: dict | None = None):
        """Execute raw SQL query"""
        try:
            result = await session.execute(sql, params or {})
            return result.fetchall()
        except Exception as e:
            logger.error("Raw SQL execution failed", error=str(e), sql=sql)
            raise
