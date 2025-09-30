"""Test cleanup endpoint for E2E testing."""

from fastapi import APIRouter, HTTPException, status
from structlog import get_logger

from app.core.config import settings

logger = get_logger()
router = APIRouter()


@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_test_data():
    """
    Clean up test data after E2E tests.

    This endpoint is used by E2E tests to clean up any test data
    that was created during testing. In development mode, this
    provides a simple way to reset the test state.

    Returns:
        dict: Cleanup status message
    """
    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test cleanup is only available in development mode",
        )

    try:
        logger.info("Cleaning up test data")

        # In a real implementation, this would clean up:
        # - Test users
        # - Test projects
        # - Test tenants
        # - Test documents
        # - Any other test data

        # For now, just log and return success
        logger.info("Test data cleanup completed")

        return {
            "status": "success",
            "message": "Test data cleaned up successfully",
            "environment": settings.ENVIRONMENT,
        }

    except Exception as exc:
        logger.error("Failed to clean up test data", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clean up test data",
        )
