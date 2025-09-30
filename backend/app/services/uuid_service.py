"""
UUID generation service leveraging PostgreSQL 18 uuidv7() function.
Provides timestamp-ordered UUIDs for JTI and other use cases.
"""

from __future__ import annotations

import uuid

from app.core.logger import get_logger

logger = get_logger(__name__)


class UUIDService:
    """Service for generating UUIDs using PostgreSQL 18 uuidv7() function."""

    @staticmethod
    async def generate_uuidv7() -> str:
        """
        Generate UUID v7 using PostgreSQL 18 native function.

        UUID v7 are time-ordered and provide better performance
        characteristics than random UUID4 for JTI use cases.

        Returns:
            UUID v7 string
        """
        try:
            # Import database module to use the correct session manager
            from sqlalchemy import text

            from app.core.database import get_db_session

            async with get_db_session() as session:
                result = await session.execute(text("SELECT generate_jti() as jti"))
                jti_str = result.scalar_one()
                return str(jti_str)
        except Exception as e:
            logger.warning(
                "Failed to generate UUID v7 via PostgreSQL function, trying direct uuidv7()",
                error=str(e),
            )
            try:
                # Try direct uuidv7() function
                from sqlalchemy import text

                from app.core.database import get_db_session

                async with get_db_session() as session:
                    result = await session.execute(text("SELECT uuidv7() as uuid"))
                    uuid_str = result.scalar_one()
                    return str(uuid_str)
            except Exception as e2:
                logger.error(
                    "Failed to generate UUID v7 via PostgreSQL - no fallback available",
                    error=str(e2),
                )
                # TODO: Implement proper error handling for UUID generation failure
                raise NotImplementedError(
                    "PostgreSQL UUID v7 generation failed and no alternative implemented"
                )

    @staticmethod
    def generate_uuidv4() -> str:
        """
        Generate UUID v4 using Python's uuid module.

        Returns:
            UUID v4 string
        """
        return str(uuid.uuid4())

    @staticmethod
    async def generate_jti() -> str:
        """
        Generate JTI (JWT ID) using UUID v7 for optimal performance.

        JTI benefits from UUID v7's time-ordered nature:
        - Better cache locality
        - Improved database index performance
        - Natural chronological ordering

        Returns:
            JTI string (UUID v7)
        """
        return await UUIDService.generate_uuidv7()


# Singleton instance for backward compatibility
_uuid_service = UUIDService()


# Export convenience functions for backward compatibility
async def generate_uuidv7() -> str:
    """Generate UUID v7 using PostgreSQL 18 native function."""
    return await _uuid_service.generate_uuidv7()


async def generate_uuidv4() -> str:
    """Generate UUID v4 using Python's uuid module."""
    return _uuid_service.generate_uuidv4()


async def generate_jti() -> str:
    """Generate JTI using UUID v7 for optimal performance."""
    return await _uuid_service.generate_jti()
